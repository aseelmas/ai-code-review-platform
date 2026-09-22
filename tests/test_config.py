import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock

import pytest

from backend import config
from backend.__main__ import main


@pytest.fixture(autouse=True)
def isolated_config(monkeypatch):
    for name in ("APP_ENV", "CORS_ORIGINS", "PORT", "LIMIT_CONCURRENCY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(config, "load_dotenv", Mock())


def test_development_preserves_local_origins():
    assert config.get_cors_origins() == ["http://localhost:5173", "http://127.0.0.1:5173"]


def test_production_defaults_to_no_cross_origin_access(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    assert config.get_cors_origins() == []
    config.load_dotenv.assert_not_called()


def test_origins_are_normalized_and_deduplicated(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CORS_ORIGINS", " https://UI.example.test/, https://other.example.test,https://ui.example.test ")
    assert config.get_cors_origins() == ["https://ui.example.test", "https://other.example.test"]


@pytest.mark.parametrize("origin", [
    "*", "https://*.example.test", "null", "http://ui.example.test",
    "https://ui.example.test/path", "https://ui.example.test?secret=value",
    "https://ui.example.test#fragment", "https://secret@ui.example.test",
    "https://@ui.example.test", "https://ui.example.test:wrong", "https://bad host.test",
])
def test_invalid_production_origins_fail_safely(monkeypatch, origin):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CORS_ORIGINS", origin)
    with pytest.raises(ValueError, match="CORS_ORIGINS") as error:
        config.get_cors_origins()
    assert "secret" not in str(error.value)


def test_dotenv_is_explicit_and_does_not_override_environment():
    config.load_environment()
    config.load_dotenv.assert_called_once_with(
        Path(config.__file__).resolve().parent.parent / ".env", override=False,
    )


def test_unknown_environment_is_rejected(monkeypatch):
    monkeypatch.setenv("APP_ENV", "prodution")
    with pytest.raises(ValueError, match="APP_ENV"):
        config.get_environment()


def test_production_entrypoint_binds_platform_port_without_reload(monkeypatch):
    run = Mock()
    monkeypatch.setattr("backend.__main__.uvicorn.run", run)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("PORT", "10000")
    monkeypatch.setenv("LIMIT_CONCURRENCY", "12")
    main()
    assert run.call_args.args == ("backend.main:app",)
    assert run.call_args.kwargs == {
        "host": "0.0.0.0", "port": 10000, "workers": 1, "reload": False,
        "limit_concurrency": 12, "timeout_graceful_shutdown": 30,
    }


@pytest.mark.parametrize("name,value", [
    ("PORT", "0"), ("PORT", "65536"), ("PORT", "invalid"),
    ("LIMIT_CONCURRENCY", "-1"), ("LIMIT_CONCURRENCY", "1001"),
])
def test_invalid_server_settings_do_not_start_server(monkeypatch, name, value):
    run = Mock()
    monkeypatch.setattr("backend.__main__.uvicorn.run", run)
    monkeypatch.setenv(name, value)
    with pytest.raises(ValueError, match=name):
        main()
    run.assert_not_called()


def test_real_app_cors_in_fresh_production_process():
    # Fresh import tests production middleware without mutating the shared app
    # used by the existing API regression tests. No external APIs are invoked.
    script = '''
import json
from fastapi.testclient import TestClient
from backend.main import app
with TestClient(app) as client:
    accepted = client.options('/analyze', headers={
        'Origin': 'https://ui.example.test',
        'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'content-type',
    })
    rejected = client.options('/analyze', headers={
        'Origin': 'https://untrusted.example.test',
        'Access-Control-Request-Method': 'POST',
    })
    print(json.dumps({
        'health': client.get('/').status_code,
        'accepted': accepted.status_code,
        'origin': accepted.headers.get('access-control-allow-origin'),
        'credentials': accepted.headers.get('access-control-allow-credentials'),
        'rejected': rejected.status_code,
        'rejected_origin': rejected.headers.get('access-control-allow-origin'),
    }))
'''
    env = {**os.environ, "APP_ENV": "production", "CORS_ORIGINS": "https://ui.example.test"}
    result = subprocess.run([sys.executable, "-c", script], env=env, check=True, capture_output=True, text=True, timeout=30)
    assert json.loads(result.stdout) == {
        "health": 200, "accepted": 200, "origin": "https://ui.example.test",
        "credentials": None, "rejected": 400, "rejected_origin": None,
    }
