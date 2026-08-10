from pydantic import BaseModel, HttpUrl


class AnalyzeRepositoryRequest(BaseModel):
    repo_url: HttpUrl