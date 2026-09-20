from pathlib import Path
from unittest.mock import Mock
from types import SimpleNamespace

import pytest

from backend import repository


@pytest.fixture
def clone_setup(tmp_path, monkeypatch):
    clone = tmp_path / "clone"
    clone.mkdir()
    monkeypatch.setattr(repository.tempfile, "mkdtemp", lambda **kwargs: str(clone))
    process = Mock(returncode=0)
    process.poll.return_value = 0
    popen = Mock(return_value=process)
    monkeypatch.setattr(repository.subprocess, "Popen", popen)
    return clone, process, popen


def test_clone_discovers_python_and_uses_safe_options(clone_setup):
    clone, _, popen = clone_setup
    (clone / "app.py").write_text("x = 1", encoding="utf-8")
    (clone / "README.md").write_text("hello", encoding="utf-8")
    (clone / ".git").mkdir()
    (clone / ".git" / "hidden.py").write_text("print(1)", encoding="utf-8")
    path, files = repository.clone_repository("https://github.com/example/repo")
    assert path == str(clone)
    assert files == ["app.py"]
    args, kwargs = popen.call_args
    assert "--depth" in args[0] and "--single-branch" in args[0]
    assert "http.followRedirects=false" in args[0]
    assert kwargs["env"]["GIT_TERMINAL_PROMPT"] == "0"
    assert kwargs["env"]["GIT_CONFIG_NOSYSTEM"] == "1"
    repository.cleanup_repository(path)
    assert not clone.exists()


def test_clone_failure_cleans_up_and_hides_git_output(clone_setup):
    clone, process, _ = clone_setup
    process.returncode = 128
    with pytest.raises(repository.RepositoryError, match="exists, is public"):
        repository.clone_repository("https://github.com/example/missing")
    assert not clone.exists()


def test_missing_git_cleans_up(clone_setup):
    clone, _, popen = clone_setup
    popen.side_effect = FileNotFoundError("git unavailable")
    with pytest.raises(FileNotFoundError):
        repository.clone_repository("https://github.com/example/repo")
    assert not clone.exists()


def test_clone_timeout_stops_process_before_cleanup(clone_setup, monkeypatch):
    clone, process, _ = clone_setup
    process.poll.return_value = None
    monkeypatch.setattr(repository.time, "monotonic", Mock(side_effect=[0, 61]))
    stop = Mock(side_effect=lambda process: (clone / "stopped").touch())
    monkeypatch.setattr(repository, "stop_clone", stop)
    with pytest.raises(repository.RepositoryError) as error:
        repository.clone_repository("https://github.com/example/repo")
    assert error.value.status_code == 504
    stop.assert_called_once_with(process)
    assert not clone.exists()


@pytest.mark.parametrize("limit", [
    "MAX_REPOSITORY_BYTES", "MAX_REPOSITORY_FILES", "MAX_PYTHON_FILES",
    "MAX_PYTHON_FILE_BYTES", "MAX_PYTHON_BYTES",
])
def test_large_repositories_rejected_and_cleaned(clone_setup, monkeypatch, limit):
    clone, _, _ = clone_setup
    (clone / "app.py").write_text("x = 1", encoding="utf-8")
    monkeypatch.setattr(repository, limit, 0)
    with pytest.raises(repository.RepositoryError) as error:
        repository.clone_repository("https://github.com/example/repo")
    assert error.value.status_code == 413
    assert not clone.exists()


def test_size_checked_while_clone_is_running(clone_setup, monkeypatch):
    clone, process, _ = clone_setup
    (clone / "large.bin").write_bytes(b"large")
    process.poll.return_value = None
    monkeypatch.setattr(repository, "MAX_REPOSITORY_BYTES", 1)
    stop = Mock()
    monkeypatch.setattr(repository, "stop_clone", stop)
    with pytest.raises(repository.RepositoryError):
        repository.clone_repository("https://github.com/example/repo")
    stop.assert_called_once_with(process)
    assert not clone.exists()


def test_symlink_files_are_not_analyzed(tmp_path, monkeypatch):
    (tmp_path / "linked.py").write_text("secret", encoding="utf-8")
    (tmp_path / "normal.py").write_text("x = 1", encoding="utf-8")
    # Windows often restricts creating symlinks; simulate their filesystem flag.
    monkeypatch.setattr(Path, "is_symlink", lambda path: path.name == "linked.py")
    assert repository.discover_python_files(str(tmp_path)) == ["normal.py"]


def test_readonly_git_object_is_removed(tmp_path):
    clone = tmp_path / "clone"
    clone.mkdir()
    path = clone / "readonly"
    path.write_bytes(b"object")
    path.chmod(0o444)
    repository.cleanup_repository(str(clone))
    assert not clone.exists()


def test_invalid_url_never_starts_git(clone_setup):
    _, _, popen = clone_setup
    with pytest.raises(ValueError):
        repository.clone_repository("https://example.com/repo")
    popen.assert_not_called()


@pytest.mark.parametrize("platform", ["nt", "posix"])
def test_stopping_clone_terminates_children_and_waits(monkeypatch, platform):
    process = Mock(pid=12345)
    process.poll.return_value = None
    kill_group = Mock()
    monkeypatch.setattr(repository, "os", SimpleNamespace(name=platform, killpg=kill_group))
    monkeypatch.setattr(repository, "signal", SimpleNamespace(SIGKILL=9))
    command = Mock()
    monkeypatch.setattr(repository.subprocess, "run", command)
    repository.stop_clone(process)
    if platform == "nt":
        assert command.call_args.args[0] == ["taskkill", "/PID", "12345", "/T", "/F"]
    else:
        kill_group.assert_called_once_with(12345, repository.signal.SIGKILL)
    process.wait.assert_called_once_with(timeout=10)
