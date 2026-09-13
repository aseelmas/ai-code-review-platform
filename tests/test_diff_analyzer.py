import pytest

from backend.diff_analyzer import analyze_diff, get_changed_lines
from backend.models import DiffFile


def review(before, after, file="example.py"):
    return analyze_diff([DiffFile(file=file, before=before, after=after)])


@pytest.mark.parametrize("before,after,expected", [
    ("", "x = 1\nprint(x)\n", [1, 2]),
    ("x = 1\n", "x = 2\n", [1]),
    ("print(1)\nx = 1\n", "x = 1\n", []),
    ("print(1)\n", "", []),
    ("x = 1\n", "x = 1\n", []),
    ("x = 1\r\n", "x = 1\n", []),
    ("x = 1", "x = 1\n", []),
    ("a\nb\nc\nd\n", "A\nb\nc\nD\n", [1, 4]),
])
def test_changed_line_mapping(before, after, expected):
    assert get_changed_lines(before, after) == expected


def test_repeated_lines_do_not_hide_small_change():
    before = "x = 1\n" * 250
    after = "x = 1\n" * 125 + "print(x)\n" + "x = 1\n" * 125
    assert get_changed_lines(before, after) == [126]


def test_unchanged_findings_are_excluded_even_when_shifted():
    result = review('print("existing")\n', 'x = 1\nprint("existing")\neval(x)\n')
    assert result["summary"] == {
        "total_issues": 1,
        "severity_counts": {"high": 1, "medium": 0, "low": 0},
    }
    issue = result["top_issues"][0]
    assert issue["rule"] == "dangerous-dynamic-execution"
    assert issue["line"] == 3
    assert issue["file"] == "example.py"
    assert "3: eval(x)" in issue["code_context"]
    assert result["health_score"] == 90


def test_full_source_is_parsed_for_indented_changes():
    result = review("def f():\n    return 1\n", "def f():\n    print(1)\n")
    assert result["top_issues"][0]["line"] == 2


def test_existing_issue_on_replaced_line_is_reported():
    result = review("print(1)\n", "print(2)\n")
    assert result["summary"]["total_issues"] == 1


def test_issue_start_line_scope_is_explicit():
    # The existing detector anchors the call to line 1, which is unchanged.
    result = review("subprocess.run(\n    cmd, shell=False\n)\n",
                    "subprocess.run(\n    cmd, shell=True\n)\n")
    assert result["files"][0]["changed_lines"] == [2]
    assert result["summary"]["total_issues"] == 0


@pytest.mark.parametrize("before,after", [
    ("print(1)\n", "print(1)\n"),
    ("print(1)\n", ""),
    ("print(1)\nx = 1\n", "x = 1\n"),
])
def test_no_reviewable_lines_have_no_score(before, after):
    result = review(before, after)
    assert result["health_score"] is None
    assert result["analyzed_files_count"] == 0
    assert result["files"][0]["status"] == "skipped"


def test_non_python_is_skipped_without_parsing():
    result = review("", "not python!", "README.md")
    assert result["python_files_count"] == 0
    assert result["files"][0]["status"] == "skipped"
    assert result["health_score"] is None


def test_invalid_after_does_not_prevent_other_file_reviews():
    result = analyze_diff([
        DiffFile(file="broken.py", before="", after="def broken(:"),
        DiffFile(file="good.py", before="", after="print(1)"),
    ])
    assert result["files"][0]["status"] == "error"
    assert "Invalid updated Python source" in result["files"][0]["reason"]
    assert result["files"][1]["status"] == "analyzed"
    assert result["analyzed_files_count"] == 1
    assert result["summary"]["total_issues"] == 1
    assert result["health_score"] is None


def test_invalid_before_can_be_fixed():
    result = review("def broken(:", "x = 1")
    assert result["files"][0]["status"] == "analyzed"
    assert result["health_score"] == 100


def test_priority_and_top_ten_use_only_changed_findings():
    result = review("", 'print(1)\n' * 12 + 'eval("1")\n')
    assert result["summary"]["total_issues"] == 13
    assert len(result["top_issues"]) == 10
    assert result["top_issues"][0]["severity"] == "high"
    assert result["health_score"] == 66
