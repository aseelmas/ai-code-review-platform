from fastapi import FastAPI
from backend.models import AnalyzeRepositoryRequest

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
    return {
        "repository": str(request.repo_url),
        "status": "ready for analysis",
    }