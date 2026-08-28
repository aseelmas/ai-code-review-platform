import ast
import os
import shutil
import subprocess
import tempfile


SEVERITY_SCORES = {
    "high": 3,
    "medium": 2,
    "low": 1,
}


def clone_repository(repo_url: str) -> tuple[str, list[str]]:
    temp_dir = tempfile.mkdtemp()

    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, temp_dir],
            check=True,
            capture_output=True,
            text=True,
        )

        python_files = []

        for root, _, files in os.walk(temp_dir):
            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    relative_path = os.path.relpath(full_path, temp_dir)
                    python_files.append(relative_path)

        return temp_dir, python_files

    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


def analyze_python_file(file_path: str) -> dict:
    with open(file_path, "r", encoding="utf-8") as file:
        source_code = file.read()

    tree = ast.parse(source_code)

    functions = []
    classes = []
    imports = []

    # Inspect only top-level elements
    for node in tree.body:

        # Top-level function
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append({
                "name": node.name,
                "line": node.lineno,
            })

        # Class
        elif isinstance(node, ast.ClassDef):
            methods = []

            for class_node in node.body:
                if isinstance(
                    class_node,
                    (ast.FunctionDef, ast.AsyncFunctionDef),
                ):
                    methods.append({
                        "name": class_node.name,
                        "line": class_node.lineno,
                    })

            classes.append({
                "name": node.name,
                "line": node.lineno,
                "methods": methods,
            })

        # import os
        elif isinstance(node, ast.Import):
            for name in node.names:
                imports.append(name.name)

        # from fastapi import FastAPI
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)

    return {
        "functions": functions,
        "classes": classes,
        "imports": imports,
    }


def detect_code_issues(file_path: str) -> list[dict]:
    with open(file_path, "r", encoding="utf-8") as file:
        source_code = file.read()

    tree = ast.parse(source_code)

    issues = []

    for node in ast.walk(tree):

        # Rule 1: bare except
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            issues.append({
                "rule": "bare-except",
                "severity": "high",
                "line": node.lineno,
                "message": (
                    "Bare except catches all exceptions, including "
                    "unexpected system-level exceptions."
                ),
            })

        # Rule 2: specific exception handler containing only pass
        elif isinstance(node, ast.ExceptHandler):
            if (
                len(node.body) == 1
                and isinstance(node.body[0], ast.Pass)
            ):
                issues.append({
                    "rule": "silent-exception",
                    "severity": "medium",
                    "line": node.lineno,
                    "message": (
                        "Exception is silently ignored. "
                        "Verify that this behavior is intentional."
                    ),
                })

        # Rule 3: print()
        if isinstance(node, ast.Call):
            if (
                isinstance(node.func, ast.Name)
                and node.func.id == "print"
            ):
                issues.append({
                    "rule": "print-statement",
                    "severity": "low",
                    "line": node.lineno,
                    "message": "Consider using logging instead of print().",
                })

        # Rule 4: eval() / exec()
        if isinstance(node, ast.Call):
            if (
                isinstance(node.func, ast.Name)
                and node.func.id in {"eval", "exec"}
            ):
                issues.append({
                    "rule": "dangerous-dynamic-execution",
                    "severity": "high",
                    "line": node.lineno,
                    "message": (
                        f"Use of {node.func.id}() can execute arbitrary Python code. "
                        "Avoid using it with untrusted input."
                    ),
                })

        # Rule 5: subprocess with shell=True
        if isinstance(node, ast.Call):
            is_subprocess_call = False

            # subprocess.run(...)
            # subprocess.Popen(...)
            # subprocess.call(...)
            if isinstance(node.func, ast.Attribute):
                if (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "subprocess"
                    and node.func.attr in {"run", "Popen", "call", "check_call", "check_output"}
                ):
                    is_subprocess_call = True

            if is_subprocess_call:
                for keyword in node.keywords:
                    if (
                        keyword.arg == "shell"
                        and isinstance(keyword.value, ast.Constant)
                        and keyword.value.value is True
                    ):
                        issues.append({
                            "rule": "subprocess-shell-true",
                            "severity": "high",
                            "line": node.lineno,
                            "message": (
                                "subprocess is executed with shell=True. "
                                "If command input is user-controlled, this may allow command injection."
                            ),
                        })

        # Rule 6: possible hard-coded secret
        if isinstance(node, ast.Assign):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                value = node.value.value

                sensitive_names = {
                    "password",
                    "passwd",
                    "pwd",
                    "api_key",
                    "apikey",
                    "secret",
                    "secret_key",
                    "token",
                    "access_token",
                    "auth_token",
                }

                for target in node.targets:
                    if isinstance(target, ast.Name):
                        variable_name = target.id.lower()

                        if (
                            variable_name in sensitive_names
                            and len(value.strip()) >= 6
                        ):
                            issues.append({
                                "rule": "hardcoded-secret",
                                "severity": "high",
                                "line": node.lineno,
                                "message": (
                                    f"Possible hard-coded secret in variable "
                                    f"'{target.id}'. Store sensitive values in "
                                    "environment variables or a secret manager."
                                ),
                            })
        # Rule 7: annotated hard-coded secret
        if isinstance(node, ast.AnnAssign):
            if (
                isinstance(node.target, ast.Name)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
            ):
                variable_name = node.target.id.lower()
                value = node.value.value

                sensitive_names = {
                    "password",
                    "passwd",
                    "pwd",
                    "api_key",
                    "apikey",
                    "secret",
                    "secret_key",
                    "token",
                    "access_token",
                    "auth_token",
                }

                if (
                    variable_name in sensitive_names
                    and len(value.strip()) >= 6
                ):
                    issues.append({
                        "rule": "hardcoded-secret",
                        "severity": "high",
                        "line": node.lineno,
                        "message": (
                            f"Possible hard-coded secret in variable "
                            f"'{node.target.id}'. Store sensitive values in "
                            "environment variables or a secret manager."
                        ),
                    })

    # Add numeric score
    for issue in issues:
        issue["score"] = SEVERITY_SCORES[issue["severity"]]

    # Highest priority issues first
    issues.sort(
        key=lambda issue: issue["score"],
        reverse=True,
    )

    return issues