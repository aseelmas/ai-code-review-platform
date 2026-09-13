from fastapi.testclient import TestClient
import pytest

from backend.main import app


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
