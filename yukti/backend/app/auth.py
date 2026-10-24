"""Server-side identity for Yukti AI (P0.4, SPEC-06 §4.4, BUG-06).

The persona is derived only from a backend-signed session token (demo mode) or, in production, from an
IAP assertion. The request body, WebSocket query string and voice/text commands can never change it.

- Token: HS256 JWT `{sub, persona, function, grade, is_admin, demo, iat, exp, jti}` signed with
  `YUKTI_PERSONA_SIGNING_KEY`. Implemented with the standard library (hmac/hashlib), so no new dependency:
  the header must be exactly `alg=HS256`; `alg:none`, other algorithms, bad signatures, expired tokens
  and unknown personas are rejected (-> HTTP 401).
- Transport: `HttpOnly; Secure; SameSite=Strict` cookie `yk_session` (browser) or
  `Authorization: Bearer <token>` (tests, scripts). The WebSocket upgrade carries the cookie; a first
  frame `{"type": "auth", "token": ...}` is also accepted.
- Audit: JSONL at `logs/access_audit.jsonl` (SPEC-06 §4.8 schema; BigQuery sink comes with P2H.1).
"""

from __future__ import annotations

import base64
from contextvars import ContextVar, Token
import hashlib
import hmac
import json
import logging
import os
from pathlib import Path
import secrets
import tempfile
import threading
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional
import uuid
import yaml

from fastapi import HTTPException, Request

logger = logging.getLogger("yukti.auth")

COOKIE_NAME = "yk_session"
TOKEN_TTL_S = 8 * 3600


def _load_persona_directory() -> Dict[str, Dict[str, Any]]:
    """P2H.1 (SPEC-06 §4.1 / D-41 / D-60 / S9): load the 11 canonical personas strictly from app_users.yaml."""
    from app.access_control import VALID_PERSONAS

    yaml_path = Path(__file__).resolve().parent / "brain" / "app_users.yaml"
    if not yaml_path.exists():
        raise RuntimeError(f"app_users.yaml not found at {yaml_path}; required for 11-persona identity directory")
    raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    personas = raw.get("personas") or {}
    if set(personas.keys()) != set(VALID_PERSONAS) or len(personas) != 11:
        raise RuntimeError(
            f"app_users.yaml must define all 11 canonical personas {sorted(VALID_PERSONAS)}, got {sorted(personas.keys())}"
        )
    out: Dict[str, Dict[str, Any]] = {}
    for pid, info in personas.items():
        desig = info.get("functional_designation") or info.get("designation") or ""
        out[pid] = {
            **info,
            "designation": desig,
            "functional_designation": desig,
            "wc_id": info.get("wc_id", "WC-DEL"),
            "work_centre": info.get("work_centre", "Delhi HQ"),
        }
    return out


PERSONA_DIRECTORY: Dict[str, Dict[str, Any]] = _load_persona_directory()
ADMIN_PERSONA_ID = "DEMO_ADMIN"
ADMIN_DEFAULT_ACTING_PERSONA = "CMD"


class AuthError(Exception):
    """Token missing/invalid. The message is for logs only, never for users."""


@dataclass(frozen=True)
class Principal:
    emp_id: str
    persona: str              # effective RBAC persona (for DEMO_ADMIN: the persona it is acting as)
    function: str
    grade: str
    display_name: str
    designation: str
    is_admin: bool = False
    demo: bool = True
    jti: str = ""
    exp: int = 0
    wc_id: str = "WC-DEL"
    work_centre: str = "Delhi HQ"
    functional_designation: str = ""

    def public(self) -> Dict[str, Any]:
        d = asdict(self)
        d.pop("jti", None)
        if not d.get("functional_designation"):
            d["functional_designation"] = self.designation
        return d


# Per-turn server-side Principal contextvar so agent tool wrappers (run_certified_query, etc.)
# always bind the authenticated Principal (M1 / SPEC-06 §4.5) and fail closed when absent.
_ACTIVE_PRINCIPAL: ContextVar[Optional[Principal]] = ContextVar("yukti_active_principal", default=None)


