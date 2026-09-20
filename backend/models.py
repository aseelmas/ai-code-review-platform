from typing import Literal

from pydantic import BaseModel, Field, field_validator

from backend.repository import validate_repository_url


class AnalyzeRepositoryRequest(BaseModel):
    repo_url: str = Field(min_length=1, max_length=300)
    include_ai_review: bool = False

    @field_validator("repo_url")
    @classmethod
    def github_repository(cls, value: str) -> str:
        return validate_repository_url(value)


class AIReviewRequest(BaseModel):
    rule: str = Field(min_length=1, max_length=100)
    severity: Literal["high", "medium", "low"]
    line: int = Field(ge=1)
    message: str = Field(min_length=1, max_length=2000)
    code_context: str = Field(default="", max_length=12000)


class DiffFile(BaseModel):
    # Paths are display labels only; they are never opened on the server.
    file: str = Field(min_length=1, max_length=500)
    before: str = Field(max_length=100_000)
    after: str = Field(max_length=100_000)

    @field_validator("file")
    @classmethod
    def validate_file(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("File name must not be blank")
        return value


class AnalyzeDiffRequest(BaseModel):
    files: list[DiffFile] = Field(min_length=1, max_length=20)

    @field_validator("files")
    @classmethod
    def unique_files(cls, files: list[DiffFile]) -> list[DiffFile]:
        names = [file.file for file in files]
        if len(names) != len(set(names)):
            raise ValueError("File names must be unique")
        return files
