from fastapi.testclient import TestClient
import pytest

from backend.main import app
from backend.repository import RepositoryError
from unittest.mock import Mock


client = TestClient(app)


def test_diff_endpoint():
    response = client.post("/analyze-diff", json={"files": [
        {"file": "app.py", "before": "x = 1\n", "after": "x = 1\nprint(x)\n"},
    ]})
    assert response.status_code == 200
    data = response.json()
    assert data["analysis_type"] == "diff"
    assert data["files"][0]["changed_lines"] == [2]
    assert data["top_issues"][0]["line"] == 2
    assert data["health_score"] == 98


@pytest.mark.parametrize("payload", [
    {},
    {"files": []},
    {"files": [{"file": "x.py", "after": ""}]},
    {"files": [{"file": "  ", "before": "", "after": ""}]},
    {"files": [{"file": "x.py", "before": "", "after": None}]},
    {"files": [{"file": "x.py", "before": "", "after": "x" * 100001}]},
    {"files": [{"file": "x.py", "before": "", "after": ""}] * 2},
    {"files": [{"file": f"{i}.py", "before": "", "after": ""} for i in range(21)]},
])
def test_diff_rejects_invalid_requests(payload):
    assert client.post("/analyze-diff", json=payload).status_code == 422


def test_syntax_error_is_visible_in_api_result():
    response = client.post("/analyze-diff", json={"files": [
        {"file": "x.py", "before": "", "after": "def (:"},
    ]})
    assert response.status_code == 200
    assert response.json()["files"][0]["status"] == "error"
    assert response.json()["health_score"] is None