def set_active_principal(principal: Optional[Principal]) -> Token:
    return _ACTIVE_PRINCIPAL.set(principal)


def reset_active_principal(token: Token) -> None:
    _ACTIVE_PRINCIPAL.reset(token)


def get_active_principal() -> Optional[Principal]:
    return _ACTIVE_PRINCIPAL.get()


def principal_for_persona(persona: str) -> Principal:
    """Build a server-side Principal for a canonical persona (raises UnknownPersona on unknown/empty)."""
    from app.access_control import normalize_persona

    canon = normalize_persona(persona)
    info = PERSONA_DIRECTORY[canon]
    return Principal(
        emp_id=str(info["emp_id"]),
        persona=canon,
        function=str(info["function"]),
        grade=str(info["grade"]),
        display_name=str(info["display_name"]),
        designation=str(info["designation"]),
        is_admin=False,
        demo=True,
        wc_id=str(info.get("wc_id", "WC-DEL")),
        work_centre=str(info.get("work_centre", "Delhi HQ")),
        functional_designation=str(info.get("functional_designation") or info["designation"]),
    )


# ------------------------------------------------------------------ signing key
_KEY_LOCK = threading.Lock()
_KEY: Optional[bytes] = None


MIN_KEY_BYTES = 32


def _is_prod() -> bool:
    return os.getenv("YUKTI_ENV", "dev").strip().lower() == "prod"


def _dev_key_path() -> Path:
    override = os.getenv("YUKTI_DEV_KEY_FILE")
    if override:
        return Path(override)
    return Path(tempfile.gettempdir()) / f"yukti_dev_persona_key_{os.getuid() if hasattr(os, 'getuid') else 'u'}"


def _read_trusted_key_file(path: Path) -> Optional[bytes]:
    """P0.4 r2: read the dev key only if it is a regular file (no symlink) owned by us with mode 0600-or-stricter."""
    import stat as _stat
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError:
        return None
    try:
        st = os.fstat(fd)
        if not _stat.S_ISREG(st.st_mode):
            logger.warning("Dev signing key file rejected: not a regular file")
            return None
        if hasattr(os, "getuid") and st.st_uid != os.getuid():
            logger.warning("Dev signing key file rejected: owned by another user")
            return None
        if st.st_mode & 0o077:
            logger.warning("Dev signing key file rejected: group/other permissions set")
            return None
        data = os.read(fd, 4096)
        return data if len(data) >= MIN_KEY_BYTES else None
    finally:
        os.close(fd)


def _signing_key() -> bytes:
    """`YUKTI_PERSONA_SIGNING_KEY` (Secret Manager in prod).

    - prod (`YUKTI_ENV=prod`): the secret is mandatory and must be >= 32 bytes; otherwise AuthError on every use,
      so protected routes fail closed with 401 (P0.4 r2). Never falls back to a file.
    - dev: a random 32-byte key kept in a 0600 file in the OS temp dir so all local uvicorn workers share it
      (a per-process key would make tokens fail across `--workers 2`). The file is trusted only if it is ours,
      not a symlink, and not group/other accessible; otherwise a per-process key is used. Never in the repo.
    """
    global _KEY
    if _KEY is not None:
        return _KEY
    with _KEY_LOCK:
        if _KEY is not None:
            return _KEY
        env = os.getenv("YUKTI_PERSONA_SIGNING_KEY", "")
        if _is_prod():
            if len(env.encode("utf-8")) < MIN_KEY_BYTES:
                logger.error("YUKTI_ENV=prod but YUKTI_PERSONA_SIGNING_KEY is missing or shorter than 32 bytes: "
                             "refusing to sign or verify sessions (fail closed)")
                raise AuthError("signing key not configured (prod)")
            _KEY = env.encode("utf-8")
            return _KEY
        if env:
            if len(env.encode("utf-8")) < MIN_KEY_BYTES:
                logger.warning("YUKTI_PERSONA_SIGNING_KEY is shorter than 32 bytes (dev only; prod refuses it)")
            _KEY = env.encode("utf-8")
            return _KEY
        path = _dev_key_path()
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
            with os.fdopen(fd, "wb") as f:
                f.write(secrets.token_bytes(MIN_KEY_BYTES))
        except FileExistsError:
            pass
        except OSError:
            pass
        key = _read_trusted_key_file(path)
        if key is None:
            key = secrets.token_bytes(MIN_KEY_BYTES)
            logger.warning("Persona signing key: using a random per-process key (tokens will not survive restarts)")
        _KEY = key
        logger.warning("YUKTI_PERSONA_SIGNING_KEY not set: using a local dev signing key (demo only; set the secret in prod)")
        return _KEY


