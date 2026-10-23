"""P0.5 (BUG-32, SPEC-06 §4.7): CORS allow-list, /admin/* lock, docs off in prod."""

import importlib
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402


def _fresh_app(monkeypatch, **env):
    for k in ("YUKTI_ALLOWED_ORIGINS", "YUKTI_ENABLE_ADMIN", "YUKTI_ENV"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    import app.config as cfg
    import app.main as main
    importlib.reload(cfg)
    importlib.reload(main)
    return main


@pytest.fixture(autouse=True)
def _restore(monkeypatch, tmp_path):
    monkeypatch.setenv("YUKTI_AUDIT_LOG", str(tmp_path / "audit.jsonl"))
    yield
    for k in ("YUKTI_ALLOWED_ORIGINS", "YUKTI_ENABLE_ADMIN", "YUKTI_ENV"):
        monkeypatch.delenv(k, raising=False)
    import app.config as cfg
    import app.main as main
    importlib.reload(cfg)
    importlib.reload(main)


def _preflight(client, origin):
    return client.options("/api/turn", headers={"Origin": origin, "Access-Control-Request-Method": "POST",
                                                 "Access-Control-Request-Headers": "content-type"})


def test_evil_origin_gets_no_cors_header(monkeypatch):
    main = _fresh_app(monkeypatch)
    r = _preflight(TestClient(main.app), "https://evil.example")
    assert "access-control-allow-origin" not in {k.lower() for k in r.headers}


def test_allowed_origin_gets_cors_header(monkeypatch):
    main = _fresh_app(monkeypatch)
    r = _preflight(TestClient(main.app), "http://localhost:3300")
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3300"
    assert r.headers.get("access-control-allow-credentials") == "true"
    methods = r.headers.get("access-control-allow-methods", "")
    assert "POST" in methods and "DELETE" not in methods and "*" not in methods


def test_wildcard_in_env_is_dropped(monkeypatch):
    main = _fresh_app(monkeypatch, YUKTI_ALLOWED_ORIGINS="*,https://app.example")
    c = TestClient(main.app)
    assert "access-control-allow-origin" not in {k.lower() for k in _preflight(c, "https://evil.example").headers}
    assert _preflight(c, "https://app.example").headers.get("access-control-allow-origin") == "https://app.example"


def test_admin_without_token_401(monkeypatch):
    main = _fresh_app(monkeypatch, YUKTI_ENABLE_ADMIN="1")
    c = TestClient(main.app)
    assert c.post("/admin/cache/clear").status_code == 401
    assert c.get("/admin/cache").status_code == 401


def test_admin_with_non_admin_token_401(monkeypatch):
    main = _fresh_app(monkeypatch, YUKTI_ENABLE_ADMIN="1")
    from app.auth import issue_token
    c = TestClient(main.app, headers={"Authorization": f"Bearer {issue_token('CMD')}"})
    assert c.post("/admin/cache/clear").status_code == 401  # even CMD is not an admin


def test_admin_with_admin_token_ok_when_enabled(monkeypatch):
    main = _fresh_app(monkeypatch, YUKTI_ENABLE_ADMIN="1")
    from app.auth import issue_token
    c = TestClient(main.app, headers={"Authorization": f"Bearer {issue_token('CMD', is_admin=True)}"})
    r = c.post("/admin/cache/clear")
    assert r.status_code == 200 and r.json()["status"] == "cleared"
    assert c.get("/admin/cache").status_code == 200


def test_admin_disabled_is_404(monkeypatch):
    main = _fresh_app(monkeypatch)  # YUKTI_ENABLE_ADMIN unset -> routes not registered
    from app.auth import issue_token
    c = TestClient(main.app, headers={"Authorization": f"Bearer {issue_token('CMD', is_admin=True)}"})
    assert c.post("/admin/cache/clear").status_code == 404
    assert c.get("/admin/cache").status_code == 404


def test_docs_off_in_prod(monkeypatch):
    main = _fresh_app(monkeypatch, YUKTI_ENV="prod")
    c = TestClient(main.app)
    assert c.get("/docs").status_code == 404 and c.get("/openapi.json").status_code == 404
    main = _fresh_app(monkeypatch)
    assert TestClient(main.app).get("/openapi.json").status_code == 200


def test_prod_without_origins_env_allows_no_cross_origin(monkeypatch):
    """P0.5 r2 (G4 minor): in prod the localhost dev defaults are not trusted."""
    main = _fresh_app(monkeypatch, YUKTI_ENV="prod")
    r = _preflight(TestClient(main.app), "http://localhost:3300")
    assert "access-control-allow-origin" not in {k.lower() for k in r.headers}
