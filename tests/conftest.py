from unittest.mock import Mock

import pytest


@pytest.fixture(autouse=True)
def block_real_openai(monkeypatch):
    """Every test must explicitly replace the SDK to exercise AI calls."""
    constructor = Mock(side_effect=AssertionError("Real OpenAI calls are forbidden in tests"))
    monkeypatch.setattr("backend.ai_reviewer.OpenAI", constructor)
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-not-a-real-key")
    return constructor
