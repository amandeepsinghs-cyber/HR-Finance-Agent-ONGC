"""P0.4 (FEAT-031, BUG-06): server-side persona tokens (SPEC-06 §4.4)."""

import base64
import json
from pathlib import Path
import sys
import time

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app import auth  # noqa: E402
from app.access_control import UnknownPersona, normalize_persona  # noqa: E402


@pytest.fixture(autouse=True)
def _audit_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv("YUKTI_AUDIT_LOG", str(tmp_path / "audit.jsonl"))
    yield tmp_path / "audit.jsonl"


def _b64(d) -> str:
    return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()


def _client():
    from app.main import app
    return TestClient(app)


def test_issue_and_verify_roundtrip():
    tok = auth.issue_token("E2_HR")
    p = auth.verify_token(tok)
    assert p.persona == "E2_HR" and p.grade == "E2" and p.function == "HR" and not p.is_admin
    assert p.display_name == "Pooja Verma"
    hdr = json.loads(base64.urlsafe_b64decode(tok.split(".")[0] + "=="))
    assert hdr == {"alg": "HS256", "typ": "JWT"}
    claims = json.loads(base64.urlsafe_b64decode(tok.split(".")[1] + "=="))
    assert {"sub", "persona", "function", "grade", "is_admin", "demo", "iat", "exp", "jti"} <= set(claims)
    assert claims["exp"] - claims["iat"] == 8 * 3600


def test_forged_signature_rejected():
    tok = auth.issue_token("E2_HR")
    h, p, s = tok.split(".")
    claims = json.loads(base64.urlsafe_b64decode(p + "=="))
    claims["persona"] = "CMD"
    forged = f"{h}.{_b64(claims)}.{s}"
    with pytest.raises(auth.AuthError):
        auth.verify_token(forged)
    r = _client().post("/api/turn", json={"query": "hello"}, headers={"Authorization": f"Bearer {forged}"})
    assert r.status_code == 401


def test_alg_none_rejected():
    claims = {"sub": "x", "persona": "CMD", "is_admin": True, "iat": int(time.time()), "exp": int(time.time()) + 3600}
    for alg in ("none", "None", "HS512", "RS256"):
        tok = f"{_b64({'alg': alg, 'typ': 'JWT'})}.{_b64(claims)}."
        with pytest.raises(auth.AuthError):
            auth.verify_token(tok)
    tok = f"{_b64({'alg': 'none', 'typ': 'JWT'})}.{_b64(claims)}."
    assert _client().post("/api/turn", json={"query": "hello"}, headers={"Authorization": f"Bearer {tok}"}).status_code == 401


def test_expired_rejected():
    tok = auth.issue_token("DIR_FIN", ttl_s=60, now=int(time.time()) - 3600)
    with pytest.raises(auth.AuthError):
        auth.verify_token(tok)
    assert _client().post("/api/turn", json={"query": "hello"}, headers={"Authorization": f"Bearer {tok}"}).status_code == 401


def test_unknown_persona_never_coerced():
    with pytest.raises(auth.AuthError):
        auth.issue_token("INTERN")
    with pytest.raises(UnknownPersona):
        normalize_persona("intern")
    with pytest.raises(UnknownPersona):
        normalize_persona(None)
    assert normalize_persona("Director (Finance)") == "DIR_FIN"
    r = _client().post("/api/auth/session", json={"persona_id": "INTERN"})
    assert r.status_code == 401


@pytest.mark.parametrize("path,method", [("/api/turn", "post"), ("/api/voice-turn", "post"), ("/api/export", "post"),
                                         ("/api/export/exp_" + "0" * 32, "get"), ("/api/auth/me", "get")])
def test_protected_routes_401_without_token(path, method):
    c = _client()
    body = {"query": "hello"} if path == "/api/turn" else ({"audio_base64": ""} if "voice" in path else {"format": "pdf"})
    r = c.post(path, json=body) if method == "post" else c.get(path)
    assert r.status_code == 401, (path, r.status_code)
    assert "Traceback" not in r.text


def test_session_cookie_flags_and_me():
    c = _client()
    r = c.post("/api/auth/session", json={"persona_id": "E3_FIN"})
    assert r.status_code == 200
    sc = r.headers.get("set-cookie", "")
    assert sc.startswith("yk_session=") and "HttpOnly" in sc and "Secure" in sc and "SameSite=strict" in sc.replace("Strict", "strict")
    tok = sc.split(";", 1)[0].split("=", 1)[1]
    me = c.get("/api/auth/me", headers={"Authorization": f"Bearer {tok}"}).json()["principal"]
    assert me["persona"] == "E3_FIN" and me["display_name"] == "Asha Mishra" and "jti" not in me
    assert r.json()["principal"]["persona"] == "E3_FIN" and "token" not in r.json()


def test_personas_listing_has_p0_set():
    ids = [p["id"] for p in _client().get("/api/auth/personas").json()["personas"]]
    assert ids == [
        "CMD",
        "DIR_HR",
        "DIR_FIN",
        "E1_HR",
        "E2_HR",
        "E3_HR",
        "E4_HR",
        "E1_FIN",
        "E2_FIN",
        "E3_FIN",
        "E4_FIN",
        "DEMO_ADMIN",
    ]


