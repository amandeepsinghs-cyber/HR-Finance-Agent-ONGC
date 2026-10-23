"""Unit test verifying export endpoints (POST /api/export, GET /api/export/{export_id})
and structured error handling.
"""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app
from app.auth import issue_token

# P0.4: export routes require a signed session token
client = TestClient(app, headers={"Authorization": f"Bearer {issue_token('CMD')}"})


def test_post_and_get_export():
    # 1. Test POST /api/export
    payload = {
        "format": "pdf",
        "title": "Board_Note_Test",
        "content": "# Agenda Note\nSample operational review content.",
    }
    res_post = client.post("/api/export", json=payload)
    assert res_post.status_code == 200
    data = res_post.json()
    assert "export_id" in data
    assert data["format"] == "pdf"
    assert "filename" in data

    export_id = data["export_id"]

    # 2. Test GET /api/export/{export_id}
    res_get = client.get(f"/api/export/{export_id}")
    assert res_get.status_code == 200
    assert res_get.headers.get("content-type") == "application/pdf"
    assert len(res_get.content) > 100


def test_invalid_export_returns_structured_error():
    # Test non-existent ID
    res = client.get("/api/export/non_existent_id_abc123")
    assert res.status_code == 404
    err_json = res.json()
    assert err_json.get("type") == "error"
    assert "not found" in err_json.get("message", "").lower()
    assert err_json.get("retryable") is False


def test_directory_traversal_prevented():
    # Attempt directory traversal
    res = client.get("/api/export/../../etc/passwd")
    assert res.status_code == 404
    err_json = res.json()
    assert err_json.get("type") == "error"
