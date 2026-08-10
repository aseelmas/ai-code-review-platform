import ast
import os
import shutil
import subprocess
import tempfile


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

    # Only inspect top-level elements of the file
    for node in tree.body:

        # Top-level function
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append({
                "name": node.name,
                "line": node.lineno
            })

        # Class
        elif isinstance(node, ast.ClassDef):
            methods = []

            for class_node in node.body:
                if isinstance(
                    class_node,
                    (ast.FunctionDef, ast.AsyncFunctionDef)
                ):
                    methods.append({
                        "name": class_node.name,
                        "line": class_node.lineno
                    })

            classes.append({
                "name": node.name,
                "line": node.lineno,
                "methods": methods
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
        "imports": imports
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
                "severity": "medium",
                "line": node.lineno,
                "message": "Bare except catches every exception."
            })

        # Rule 2: exception handler that only contains pass
        if isinstance(node, ast.ExceptHandler):
            if (
                len(node.body) == 1
                and isinstance(node.body[0], ast.Pass)
            ):
                issues.append({
                    "rule": "empty-except",
                    "severity": "high",
                    "line": node.lineno,
                    "message": "Exception is silently ignored."
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
                    "message": "Consider using logging instead of print()."
                })

    return issues