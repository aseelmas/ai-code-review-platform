import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from openai import APIConnectionError, APITimeoutError, RateLimitError

from backend.ai_reviewer import AIReviewUnavailable, generate_ai_review
from backend.main import app


ISSUE = {
    "rule": "dangerous-dynamic-execution", "severity": "high", "line": 1,
    "message": "Avoid eval.", "code_context": "1: eval(user_input)",
}
REVIEW = {
    "explanation": "This evaluates untrusted Python.",
    "risk": "An attacker can run arbitrary code.",
    "recommendation": "Parse data instead of evaluating code.",
    "suggested_fix": "value = json.loads(user_input)",
}


@pytest.fixture
def sdk(monkeypatch):
    constructor = MagicMock()
    client = constructor.return_value.__enter__.return_value
    client.responses.create.return_value = SimpleNamespace(
        status="completed", output_text=json.dumps(REVIEW),
    )
    monkeypatch.setattr("backend.ai_reviewer.OpenAI", constructor)
    return constructor, client


def test_ai_review_success_uses_bounded_structured_output(sdk, monkeypatch):
    constructor, client = sdk
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    assert generate_ai_review(ISSUE) == REVIEW
    constructor.assert_called_once_with(api_key="test-only-not-a-real-key", timeout=20.0, max_retries=0)
    payload = client.responses.create.call_args.kwargs
    assert payload["model"] == "test-model"
    assert payload["store"] is False
    assert payload["text"]["format"]["strict"] is True
    assert json.loads(payload["input"])["code_context"] == ISSUE["code_context"]
    assert "test-only-not-a-real-key" not in payload["input"]
    constructor.return_value.__exit__.assert_called_once()


def test_missing_key_does_not_contact_openai(sdk, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(AIReviewUnavailable):
        generate_ai_review(ISSUE)
    sdk[0].assert_not_called()


@pytest.mark.parametrize("output", [
    "", "not JSON", "null", "[]", "{}", '{"explanation": 123}',
    json.dumps({**REVIEW, "risk": ""}), json.dumps({**REVIEW, "extra": "field"}),
])
def test_invalid_output_is_never_returned(sdk, output):
    sdk[1].responses.create.return_value.output_text = output
    with pytest.raises(ValidationError):
        generate_ai_review(ISSUE)


def test_incomplete_response_is_not_used(sdk):
    sdk[1].responses.create.return_value.status = "incomplete"
    with pytest.raises(AIReviewUnavailable):
        generate_ai_review(ISSUE)


def test_api_success_with_mocked_sdk(sdk):
    response = TestClient(app).post("/ai-review", json=ISSUE)
    assert response.status_code == 200
    assert response.json()["ai_review"] == REVIEW


@pytest.mark.parametrize("failure", [TimeoutError("private-key"), RuntimeError("private-key")])
def test_api_failure_returns_safe_fallback(sdk, failure):
    sdk[1].responses.create.side_effect = failure
    response = TestClient(app).post("/ai-review", json=ISSUE)
    assert response.status_code == 503
    assert "Static analysis results are still available" in response.json()["detail"]
    assert "private-key" not in response.text


def test_malformed_ai_response_is_safe_at_api_boundary(sdk):
    sdk[1].responses.create.return_value.output_text = "internal secret error"
    response = TestClient(app).post("/ai-review", json=ISSUE)
    assert response.status_code == 503
    assert "internal secret" not in response.text


def test_context_is_bounded(sdk):
    generate_ai_review({**ISSUE, "code_context": "x" * 20000})
    assert len(json.loads(sdk[1].responses.create.call_args.kwargs["input"])["code_context"]) == 12000


@pytest.mark.parametrize("failure", [
    APIConnectionError(request=MagicMock()),
    APITimeoutError(request=MagicMock()),
    RateLimitError("provider-private-details", response=MagicMock(status_code=429), body=None),
])
def test_openai_sdk_failures_are_sanitized(sdk, failure):
    sdk[1].responses.create.side_effect = failure
    response = TestClient(app).post("/ai-review", json=ISSUE)
    assert response.status_code == 503
    assert "provider-private-details" not in response.text
