import os

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from fastapi.middleware.cors import CORSMiddleware

from backend.models import (
    AnalyzeRepositoryRequest,
    AIReviewRequest,
    AnalyzeDiffRequest,
)
from backend.diff_analyzer import analyze_diff
from backend.config import get_cors_origins

from backend.ai_reviewer import (
    generate_ai_review, AI_UNAVAILABLE_MESSAGE, MAX_AI_REVIEWS,
)
from backend.repository import RepositoryError, cleanup_repository

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(RequestValidationError)
async def validation_error(request, error):
    # Do not echo rejected input, which could contain credentials or source code.
    return JSONResponse(status_code=422, content={"detail": [
        {"loc": item["loc"], "msg": item["msg"], "type": item["type"]}
        for item in error.errors()
    ]})


@app.get("/")
def home():
    return {"message": "AI Code Review Platform is running"}


@app.post("/analyze")
def analyze_repository(request: AnalyzeRepositoryRequest):
    repo_path = None

    try:
        repo_path, python_files = clone_repository(str(request.repo_url))

        analyzed_files = []
        skipped_files = []
        warnings = []

        for relative_path in python_files:
            full_path = os.path.join(repo_path, relative_path)

            try:
                result = analyze_python_file(full_path)
                issues = detect_code_issues(full_path)

                for issue in issues:
                    issue["code_context"] = get_code_context(
                        full_path,
                        issue["line"],
                    )[:12000]

                analyzed_files.append({
                    "file": relative_path,
                    "functions": result["functions"],
                    "classes": result["classes"],
                    "imports": result["imports"],
                    "issues": issues,
                })

            except (SyntaxError, UnicodeDecodeError, ValueError, RecursionError):
                skipped_files.append({"file": relative_path, "reason": "Invalid or unsupported Python source."})
                continue

        if not python_files:
            warnings.append("No Python files found. This repository cannot currently be analyzed.")
        elif skipped_files:
            warnings.append("Some Python files could not be analyzed. The health score is unavailable for this partial analysis.")

        if request.include_ai_review:
            important_issues = sorted(
                (issue for file in analyzed_files for issue in file["issues"]
                 if issue["severity"] in {"high", "medium"}),
                key=lambda issue: issue["score"], reverse=True,
            )[:MAX_AI_REVIEWS]
            for issue in important_issues:
                try:
                    issue["ai_review"] = generate_ai_review(issue)
                except Exception:
                    issue["ai_error"] = AI_UNAVAILABLE_MESSAGE
                    warnings.append(AI_UNAVAILABLE_MESSAGE)
                    # Stop further calls when the provider is unavailable/rate limited.
                    break

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

        all_issues.sort(
            key=lambda issue: issue["score"],
            reverse=True,
        )

        top_issues = all_issues[:10]

        health_score = (
            calculate_health_score(all_issues)
            if analyzed_files and not skipped_files
            else None
        )

        return {
            "repository": str(request.repo_url),
            "python_files_count": len(python_files),
            "analyzed_files_count": len(analyzed_files),
            "skipped_files": skipped_files,
            "warnings": warnings,
            "health_score": health_score,
            "summary": {
                "total_issues": total_issues,
                "severity_counts": severity_counts,
            },
            "top_issues": top_issues,
            "files": analyzed_files,
        }

    except RepositoryError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from None
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Repository analysis failed. Please try again later.",
        ) from None

    finally:
        if repo_path and os.path.exists(repo_path):
            cleanup_repository(repo_path)


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

    except Exception:
        raise HTTPException(
            status_code=503,
            detail=AI_UNAVAILABLE_MESSAGE,
        ) from None


@app.post("/analyze-diff")
def review_code_diff(request: AnalyzeDiffRequest):
    return analyze_diff(request.files)
