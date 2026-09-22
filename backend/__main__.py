"""Production entry point: python -m backend (run from the repository root)."""

import uvicorn

from backend.config import get_cors_origins, get_positive_integer, load_environment


def main() -> None:
    load_environment()
    get_cors_origins()  # Fail early on invalid deployment configuration.
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=get_positive_integer("PORT", 8000, 65535),
        workers=1,
        reload=False,
        limit_concurrency=get_positive_integer("LIMIT_CONCURRENCY", 8, 1000),
        timeout_graceful_shutdown=30,
    )


if __name__ == "__main__":
    main()