def signing_key_ok() -> bool:
    """Startup probe (no secret material returned)."""
    try:
        _signing_key()
        return True
    except AuthError:
        return False


def _reset_key_for_tests() -> None:
    global _KEY
    _KEY = None


# ------------------------------------------------------------------ JWT (HS256, stdlib)
def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def _b64d(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def _sign(signing_input: bytes) -> str:
    return _b64e(hmac.new(_signing_key(), signing_input, hashlib.sha256).digest())


def issue_token(persona_id: str, is_admin: bool = False, ttl_s: int = TOKEN_TTL_S, now: Optional[int] = None) -> str:
    """Signs a session token for a known persona. Raises AuthError for unknown personas."""
    pid = (persona_id or "").strip().upper()
    if pid not in PERSONA_DIRECTORY:
        raise AuthError(f"unknown persona {persona_id!r}")
    info = PERSONA_DIRECTORY[pid]
    iat = int(now if now is not None else time.time())
    claims = {
        "sub": "DEMO-ADMIN" if is_admin else info["emp_id"],
        "persona": pid,
        "function": info["function"],
        "grade": info["grade"],
        "is_admin": bool(is_admin),
        "demo": True,
        "iat": iat,
        "exp": iat + int(ttl_s),
        "jti": uuid.uuid4().hex,
    }
    header = {"alg": "HS256", "typ": "JWT"}
    signing_input = f"{_b64e(json.dumps(header, separators=(',', ':')).encode())}.{_b64e(json.dumps(claims, separators=(',', ':')).encode())}"
    return f"{signing_input}.{_sign(signing_input.encode('ascii'))}"


_JWT_RE = __import__("re").compile(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")


def verify_token(token: str, now: Optional[int] = None) -> Principal:
    """Verifies signature, algorithm, expiry and persona. Raises AuthError on any problem."""
    if not token or token.count(".") != 2:
        raise AuthError("malformed token")
    # P0.4 r2: only the base64url JWT charset; anything else (e.g. non-ASCII) is a 401, never a 500
    if not _JWT_RE.fullmatch(token):
        raise AuthError("malformed token")
    h_b64, p_b64, s_b64 = token.split(".")
    try:
        header = json.loads(_b64d(h_b64))
        claims = json.loads(_b64d(p_b64))
    except Exception as exc:  # noqa: BLE001
        raise AuthError("undecodable token") from exc
    if not isinstance(header, dict) or header.get("alg") != "HS256":
        raise AuthError(f"rejected alg {header.get('alg') if isinstance(header, dict) else None!r}")
    expected = _sign(f"{h_b64}.{p_b64}".encode("ascii"))
    if not s_b64 or not hmac.compare_digest(expected.encode("ascii"), s_b64.encode("ascii")):
        raise AuthError("bad signature")
    if not isinstance(claims, dict):
        raise AuthError("bad claims")
    t = int(now if now is not None else time.time())
    try:
        exp = int(claims["exp"])
    except Exception as exc:  # noqa: BLE001
        raise AuthError("missing exp") from exc
    if exp <= t:
        raise AuthError("expired")
    try:
        if int(claims.get("iat", t)) > t + 60:  # P0.4 r2: future-dated tokens are rejected
            raise AuthError("iat in the future")
    except (TypeError, ValueError) as exc:
        raise AuthError("bad iat") from exc
    pid = str(claims.get("persona") or "").upper()
    if pid not in PERSONA_DIRECTORY:
        raise AuthError(f"unknown persona {pid!r}")
    info = PERSONA_DIRECTORY[pid]
    return Principal(
        emp_id=str(claims.get("sub") or info["emp_id"]),
        persona=pid,
        function=info["function"],
        grade=info["grade"],
        display_name=info["display_name"],
        designation=info["designation"],
        is_admin=bool(claims.get("is_admin")),
        demo=bool(claims.get("demo", True)),
        jti=str(claims.get("jti") or ""),
        exp=exp,
        wc_id=str(info.get("wc_id", "WC-DEL")),
        work_centre=str(info.get("work_centre", "Delhi HQ")),
        functional_designation=str(info.get("functional_designation") or info["designation"]),
    )


# ------------------------------------------------------------------ request helpers
def auth_mode() -> str:
    return os.getenv("YUKTI_AUTH_MODE", "demo").strip().lower() or "demo"


def verify_iap_assertion(assertion: str) -> Principal:
    """Prod (`YUKTI_AUTH_MODE=iap`) stub: IAP JWT verification + dim_app_user lookup land with P2H.1/P5.6.
    Until then iap mode fails closed (401)."""
    raise AuthError("IAP verification not implemented yet (fails closed)")


def token_from_headers(headers: Any, cookies: Optional[Dict[str, str]] = None) -> Optional[str]:
    authz = (headers.get("authorization") or headers.get("Authorization") or "") if headers is not None else ""
    if authz.lower().startswith("bearer "):
        return authz[7:].strip() or None
    if cookies and cookies.get(COOKIE_NAME):
        return cookies.get(COOKIE_NAME)
    return None


def principal_from_request(request: Request) -> Principal:
    if auth_mode() == "iap":
        return verify_iap_assertion(request.headers.get("x-goog-iap-jwt-assertion", ""))
    token = token_from_headers(request.headers, request.cookies)
    if not token:
        raise AuthError("no session token")
    return verify_token(token)


_UNAUTH = {"type": "error", "message": "Please sign in again to continue.", "retryable": False}


def require_principal(request: Request) -> Principal:
    """FastAPI dependency for protected routes: 401 without a valid token (never coerced to a persona)."""
    try:
        return principal_from_request(request)
    except AuthError as exc:
        logger.info(f"401 on {request.url.path}: {exc}")
        raise HTTPException(status_code=401, detail=_UNAUTH)


def require_admin(request: Request) -> Principal:
    """FastAPI dependency for /admin/*: a valid token that carries the admin claim, else 401."""
    p = require_principal(request)
    if not p.is_admin:
        audit("admin_denied", p, decision="refused", rule_ref="SPEC-06 §4.7")
        raise HTTPException(status_code=401, detail={"type": "error", "message": "Admin access required.", "retryable": False})
    return p


def cookie_secure() -> bool:
    # Secure by default (browsers treat http://localhost as secure); YUKTI_COOKIE_SECURE=0 only for plain-http hosts.
    return os.getenv("YUKTI_COOKIE_SECURE", "1") not in ("0", "false", "no")


def set_session_cookie(response: Any, token: str) -> None:
    response.set_cookie(COOKIE_NAME, token, max_age=TOKEN_TTL_S, httponly=True, secure=cookie_secure(),
                        samesite="strict", path="/")


def personas_public() -> List[Dict[str, Any]]:
    out = [
        {
            "id": pid,
            "persona_id": pid,
            "emp_id": v["emp_id"],
            "display_name": v["display_name"],
            "designation": v["designation"],
            "functional_designation": v.get("functional_designation", v["designation"]),
            "function": v["function"],
            "grade": v["grade"],
            "wc_id": v.get("wc_id", "WC-DEL"),
            "work_centre": v.get("work_centre", "Delhi HQ"),
        }
        for pid, v in PERSONA_DIRECTORY.items()
    ]
    out.append(
        {
            "id": ADMIN_PERSONA_ID,
            "persona_id": ADMIN_PERSONA_ID,
            "emp_id": "EMP-000001",
            "display_name": "Demo presenter",
            "designation": "Presenter (admin)",
            "functional_designation": "Presenter (admin)",
            "function": "ADMIN",
            "grade": "-",
            "wc_id": "WC-DEL",
            "work_centre": "Delhi HQ",
            "requires_passphrase": True,
        }
    )
    return out


def admin_passphrase_ok(passphrase: Optional[str]) -> bool:
    expected = os.getenv("YUKTI_DEMO_ADMIN_PASSPHRASE", "")
    if not expected or not passphrase:
        return False  # admin sessions are disabled unless the passphrase secret is configured
    return hmac.compare_digest(expected.encode("utf-8"), str(passphrase).encode("utf-8"))


# ------------------------------------------------------------------ role-switch detection (BEH-01, SPEC-06 §4.4 rule 4)
import re  # noqa: E402

_ROLE_WORDS = (r"(?:cmd|c\.m\.d|chairman|ceo|cfo|md|director|dir[\s_-]?(?:hr|fin(?:ance)?)|admin|administrator|"
               r"e\d(?:[\s_-]?(?:hr|fin))?|सीएमडी|चेयरमैन|निदेशक|डायरेक्टर|एडमिन)")
_ROLE_SWITCH_PATTERNS = [
    # P0.4 r2: "role/persona/access level" always count; "profile/user" only with "my" ("update the profile of
    # Rajesh" is a normal HR request, not a role switch)
    re.compile(r"\b(?:switch|change|set|update|elevate|upgrade)\s+(?:my\s+|the\s+)?(?:role|persona|access(?:\s+level)?)\b", re.I),
    re.compile(r"\b(?:switch|change|set|elevate|upgrade)\s+my\s+(?:profile|user)\b", re.I),
    re.compile(r"\b(?:switch|change)\s+(?:me\s+)?to\s+(?:the\s+)?" + _ROLE_WORDS + r"\b", re.I),
    re.compile(r"\b(?:act|log\s*in|login|sign\s*in|signin|speak|answer)\s+as\s+(?:the\s+|a\s+|an\s+)?" + _ROLE_WORDS, re.I),
    re.compile(r"\bmake\s+me\s+(?:the\s+|a\s+|an\s+)?" + _ROLE_WORDS, re.I),
    re.compile(r"\bpersona\s+" + _ROLE_WORDS + r"\b", re.I),
    re.compile(r"(?:मुझे|mujhe|muje|mujhko)\s+.{0,25}?(?:बना\s*दो|बना\s*दीजिए|बनाओ|bana\s*do|bana\s*dijiye|banao|bana\s*de)", re.I),
    re.compile(r"(?:रोल|भूमिका|role|persona)\s+.{0,20}?(?:बदलो|बदल\s*दो|बदलें|badlo|badal\s*do|change\s*karo)", re.I),
]
# "I am the CMD" alone is a role claim; "I am the director, show me everyone's salary" is a data request
# (BEH-01.05 expects R-PAY with the persona unchanged), so only short claims are treated as switches.
_ROLE_CLAIM = re.compile(r"^\s*(?:hi|hello|namaste)?[,\s]*(?:i\s*am|i'm|im|main|मैं)\s+(?:the\s+|a\s+|an\s+)?" + _ROLE_WORDS +
                         r"(?:\s+(?:now|here|hoon|हूँ|हूं))?\s*[.!]?\s*$", re.I)


def is_role_switch_request(query: str) -> bool:
    q = (query or "").strip()
    if not q:
        return False
    if _ROLE_CLAIM.search(q):
        return True
    return any(p.search(q) for p in _ROLE_SWITCH_PATTERNS)


def requested_persona(query: str) -> Optional[str]:
    """Best-effort target persona for an admin switch ("switch role to E3_FIN" -> E3_FIN) across all 11 personas."""
    q = (query or "").lower()
    table = [
        (r"\b(e1[\s_-]?hr|hr[\s_-]?e1|dinesh\s+deshmukh)\b", "E1_HR"),
        (r"\b(e2[\s_-]?hr|hr[\s_-]?e2|pooja\s+verma|pooja)\b", "E2_HR"),
        (r"\b(e3[\s_-]?hr|hr[\s_-]?e3|pooja\s+pillai)\b", "E3_HR"),
        (r"\b(e4[\s_-]?hr|hr[\s_-]?e4|aarti\s+saikia)\b", "E4_HR"),
        (r"\b(e1[\s_-]?fin(?:ance)?|fin(?:ance)?[\s_-]?e1|ajay\s+deshmukh)\b", "E1_FIN"),
        (r"\b(e2[\s_-]?fin(?:ance)?|fin(?:ance)?[\s_-]?e2|praveen\s+nair)\b", "E2_FIN"),
        (r"\b(e3[\s_-]?fin(?:ance)?|fin(?:ance)?[\s_-]?e3|asha\s+mishra|rajesh\s+kulkarni|rajesh)\b", "E3_FIN"),
        (r"\b(e4[\s_-]?fin(?:ance)?|fin(?:ance)?[\s_-]?e4|santosh\s+banerjee)\b", "E4_FIN"),
        (r"\b(dir(ector)?[\s_-]*(\()?(fin|finance)|finance\s+director|cfo|vivek\s+rao)\b", "DIR_FIN"),
        (r"\b(dir(ector)?[\s_-]*(\()?hr|hr\s+director|director\s+human\s+resources|manish\s+deshpande)\b", "DIR_HR"),
        (r"\b(cmd|c\.m\.d|chairman|ceo|arun\s+mehra)\b", "CMD"),
    ]
    for pat, pid in table:
        if re.search(pat, q):
            return pid
    return None


R_ROLE_COPY = {
    "en": "I can't change your access level from a conversation. You're signed in as {display_name}, {designation}.",
    "hi": "बातचीत से आपका एक्सेस स्तर नहीं बदला जा सकता। आप {display_name}, {designation} के रूप में साइन-इन हैं।",
}


def r_role_text(principal: Principal, lang: str = "en") -> str:
    key = "hi" if lang == "hi" else "en"
    return R_ROLE_COPY[key].format(display_name=principal.display_name, designation=principal.designation)


# ------------------------------------------------------------------ audit (SPEC-06 §4.8)
_AUDIT_LOCK = threading.Lock()


def audit_path() -> Path:
    env = os.getenv("YUKTI_AUDIT_LOG")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent / "logs" / "access_audit.jsonl"


def audit(event: str, principal: Optional[Principal], *, turn_id: str = "", data_classes: Optional[List[str]] = None,
          decision: str = "", rule_ref: str = "", query: Optional[str] = None, **extra: Any) -> None:
    """Appends one audit row. Question text is never stored; only a hash (SPEC-06 §4.8)."""
    row = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "emp_id": principal.emp_id if principal else None,
        "persona": principal.persona if principal else None,
        "turn_id": turn_id,
        "event": event,
        "data_classes": list(data_classes or []),
        "decision": decision,
        "rule_ref": rule_ref,
        "query_hash": hashlib.sha256(query.encode("utf-8")).hexdigest()[:16] if query else None,
    }
    for k, v in extra.items():
        if k not in row:
            row[k] = v
    try:
        p = audit_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        with _AUDIT_LOCK, open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError as exc:  # auditing must never take a turn down
        logger.warning(f"audit write failed: {exc}")
