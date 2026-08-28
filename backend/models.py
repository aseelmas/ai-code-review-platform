from pydantic import BaseModel, HttpUrl


class AnalyzeRepositoryRequest(BaseModel):
    repo_url: HttpUrl


class AIReviewRequest(BaseModel):
    rule: str
    severity: str
    line: int
    message: str
    code_context: str = ""