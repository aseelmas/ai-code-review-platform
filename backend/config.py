"""Environment configuration shared by local development and deployment."""

import os
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv


def get_environment() -> str:
    environment = os.getenv("APP_ENV", "development").strip().lower()
    if environment not in {"development", "production"}:
        raise ValueError("APP_ENV must be development or production.")
    return environment


def load_environment() -> None:
    # Hosted deployments use injected variables, never a file baked into an image.
    if get_environment() == "development":
        load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)


def get_cors_origins() -> list[str]:
    load_environment()
    production = get_environment() == "production"
    default = "" if production else "http://localhost:5173,http://127.0.0.1:5173"
    raw = os.getenv("CORS_ORIGINS", default)
    origins = []
    for value in raw.split(","):
        origin = value.strip().rstrip("/")
        if not origin:
            continue
        try:
            parsed = urlsplit(origin)
            valid = (
                parsed.scheme in ({"https"} if production else {"http", "https"})
                and parsed.hostname and parsed.netloc
                and parsed.username is None and parsed.password is None
                and not parsed.path and not parsed.query and not parsed.fragment
                and "*" not in origin and not any(char.isspace() for char in origin)
            )
            parsed.port  # Validate malformed/out-of-range ports too.
        except ValueError:
            valid = False
        if not valid:
            raise ValueError("CORS_ORIGINS must contain exact origins without paths or wildcards; production requires HTTPS.")
        normalized = f"{parsed.scheme}://{parsed.netloc.lower()}"
        if normalized not in origins:
            origins.append(normalized)
    return origins


def get_positive_integer(name: str, default: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        raise ValueError(f"{name} must be a positive integer up to {maximum}.") from None
    if not 1 <= value <= maximum:
        raise ValueError(f"{name} must be a positive integer up to {maximum}.")
    return value