def test_repository_analysis_still_returns_structure_and_cleans_up(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("import os\ndef f():\n    print(1)\n", encoding="utf-8")
    monkeypatch.setattr("backend.main.clone_repository", lambda url: (str(repo), ["app.py"]))
    response = client.post("/analyze", json={"repo_url": "https://github.com/example/repo"})
    assert response.status_code == 200
    result = response.json()
    assert result["files"][0]["functions"] == [{"name": "f", "line": 2}]
    assert result["files"][0]["imports"] == ["os"]
    assert result["summary"]["total_issues"] == 1
    assert result["health_score"] == 98
    assert not repo.exists()


def test_repository_without_python_files_has_no_score(tmp_path, monkeypatch):
    repo = tmp_path / "empty"
    repo.mkdir()
    monkeypatch.setattr("backend.main.clone_repository", lambda url: (str(repo), []))
    response = client.post("/analyze", json={"repo_url": "https://github.com/example/repo"})
    assert response.status_code == 200
    assert response.json()["health_score"] is None
    assert not repo.exists()


def test_ai_review_accepts_diff_finding(monkeypatch):
    monkeypatch.setattr("backend.main.generate_ai_review", lambda issue: {"explanation": issue["code_context"]})
    result = client.post("/analyze-diff", json={"files": [
        {"file": "app.py", "before": "", "after": "print(1)"},
    ]}).json()
    response = client.post("/ai-review", json=result["top_issues"][0])
    assert response.status_code == 200
    assert response.json()["ai_review"]["explanation"] == "1: print(1)"


@pytest.mark.parametrize("url", [
    "not a url", "https://example.com/owner/repo", "http://github.com/owner/repo",
    "https://github.com.evil.test/owner/repo", "https://github.com/owner",
    "https://github.com/owner/repo/tree/main", "https://github.com/owner/repo?token=hidden",
    "https://github.com/owner/repo#fragment", "https://github.com:8443/owner/repo",
    "https://user:hidden@github.com/owner/repo", "file:///tmp/repo",
    "git@github.com:owner/repo.git", "https://github.com/owner/../repo",
    "https://github.com/owner/%2e%2e", "https://github.com/owner/..",
    "https://github.com/owner/repo\n--upload-pack=evil",
])
def test_invalid_repository_url_is_rejected_before_cloning(monkeypatch, url):
    clone = Mock()
    monkeypatch.setattr("backend.main.clone_repository", clone)
    response = client.post("/analyze", json={"repo_url": url})
    assert response.status_code == 422
    assert "hidden" not in response.text
    assert "input" not in response.json()["detail"][0]
    clone.assert_not_called()


@pytest.mark.parametrize("url", [
    "https://github.com/owner/repo", "https://github.com/owner/repo.git",
    "https://github.com/owner/repo/", " https://GitHub.com/owner/repo ",
])
def test_valid_github_url_forms(monkeypatch, tmp_path, url):
    clone = tmp_path / "clone"
    clone.mkdir()
    mock = Mock(return_value=(str(clone), []))
    monkeypatch.setattr("backend.main.clone_repository", mock)
    response = client.post("/analyze", json={"repo_url": url})
    assert response.status_code == 200
    assert mock.call_args.args[0].startswith("https://github.com/")
    assert response.json()["warnings"]
    assert not clone.exists()


@pytest.mark.parametrize("status", [413, 502, 504])
def test_expected_repository_failure_has_safe_status(monkeypatch, status):
    monkeypatch.setattr("backend.main.clone_repository", Mock(side_effect=RepositoryError("Safe message", status)))
    response = client.post("/analyze", json={"repo_url": "https://github.com/owner/repo"})
    assert response.status_code == status
    assert response.json()["detail"] == "Safe message"


def test_unexpected_clone_failure_does_not_leak_internal_details(monkeypatch):
    monkeypatch.setattr("backend.main.clone_repository", Mock(side_effect=RuntimeError("secret /internal/path")))
    response = client.post("/analyze", json={"repo_url": "https://github.com/owner/repo"})
    assert response.status_code == 500
    assert "secret" not in response.text
    assert "/internal/path" not in response.text


@pytest.fixture
def important_repo(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text('print(1)\neval("1")\nexec("x = 1")\neval("2")\neval("3")\n', encoding="utf-8")
    monkeypatch.setattr("backend.main.clone_repository", lambda url: (str(repo), ["app.py"]))
    return repo


def test_ai_opt_in_reviews_at_most_three_important_findings(important_repo, monkeypatch):
    review = {"explanation": "Problem", "risk": "Risk", "recommendation": "Change", "suggested_fix": "fix()"}
    ai = Mock(return_value=review)
    monkeypatch.setattr("backend.main.generate_ai_review", ai)
    response = client.post("/analyze", json={"repo_url": "https://github.com/owner/repo", "include_ai_review": True})
    assert response.status_code == 200
    data = response.json()
    assert ai.call_count == 3
    assert all(call.args[0]["severity"] == "high" for call in ai.call_args_list)
    assert data["health_score"] == 58
    assert data["summary"]["total_issues"] == 5
    assert data["top_issues"][0]["ai_review"] == review
    assert sum("ai_review" in issue for issue in data["files"][0]["issues"]) == 3
    assert not important_repo.exists()


def test_static_analysis_is_default_and_never_calls_ai(important_repo, monkeypatch):
    ai = Mock()
    monkeypatch.setattr("backend.main.generate_ai_review", ai)
    response = client.post("/analyze", json={"repo_url": "https://github.com/owner/repo"})
    assert response.status_code == 200
    ai.assert_not_called()


def test_ai_failure_preserves_all_static_findings(important_repo, monkeypatch):
    ai = Mock(side_effect=RuntimeError("secret-key provider traceback"))
    monkeypatch.setattr("backend.main.generate_ai_review", ai)
    response = client.post("/analyze", json={"repo_url": "https://github.com/owner/repo", "include_ai_review": True})
    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["total_issues"] == 5
    assert data["health_score"] == 58
    assert "Static analysis" in data["warnings"][0]
    assert "secret-key" not in response.text
    ai.assert_called_once()
    assert not important_repo.exists()


def test_cleanup_after_analysis_error(important_repo, monkeypatch):
    monkeypatch.setattr("backend.main.analyze_python_file", Mock(side_effect=OSError("sensitive file")))
    response = client.post("/analyze", json={"repo_url": "https://github.com/owner/repo"})
    assert response.status_code == 500
    assert "sensitive file" not in response.text
    assert not important_repo.exists()


def test_unparseable_python_is_not_reported_as_healthy(important_repo):
    (important_repo / "app.py").write_text("def broken(:", encoding="utf-8")
    response = client.post("/analyze", json={"repo_url": "https://github.com/owner/repo"})
    assert response.status_code == 200
    data = response.json()
    assert data["health_score"] is None
    assert data["skipped_files"][0]["file"] == "app.py"
    assert data["warnings"]


@pytest.mark.parametrize("field,value", [("severity", "urgent"), ("line", 0), ("code_context", "x" * 12001)])
def test_invalid_ai_input_is_rejected(field, value):
    payload = {"rule": "print-statement", "severity": "low", "line": 1, "message": "Use logging"}
    payload[field] = value
    assert client.post("/ai-review", json=payload).status_code == 422