def test_admin_session_requires_configured_passphrase(monkeypatch):
    c = _client()
    monkeypatch.delenv("YUKTI_DEMO_ADMIN_PASSPHRASE", raising=False)
    assert c.post("/api/auth/session", json={"persona_id": "DEMO_ADMIN", "passphrase": "x"}).status_code == 401
    monkeypatch.setenv("YUKTI_DEMO_ADMIN_PASSPHRASE", "open-sesame-test")
    assert c.post("/api/auth/session", json={"persona_id": "DEMO_ADMIN", "passphrase": "wrong"}).status_code == 401
    r = c.post("/api/auth/session", json={"persona_id": "DEMO_ADMIN", "passphrase": "open-sesame-test"})
    assert r.status_code == 200 and r.json()["principal"]["is_admin"] is True
    assert r.json()["principal"]["persona"] == "CMD"


# ---------------------------------------------------------------- P0.4 r2 (G4 must-fix 1, 2; minors 3, 5)
@pytest.mark.parametrize("mutate", ["sig_non_ascii", "hdr_non_ascii", "junk_chars"])
def test_non_ascii_or_junk_tokens_are_401_not_500(mutate):
    tok = auth.issue_token("E2_HR")
    h, p, s = tok.split(".")
    bad = {"sig_non_ascii": f"{h}.{p}.é", "hdr_non_ascii": f"hé{h}.{p}.{s}", "junk_chars": f"{h}.{p}.{s}+/="}[mutate]
    with pytest.raises(auth.AuthError):
        auth.verify_token(bad)
    c = _client()
    for path in ("/api/auth/me",):
        r = c.get(path, headers={"Authorization": f"Bearer {bad}".encode("utf-8")})  # raw UTF-8 bytes on the wire
        assert r.status_code == 401, (mutate, r.status_code)
    r = c.post("/api/turn", json={"query": "hello"}, headers={"Authorization": f"Bearer {bad}".encode("utf-8")})
    assert r.status_code == 401


def test_future_iat_rejected():
    tok = auth.issue_token("CMD", now=int(time.time()) + 3600)
    with pytest.raises(auth.AuthError):
        auth.verify_token(tok)


@pytest.fixture()
def _fresh_key(monkeypatch):
    auth._reset_key_for_tests()
    yield
    auth._reset_key_for_tests()


def test_prod_without_key_fails_closed(monkeypatch, _fresh_key):
    monkeypatch.setenv("YUKTI_ENV", "prod")
    monkeypatch.delenv("YUKTI_PERSONA_SIGNING_KEY", raising=False)
    with pytest.raises(auth.AuthError):
        auth.issue_token("CMD")
    assert auth.signing_key_ok() is False
    c = _client()
    assert c.post("/api/auth/session", json={"persona_id": "CMD"}).status_code == 401
    # a token minted with some other key is not accepted either (verification also needs the key)
    assert c.get("/api/auth/me", headers={"Authorization": "Bearer a.b.c"}).status_code == 401
    monkeypatch.setenv("YUKTI_PERSONA_SIGNING_KEY", "too-short")
    auth._reset_key_for_tests()
    with pytest.raises(auth.AuthError):
        auth.issue_token("CMD")
    monkeypatch.setenv("YUKTI_PERSONA_SIGNING_KEY", "k" * 40)
    auth._reset_key_for_tests()
    assert auth.verify_token(auth.issue_token("CMD")).persona == "CMD"


def test_untrusted_dev_key_file_is_rejected(monkeypatch, tmp_path, _fresh_key):
    import os
    monkeypatch.delenv("YUKTI_ENV", raising=False)
    monkeypatch.delenv("YUKTI_PERSONA_SIGNING_KEY", raising=False)
    planted = tmp_path / "planted_key"
    planted.write_bytes(b"A" * 32)               # attacker-chosen key
    os.chmod(planted, 0o644)                      # group/other readable -> must not be trusted
    monkeypatch.setenv("YUKTI_DEV_KEY_FILE", str(planted))
    assert auth._signing_key() != b"A" * 32
    auth._reset_key_for_tests()
    link = tmp_path / "link_key"
    target = tmp_path / "target_key"
    target.write_bytes(b"B" * 32)
    os.chmod(target, 0o600)
    link.symlink_to(target)                       # symlink -> O_NOFOLLOW refuses it
    monkeypatch.setenv("YUKTI_DEV_KEY_FILE", str(link))
    assert auth._signing_key() != b"B" * 32
    auth._reset_key_for_tests()
    good = tmp_path / "good_key"
    good.write_bytes(b"C" * 32)
    os.chmod(good, 0o600)
    monkeypatch.setenv("YUKTI_DEV_KEY_FILE", str(good))
    assert auth._signing_key() == b"C" * 32


def test_profile_of_someone_else_is_not_a_role_switch():
    for q in ("update the profile of Rajesh", "change the user's email in HRMS", "How do I update my profile photo?"):
        assert not auth.is_role_switch_request(q), q
    assert auth.is_role_switch_request("switch my profile to CMD")
