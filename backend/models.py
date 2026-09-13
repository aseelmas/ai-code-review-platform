from pydantic import BaseModel, Field, HttpUrl, field_validator


class AnalyzeRepositoryRequest(BaseModel):
    repo_url: HttpUrl


class AIReviewRequest(BaseModel):
    rule: str
    severity: str
    line: int
    message: str
    code_context: str = ""


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
