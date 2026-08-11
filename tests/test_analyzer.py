import tempfile
from pathlib import Path

from backend.analyzer import detect_code_issues


def analyze_code(code: str):
    """
    Helper function:
    creates a temporary Python file and analyzes it.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        file_path = Path(temp_dir) / "test_file.py"
        file_path.write_text(code, encoding="utf-8")

        return detect_code_issues(str(file_path))


def test_detects_bare_except():
    code = """
try:
    risky_operation()
except:
    print("Something went wrong")
"""

    issues = analyze_code(code)

    rules = [issue["rule"] for issue in issues]

    assert "bare-except" in rules


def test_detects_silent_exception():
    code = """
try:
    risky_operation()
except ValueError:
    pass
"""

    issues = analyze_code(code)

    rules = [issue["rule"] for issue in issues]

    assert "silent-exception" in rules


def test_detects_print_statement():
    code = """
def hello():
    print("Hello")
"""

    issues = analyze_code(code)

    rules = [issue["rule"] for issue in issues]

    assert "print-statement" in rules


def test_clean_code_has_no_issues():
    code = """
import logging

def divide(a, b):
    try:
        return a / b
    except ZeroDivisionError:
        logging.error("Cannot divide by zero")
"""

    issues = analyze_code(code)

    assert issues == []

def test_bare_except_with_pass_is_not_reported_twice():
    code = """
try:
    risky_operation()
except:
    pass
"""

    issues = analyze_code(code)

    rules = [issue["rule"] for issue in issues]

    assert rules.count("bare-except") == 1
    assert "silent-exception" not in rules