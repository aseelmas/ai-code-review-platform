"""Review changed lines using the existing Python static-analysis rules."""

from difflib import SequenceMatcher

from backend.analyzer import (
    calculate_health_score,
    detect_source_issues,
    get_source_context,
)
from backend.models import DiffFile


def get_changed_lines(before: str, after: str) -> list[int]:
    """Return one-based added/replaced lines in the updated source.

    Deleted lines have no location in the updated file. Line-ending-only
    changes are ignored. Disable the popularity heuristic for repeated code.
    """
    matcher = SequenceMatcher(None, before.splitlines(), after.splitlines(), autojunk=False)
    return [
        line
        for operation, _, _, start, end in matcher.get_opcodes()
        if operation in {"insert", "replace"}
        for line in range(start + 1, end + 1)
    ]


def analyze_diff(files: list[DiffFile]) -> dict:
    results = []
    all_issues = []
    analyzed_count = 0
    python_count = 0

    for file in files:
        changed_lines = get_changed_lines(file.before, file.after)
        result = {
            "file": file.file,
            "changed_lines": changed_lines,
            "issues": [],
            "status": "skipped",
        }
        results.append(result)

        if not file.file.endswith(".py"):
            result["reason"] = "Only Python files are supported."
            continue

        python_count += 1
        if not changed_lines:
            result["reason"] = "No added or replaced lines to review."
            continue

        try:
            issues = detect_source_issues(file.after)
        except (SyntaxError, ValueError) as error:
            result.update(status="error", reason=f"Invalid updated Python source: {error}")
            continue

        changed = set(changed_lines)
        result["issues"] = [
            {**issue, "code_context": get_source_context(file.after, issue["line"])}
            for issue in issues
            if issue["line"] in changed
        ]
        result["status"] = "analyzed"
        analyzed_count += 1
        all_issues.extend({"file": file.file, **issue} for issue in result["issues"])

    all_issues.sort(key=lambda issue: issue["score"], reverse=True)
    return {
        "analysis_type": "diff",
        "python_files_count": python_count,
        "analyzed_files_count": analyzed_count,
        # A failed file must not make an incomplete review look healthy.
        "health_score": calculate_health_score(all_issues)
        if analyzed_count and not any(file["status"] == "error" for file in results)
        else None,
        "summary": {
            "total_issues": len(all_issues),
            "severity_counts": {
                severity: sum(issue["severity"] == severity for issue in all_issues)
                for severity in ("high", "medium", "low")
            },
        },
        "top_issues": all_issues[:10],
        "files": results,
    }
