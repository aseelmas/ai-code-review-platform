import os

from fastapi import FastAPI, HTTPException

from backend.models import (
    AnalyzeRepositoryRequest,
    AIReviewRequest,
)

from backend.ai_reviewer import generate_ai_review

from backend.analyzer import (
    clone_repository,
    analyze_python_file,
    detect_code_issues,
    calculate_health_score,
    get_code_context,
)

app = FastAPI(
    title="AI Code Review Platform",
    description="API for automated code analysis and AI-powered code review",
    version="0.1.0",
)


@app.get("/")
def home():
    return {"message": "AI Code Review Platform is running"}


@app.post("/analyze")
def analyze_repository(request: AnalyzeRepositoryRequest):
    try:
        repo_path, python_files = clone_repository(str(request.repo_url))

        analyzed_files = []

        for relative_path in python_files:
            full_path = os.path.join(repo_path, relative_path)

            try:
                result = analyze_python_file(full_path)
                issues = detect_code_issues(full_path)

                for issue in issues:
                    issue["code_context"] = get_code_context(
                        full_path,
                        issue["line"],
                    )

                analyzed_files.append({
                    "file": relative_path,
                    "functions": result["functions"],
                    "classes": result["classes"],
                    "imports": result["imports"],
                    "issues": issues,
                })

            except (SyntaxError, UnicodeDecodeError):
                continue

        total_issues = 0

        severity_counts = {
            "high": 0,
            "medium": 0,
            "low": 0,
        }

        all_issues = []

        for file_result in analyzed_files:
            for issue in file_result["issues"]:
                total_issues += 1

                severity = issue["severity"]

                if severity in severity_counts:
                    severity_counts[severity] += 1

                all_issues.append({
                    "file": file_result["file"],
                    **issue,
                })

        # Sort all repository issues by risk score
        all_issues.sort(
            key=lambda issue: issue["score"],
            reverse=True,
        )

        # Keep only the 10 highest-priority issues
        top_issues = all_issues[:10]

        health_score = calculate_health_score(all_issues)

        return {
            "repository": str(request.repo_url),
            "python_files_count": len(python_files),
            "analyzed_files_count": len(analyzed_files),
            "health_score": health_score,

            "summary": {
                "total_issues": total_issues,
                "severity_counts": severity_counts,
            },

            "top_issues": top_issues,

            "files": analyzed_files,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Repository analysis failed: {str(e)}",
        )


@app.post("/ai-review")
def ai_review(request: AIReviewRequest):
    try:
        issue = {
            "rule": request.rule,
            "severity": request.severity,
            "line": request.line,
            "message": request.message,
            "code_context": request.code_context,
        }

        review = generate_ai_review(issue)

        return {
            "issue": issue,
            "ai_review": review,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI review failed: {str(e)}",
        )