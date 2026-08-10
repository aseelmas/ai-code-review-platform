import os

from fastapi import FastAPI, HTTPException

from backend.models import AnalyzeRepositoryRequest
from backend.analyzer import (
    clone_repository,
    analyze_python_file,
    detect_code_issues,
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

                analyzed_files.append({
                    "file": relative_path,
                    "functions": result["functions"],
                    "classes": result["classes"],
                    "imports": result["imports"],
                    "issues": issues,
                })

            except (SyntaxError, UnicodeDecodeError):
                continue

        return {
            "repository": str(request.repo_url),
            "python_files_count": len(python_files),
            "analyzed_files_count": len(analyzed_files),
            "files": analyzed_files,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Repository analysis failed: {str(e)}",
        )