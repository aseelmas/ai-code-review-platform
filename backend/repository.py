"""Validation, bounded cloning, and cleanup for public GitHub repositories."""

import logging
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import tempfile
import time


CLONE_TIMEOUT_SECONDS = 60
MAX_REPOSITORY_BYTES = 100 * 1024 * 1024
MAX_REPOSITORY_FILES = 20_000
MAX_PYTHON_FILES = 500
MAX_PYTHON_FILE_BYTES = 512 * 1024
MAX_PYTHON_BYTES = 5 * 1024 * 1024


class RepositoryError(Exception):
    """An expected failure with a safe, user-facing message."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def validate_repository_url(value: str) -> str:
    # Validate the raw string so URL normalization cannot hide paths or credentials.
    match = re.fullmatch(
        r"https://github\.com/([A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))/([A-Za-z0-9_.-]{1,100})/?",
        value.strip(),
        flags=re.IGNORECASE,
    )
    if not match or match[2] in {".", "..", ".git"}:
        raise ValueError("Use a public GitHub repository URL: https://github.com/owner/repository")
    return f"https://github.com/{match[1]}/{match[2]}"


def cleanup_repository(repo_path: str) -> None:
    """Remove our temporary clone, including read-only Git objects on Windows."""
    def remove_readonly(function, path, error):
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
        function(path)

    try:
        shutil.rmtree(repo_path, onerror=remove_readonly)
    except FileNotFoundError:
        pass
    except OSError:
        # Do not turn a successful analysis into an error or log source/secrets.
        logging.getLogger(__name__).warning("Temporary repository cleanup failed.")


def check_repository_budget(repo_path: str) -> None:
    """Also called during cloning; never follow repository symlinks."""
    total_bytes = 0
    total_files = 0
    for root, directories, files in os.walk(repo_path):
        directories[:] = [name for name in directories if not Path(root, name).is_symlink()]
        for name in files:
            path = Path(root, name)
            if path.is_symlink():
                continue
            try:
                total_bytes += path.stat().st_size
            except FileNotFoundError:
                # Git can rename temporary pack/index files while cloning.
                continue
            total_files += 1
            if total_bytes > MAX_REPOSITORY_BYTES or total_files > MAX_REPOSITORY_FILES:
                raise RepositoryError("Repository exceeds the analysis size limit. Try a smaller repository.", 413)


def stop_clone(process: subprocess.Popen) -> None:
    """Stop Git and its download/checkout children before cleaning up."""
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
            timeout=10,
        )
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    process.wait(timeout=10)


def discover_python_files(repo_path: str) -> list[str]:
    python_files = []
    total_bytes = 0
    for root, directories, files in os.walk(repo_path):
        directories[:] = sorted(
            name for name in directories
            if name != ".git" and not Path(root, name).is_symlink()
        )
        for name in sorted(files):
            path = Path(root, name)
            if not name.endswith(".py") or path.is_symlink():
                continue
            size = path.stat().st_size
            total_bytes += size
            python_files.append(os.path.relpath(path, repo_path))
            if (size > MAX_PYTHON_FILE_BYTES or total_bytes > MAX_PYTHON_BYTES
                    or len(python_files) > MAX_PYTHON_FILES):
                raise RepositoryError("Python source exceeds the analysis size limit. Try a smaller repository.", 413)
    return python_files


def clone_repository(repo_url: str) -> tuple[str, list[str]]:
    repo_url = validate_repository_url(repo_url)
    temp_dir = tempfile.mkdtemp(prefix="code-review-")
    process = None
    try:
        # Ignore machine/user Git config and credentials. No prompts, hooks,
        # redirects, submodules, or LFS downloads are needed for static review.
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        env.update(GIT_TERMINAL_PROMPT="0", GIT_CONFIG_NOSYSTEM="1",
                   GIT_CONFIG_GLOBAL=os.devnull, GIT_LFS_SKIP_SMUDGE="1")
        process = subprocess.Popen(
            ["git", "-c", "http.followRedirects=false", "-c", "credential.helper=",
             "-c", "core.hooksPath=/dev/null", "clone", "--depth", "1",
             "--single-branch", "--no-tags", "--template=", "--", repo_url, temp_dir],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            env=env, start_new_session=os.name != "nt",
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        deadline = time.monotonic() + CLONE_TIMEOUT_SECONDS
        while process.poll() is None:
            if time.monotonic() >= deadline:
                raise RepositoryError("Repository cloning timed out. Try a smaller repository or retry later.", 504)
            check_repository_budget(temp_dir)
            time.sleep(0.2)
        if process.returncode != 0:
            raise RepositoryError(
                "Unable to clone repository. Check that it exists, is public, and the URL is correct; otherwise retry later."
            )
        check_repository_budget(temp_dir)
        return temp_dir, discover_python_files(temp_dir)
    except BaseException:
        try:
            if process is not None:
                stop_clone(process)
        finally:
            cleanup_repository(temp_dir)
        raise
