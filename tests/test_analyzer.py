import tempfile
from pathlib import Path

from backend.analyzer import (
    detect_code_issues,
    calculate_health_score,
)

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

def test_detects_eval():
    code = """
user_input = input("Expression: ")
result = eval(user_input)
"""

    issues = analyze_code(code)

    rules = [issue["rule"] for issue in issues]

    assert "dangerous-dynamic-execution" in rules


def test_detects_exec():
    code = """
code = "print('hello')"
exec(code)
"""

    issues = analyze_code(code)

    rules = [issue["rule"] for issue in issues]

    assert "dangerous-dynamic-execution" in rules

def test_safe_function_call_not_flagged_as_dynamic_execution():
    code = """
def calculate(a, b):
    return a + b

result = calculate(2, 3)
"""

    issues = analyze_code(code)

    rules = [issue["rule"] for issue in issues]

    assert "dangerous-dynamic-execution" not in rules

def test_detects_subprocess_shell_true():
    code = """
import subprocess

command = input("Command: ")
subprocess.run(command, shell=True)
"""

    issues = analyze_code(code)

    rules = [issue["rule"] for issue in issues]

    assert "subprocess-shell-true" in rules


def test_detects_popen_shell_true():
    code = """
import subprocess

command = "echo hello"
subprocess.Popen(command, shell=True)
"""

    issues = analyze_code(code)

    rules = [issue["rule"] for issue in issues]

    assert "subprocess-shell-true" in rules


def test_safe_subprocess_not_flagged():
    code = """
import subprocess

subprocess.run(["git", "status"])
"""

    issues = analyze_code(code)

    rules = [issue["rule"] for issue in issues]

    assert "subprocess-shell-true" not in rules

def test_detects_hardcoded_password():
    code = """
password = "super-secret-password"
"""

    issues = analyze_code(code)

    rules = [issue["rule"] for issue in issues]

    assert "hardcoded-secret" in rules


def test_detects_hardcoded_api_key():
    code = """
api_key = "example-api-key-value"
"""

    issues = analyze_code(code)

    rules = [issue["rule"] for issue in issues]

    assert "hardcoded-secret" in rules


def test_normal_string_is_not_flagged_as_secret():
    code = """
username = "aseel"
project_name = "code-review-platform"
"""

    issues = analyze_code(code)

    rules = [issue["rule"] for issue in issues]

    assert "hardcoded-secret" not in rules


def test_environment_variable_secret_is_not_flagged():
    code = """
import os

api_key = os.getenv("API_KEY")
"""

    issues = analyze_code(code)

    rules = [issue["rule"] for issue in issues]

    assert "hardcoded-secret" not in rules

def test_detects_annotated_hardcoded_secret():
    code = """
api_key: str = "my-secret-api-key"
"""

    issues = analyze_code(code)

    rules = [issue["rule"] for issue in issues]

    assert "hardcoded-secret" in rules


def test_hardcoded_secret_has_high_severity():
    code = """
password = "very-secret-password"
"""

    issues = analyze_code(code)

    secret_issue = next(
        issue for issue in issues
        if issue["rule"] == "hardcoded-secret"
    )

    assert secret_issue["severity"] == "high"
    assert secret_issue["score"] == 3


def test_print_statement_has_low_score():
    code = """
print("debug")
"""

    issues = analyze_code(code)

    print_issue = next(
        issue for issue in issues
        if issue["rule"] == "print-statement"
    )

    assert print_issue["severity"] == "low"
    assert print_issue["score"] == 1


def test_issue_line_number_is_correct():
    code = """
x = 10
y = 20
print("debug")
"""

    issues = analyze_code(code)

    print_issue = next(
        issue for issue in issues
        if issue["rule"] == "print-statement"
    )

    assert print_issue["line"] == 4


def test_password_text_inside_message_is_not_secret():
    code = """
message = "Please enter your password"
"""

    issues = analyze_code(code)

    rules = [issue["rule"] for issue in issues]

    assert "hardcoded-secret" not in rules


def test_short_secret_value_is_not_flagged():
    code = """
password = "123"
"""

    issues = analyze_code(code)

    rules = [issue["rule"] for issue in issues]

    assert "hardcoded-secret" not in rules


def test_subprocess_without_shell_true_is_safe():
    code = """
import subprocess

subprocess.run(["echo", "hello"], shell=False)
"""

    issues = analyze_code(code)

    rules = [issue["rule"] for issue in issues]

    assert "subprocess-shell-true" not in rules


def test_health_score_no_issues():
    issues = []

    score = calculate_health_score(issues)

    assert score == 100


def test_health_score_low_issue():
    issues = [
        {"severity": "low"}
    ]

    score = calculate_health_score(issues)

    assert score == 98


def test_health_score_mixed_issues():
    issues = [
        {"severity": "high"},
        {"severity": "medium"},
        {"severity": "low"},
    ]

    score = calculate_health_score(issues)

    assert score == 83


def test_health_score_never_below_zero():
    issues = [
        {"severity": "high"}
        for _ in range(20)
    ]

    score = calculate_health_score(issues)

    assert score == 0