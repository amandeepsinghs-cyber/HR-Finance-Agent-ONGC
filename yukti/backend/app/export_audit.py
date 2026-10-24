"""Export file naming, RBAC-aware turn/artifact registry, and JSONL audit logger (P4.6, SPEC-10 §4.9–4.10, §5).

- File naming (§4.9):
  `yukti_{subject}_{scope}_{period}_{persona}_{yyyymmdd-HHMM}[_aggregate].{ext}`
  Lowercase snake_case (`[a-z0-9_-]`), ASCII only (Hindi titles transliterated or stripped),
  <= 80 chars before the extension, matching:
  `^yukti_[a-z0-9_\\-]+_\\d{8}-\\d{4}(_aggregate)?\\.(xlsx|csv|pdf|png|svg|docx|eml)$`
- Audit table (§4.10):
  Target schema for `hrfin_ops.export_audit`, written to local JSONL (`logs/export_audit.jsonl` or
  `YUKTI_EXPORT_AUDIT_LOG`; executor writes JSONL only, no bq CLI calls):
  `ts, emp_id, persona, session_id, turn_id, format, filename, sha256, rows, columns, data_classes, masked, delivery, client_ip_hash`
- Download auth & 24h expiry (§4.10 item 5):
  Every generated export records its creator `(emp_id, persona)` and 24h `expires_at`;
  `GET /api/export/{export_id}` verifies the requesting principal matches the creator (403 on mismatch)
  and rejects expired artifacts (404).
"""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass, field
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from app.brain.rbac import column_class, enforce_contract, load_policy, persona_class, suppress_small_cells
from app.config import EXPORTS_DIR

logger = logging.getLogger("yukti.export_audit")

NAMING_REGEX = re.compile(
    r"^yukti_[a-z0-9_\-]+_\d{8}-\d{4}(_aggregate)?\.(xlsx|csv|pdf|png|svg|docx|eml)$"
)

DEFAULT_EXPORT_TTL_SECONDS = 24 * 3600  # 24 hours per SPEC-10 §4.10 item 5

_HINDI_TRANSLIT: List[Tuple[str, str]] = [
    ("ओएनजीसी", "ongc"),
    ("राजस्व", "rajasva"),
    ("शुद्ध लाभ", "shuddh_labh"),
    ("लाभ", "labh"),
    ("वित्तीय", "vittiya"),
    ("सारांश", "saransh"),
    ("दिल्ली", "delhi"),
    ("मुम्बई", "mumbai"),
    ("मुंबई", "mumbai"),
    ("अधिकारी", "adhikari"),
    ("कर्मचारी", "karmachari"),
    ("वेतन", "vetan"),
    ("स्थानांतरण", "transfer"),
    ("सूची", "roster"),
    ("रिपोर्ट", "report"),
    ("بيانات", "data"),
]

# Synonym map for user-requested column names (SPEC-07 §4.4 / SPEC-10 §4.10)
COLUMN_SYNONYM_MAP: Dict[str, str] = {
    "name": "name",
    "names": "name",
    "employee name": "name",
    "emp_name": "name",
    "naam": "name",
    "नाम": "name",
    "designation": "functional_designation",
    "designations": "functional_designation",
    "functional_designation": "functional_designation",
    "post": "functional_designation",
    "title": "functional_designation",
    "पद": "functional_designation",
    "rank": "grade",
    "ranks": "grade",
    "level": "grade",
    "levels": "grade",
    "grade": "grade",
    "grades": "grade",
    "स्तर": "grade",
    "ग्रेड": "grade",
    "tenure in delhi": "delhi_tenure_years",
    "delhi tenure": "delhi_tenure_years",
    "years in delhi": "delhi_tenure_years",
    "delhi_tenure_years": "delhi_tenure_years",
    "दिल्ली में कार्यकाल": "delhi_tenure_years",
    "service": "ongc_tenure_years",
    "ongc tenure": "ongc_tenure_years",
    "ongc service": "ongc_tenure_years",
    "ongc_tenure_years": "ongc_tenure_years",
    "retirement": "years_to_retirement",
    "years to retirement": "years_to_retirement",
    "years_to_retirement": "years_to_retirement",
    "exemption": "exemption",
    "exemptions": "exemption",
}


class TurnOwnershipError(PermissionError):
    """Raised when a principal attempts to export or download another principal's turn/artifact."""


def transliterate_or_slug(text: str, default: str = "report", max_len: int = 28) -> str:
    """Converts English/Hindi text into a clean lowercase ASCII snake_case token `[a-z0-9_-]`."""
    raw = str(text or "").strip()
    for hi, en in _HINDI_TRANSLIT:
        if hi in raw:
            raw = raw.replace(hi, f" {en} ")
    raw = raw.lower()
    # Replace common symbols
    raw = raw.replace(">=", "ge").replace("<=", "le").replace(">", "gt").replace("<", "lt")
    raw = raw.replace("&", "and").replace("–", "-").replace("—", "-")
    # Strip any remaining non-ASCII characters
    ascii_only = raw.encode("ascii", errors="ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9\-]+", "_", ascii_only)
    slug = re.sub(r"_+", "_", slug).strip("_-")
    if not slug:
        slug = default
    return slug[:max_len].strip("_-") or default


def build_export_filename(
    subject: str,
    scope: str = "corp",
    period: str = "current",
    persona: str = "cmd",
    ext: str = "xlsx",
    is_aggregate: bool = False,
    now_ts: Optional[float] = None,
) -> str:
    """Builds a canonical export filename per SPEC-10 §4.9:
    `yukti_{subject}_{scope}_{period}_{persona}_{yyyymmdd-HHMM}[_aggregate].{ext}`
    Guaranteed <= 80 chars before extension and matching `NAMING_REGEX`.
    """
    clean_ext = re.sub(r"[^a-z0-9]", "", (ext or "xlsx").lower())
    if clean_ext not in ("xlsx", "csv", "pdf", "png", "svg", "docx", "eml"):
        clean_ext = "xlsx"

    ts_struct = time.gmtime(now_ts if now_ts is not None else time.time())
    ts_str = time.strftime("%Y%m%d-%H%M", ts_struct)

    p_slug = transliterate_or_slug(persona, default="cmd", max_len=12).replace("-", "_")
    sc_slug = transliterate_or_slug(scope, default="corp", max_len=14)
    per_slug = transliterate_or_slug(period, default="current", max_len=16)
    subj_slug = transliterate_or_slug(subject, default="report", max_len=28)

    suffix = "_aggregate" if is_aggregate else ""
    fixed_tail = f"_{sc_slug}_{per_slug}_{p_slug}_{ts_str}{suffix}"
    max_subj = max(4, 80 - len("yukti_") - len(fixed_tail))
    subj_slug = subj_slug[:max_subj].strip("_-") or "report"

    stem = f"yukti_{subj_slug}{fixed_tail}"
    if len(stem) > 80:
        # Trim subject and scope if still over 80
        stem = f"yukti_{subj_slug[:12]}_{p_slug}_{ts_str}{suffix}"[:80]
    filename = f"{stem}.{clean_ext}"
    if not NAMING_REGEX.fullmatch(filename):
        fallback_stem = f"yukti_report_{p_slug}_{ts_str}{suffix}"[:80]
        filename = f"{fallback_stem}.{clean_ext}"
    return filename


def filename_from_contract(
    contract: Optional[Dict[str, Any]],
    ext: str,
    persona: str = "CMD",
    is_aggregate: bool = False,
    title_override: Optional[str] = None,
    now_ts: Optional[float] = None,
) -> str:
    """Derives `(subject, scope, period)` from a contract (or fallback title) and builds the §4.9 filename."""
    c = contract or {}
    vis = c.get("visual") or {}
    stmt = vis.get("statement") if isinstance(vis.get("statement"), dict) else None
    qspec = c.get("query_spec") if isinstance(c.get("query_spec"), dict) else {}

    if stmt:
        st_kind = str(stmt.get("statement") or "pnl").lower()
        subj = {"pnl": "pnl", "balance_sheet": "bs", "cash_flow": "cf"}.get(st_kind, st_kind)
        scope = str(stmt.get("scope") or "standalone").lower()
        periods = [str(p).lower() for p in (stmt.get("periods") or []) if p]
        if len(periods) >= 2:
            period = f"{periods[-1]}-{periods[0]}"
        elif len(periods) == 1:
            period = periods[0]
        else:
            period = "fy26"
        return build_export_filename(
            subject=subj,
            scope=scope,
            period=period,
            persona=persona,
            ext=ext,
            is_aggregate=is_aggregate,
            now_ts=now_ts,
        )

    raw_title = title_override or vis.get("title") or c.get("definition_id") or qspec.get("subject") or "report"
    subj = transliterate_or_slug(str(raw_title), default="report", max_len=24)
    if is_aggregate and subj.endswith("_roster"):
        subj = subj[:-7] + "_bylevel"

    filters = qspec.get("filters") if isinstance(qspec.get("filters"), dict) else {}
    wc_id = filters.get("wc_id") or ""
    if wc_id:
        scope = str(wc_id).lower()
    elif "delhi" in str(raw_title).lower():
        scope = "WC-DEL".lower()
    elif c.get("dcf_workbook"):
        scope = "standalone"
    else:
        scope = "corp"

    as_of = qspec.get("as_of") or ""
    if not as_of:
        for src in (c.get("sources") or []):
            if isinstance(src, dict) and src.get("as_of"):
                as_of = str(src["as_of"])
                break
    if as_of and re.match(r"^\d{4}-\d{2}-\d{2}$", str(as_of)):
        period = "asof-" + str(as_of).replace("-", "")
    else:
        m_fy = re.findall(r"fy\d{2}", str(raw_title).lower())
        if len(m_fy) >= 2:
            period = f"{m_fy[0]}-{m_fy[-1]}"
        elif len(m_fy) == 1:
            period = m_fy[0]
        else:
            period = "asof-20261019"

    return build_export_filename(
        subject=subj,
        scope=scope,
        period=period,
        persona=persona,
        ext=ext,
        is_aggregate=is_aggregate,
        now_ts=now_ts,
    )


def _is_junior_persona(persona: str) -> bool:
    p = (persona or "").strip().upper()
    if p in ("CMD", "DIR_HR", "DIR_FIN", "DEMO_ADMIN"):
        return False
    return True


def _is_hr_roster_table(columns: List[str], rows: List[Dict[str, Any]], contract: Optional[Dict[str, Any]] = None) -> bool:
    c = contract or {}
    qspec = c.get("query_spec") if isinstance(c.get("query_spec"), dict) else {}
    if qspec.get("subject") == "workforce" or c.get("definition_id") == "DELHI_GT5_CONT_V1":
        return True
    col_set = {str(col).lower() for col in (columns or [])}
    if col_set & {"name", "emp_id", "emp_name", "delhi_tenure_years", "functional_designation"}:
        return True
    if rows and isinstance(rows[0], dict):
        row_keys = {str(k).lower() for k in rows[0].keys()}
        if row_keys & {"name", "emp_id", "emp_name", "delhi_tenure_years"}:
            return True
    return False


def _collapse_roster_to_grade_counts(
    rows: List[Dict[str, Any]],
    suppress_under_5: bool = True,
) -> Tuple[List[str], Dict[str, str], List[Dict[str, Any]]]:
    """Collapses individual roster rows into aggregate counts by grade/level (SPEC-07 §4.7 / SPEC-10 §4.10)."""
    counts: Dict[str, int] = {}
    for r in rows:
        if not isinstance(r, dict):
            continue
        g = str(r.get("grade") or r.get("level") or r.get("grade_id") or "Other")
        counts[g] = counts.get(g, 0) + 1

    grade_order = ["E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9", "GRP-B", "GRP-C", "GRP-D"]
    ordered_grades = [g for g in grade_order if g in counts] + sorted(g for g in counts if g not in grade_order)
    agg_rows: List[Dict[str, Any]] = [{"grade": g, "headcount": counts[g]} for g in ordered_grades]
    if suppress_under_5 and agg_rows:
        agg_rows, _ = suppress_small_cells(agg_rows, ["headcount"], threshold=5, by_name=False)
    cols = ["grade", "headcount"]
    headers = {"grade": "Level", "headcount": "Executives"}
    return cols, headers, agg_rows


def enforce_export_rbac(
    contract: Dict[str, Any],
    persona: str,
    requested_columns: Optional[List[str]] = None,
) -> Tuple[Dict[str, Any], bool, bool, List[str], List[str]]:
    """Applies RBAC post-guard (`enforce_contract` + SPEC-07 §4.7 / SPEC-10 §4.10 rules) on a contract copy.

    Returns `(masked_contract, masked_bool, is_aggregate_bool, data_classes, dropped_columns)`.
    - Junior personas (`E1_HR..E4_HR`, `E1_FIN..E4_FIN`): roster tables collapse to aggregate counts by
      level (with `<5` small-cell suppression), no `name`/`emp_id` column, `is_aggregate=True`, `masked=True`.
    - `DIR_FIN` on HR roster (SPEC-07 §4.7 T4): collapses to aggregate counts by level (`is_aggregate=True`, `masked=True`).
    - `CMD` and `DIR_HR`: full named roster allowed (`is_aggregate=False`, `masked=False`).
    - Any user-requested `columns` are mapped via `COLUMN_SYNONYM_MAP` and intersected with allowed columns;
      any disallowed/unknown requested columns are returned in `dropped_columns` so the route can name them in `toast`.
    """
    norm_p = (persona or "CMD").strip().upper()
    c = copy.deepcopy(contract or {})
    vis = c.setdefault("visual", {"type": "table", "mode": "replace"})
    tbl = vis.get("table") if isinstance(vis.get("table"), dict) else None

    data_classes: List[str] = ["general"]
    if tbl:
        raw_cols = list(tbl.get("columns") or [])
        raw_rows = list(tbl.get("rows") or [])
        for col in raw_cols:
            cls = column_class(col)
            if cls and cls not in data_classes:
                data_classes.append(cls)
        if _is_hr_roster_table(raw_cols, raw_rows, c) and "named" not in data_classes:
            data_classes.append("named")

    is_junior = _is_junior_persona(norm_p)
    is_dir_fin_on_hr = norm_p == "DIR_FIN" and tbl is not None and _is_hr_roster_table(
        list(tbl.get("columns") or []), list(tbl.get("rows") or []), c
    )

    dropped_columns: List[str] = []
    is_aggregate = False
    masked = False

    if tbl is not None and (is_junior or is_dir_fin_on_hr) and _is_hr_roster_table(
        list(tbl.get("columns") or []), list(tbl.get("rows") or []), c
    ):
        raw_rows = list(tbl.get("rows") or [])
        # Check if rows are still individual roster rows (have 'name' or 'emp_id' or >1 row per grade)
        has_named = any(
            column_class(col) in ("named", "pay", "apar", "sensitive")
            for col in (tbl.get("columns") or [])
        ) or any(
            isinstance(r, dict) and any(column_class(k) in ("named", "pay", "apar", "sensitive") for k in r.keys())
            for r in raw_rows
        )
        if has_named:
            cols, hdrs, agg_rows = _collapse_roster_to_grade_counts(raw_rows, suppress_under_5=is_junior)
            tbl["columns"] = cols
            tbl["headers"] = hdrs
            tbl["rows"] = agg_rows
            tbl["masking"] = {
                "level": "aggregate",
                "reason": f"Aggregate view (access level: {norm_p})",
                "rule_ref": "D-11" if is_junior else "D-43",
            }
            c.setdefault("access", {})["status"] = "partial"
            c.setdefault("rbac", {})["decision"] = "aggregate"
            is_aggregate = True
            masked = True

    # Run standard enforce_contract (for junior personas, also enforces small-cell suppression and strips restricted cols)
    c = enforce_contract(c, "E2_HR" if is_junior else norm_p)
    vis = c.get("visual") or {}
    tbl = vis.get("table") if isinstance(vis.get("table"), dict) else None

    if tbl and isinstance(tbl.get("masking"), dict):
        m_level = tbl["masking"].get("level")
        if m_level in ("aggregate", "partial", "refused"):
            masked = True
        if m_level == "aggregate":
            is_aggregate = True
    if (c.get("rbac") or {}).get("decision") == "aggregate":
        is_aggregate = True
        masked = True
    if (c.get("access") or {}).get("status") == "partial":
        masked = True

    # Intersect requested_columns if specified
    if requested_columns and tbl is not None:
        allowed_cols = list(tbl.get("columns") or [])
        allowed_lower = {col.lower(): col for col in allowed_cols}
        headers_map = tbl.get("headers") if isinstance(tbl.get("headers"), dict) else {}
        header_to_col = {str(v).lower(): k for k, v in headers_map.items()}

        kept: List[str] = []
        for req_col in requested_columns:
            rc_clean = str(req_col or "").strip()
            rc_low = rc_clean.lower()
            mapped = COLUMN_SYNONYM_MAP.get(rc_low, rc_clean)
            target = (
                allowed_lower.get(mapped.lower())
                or allowed_lower.get(rc_low)
                or header_to_col.get(rc_low)
            )
            if target and target in allowed_cols:
                if target not in kept:
                    kept.append(target)
            else:
                dropped_columns.append(rc_clean)

        if kept:
            tbl["columns"] = kept
            tbl["rows"] = [
                {k: r.get(k) for k in kept} if isinstance(r, dict) else r
                for r in (tbl.get("rows") or [])
            ]

    return c, masked, is_aggregate, sorted(set(data_classes)), dropped_columns


# ------------------------------------------------------------------ Turn & Artifact Registry
@dataclass
class TurnExportEntry:
    turn_id: str
    contract: Dict[str, Any]
    emp_id: str
    persona: str
    session_id: str = ""
    created_epoch: float = field(default_factory=time.time)


@dataclass
class ArtifactRecord:
    export_id: str
    kind: str
    filename: str
    url: str
    rows: int
    columns: List[str]
    masked: bool
    created_at: str
    expires_at: str
    sha256: str
    emp_id: str = ""
    persona: str = "CMD"
    session_id: str = ""
    turn_id: str = ""
    is_aggregate: bool = False
    disk_path: str = ""
    created_epoch: float = 0.0
    expires_epoch: float = 0.0

    def public_artifact(self) -> Dict[str, Any]:
        """Returns the canonical SPEC-10 §5 `Artifact` dictionary."""
        return {
            "export_id": self.export_id,
            "kind": self.kind,
            "filename": self.filename,
            "url": self.url,
            "rows": self.rows,
            "columns": list(self.columns),
            "masked": bool(self.masked),
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "sha256": self.sha256,
        }


_REGISTRY_LOCK = threading.Lock()
_TURN_STORE: Dict[str, TurnExportEntry] = {}
_ARTIFACT_STORE: Dict[str, ArtifactRecord] = {}


def register_turn_contract(
    turn_id: str,
    contract: Dict[str, Any],
    emp_id: str,
    persona: str,
    session_id: str = "",
) -> None:
    """Stores a post-enforce_contract turn contract tagged with its creating principal `(emp_id, persona)`."""
    if not turn_id:
        return
    with _REGISTRY_LOCK:
        _TURN_STORE[turn_id] = TurnExportEntry(
            turn_id=turn_id,
            contract=copy.deepcopy(contract),
            emp_id=emp_id or f"DEMO-{persona}",
            persona=(persona or "CMD").upper(),
            session_id=session_id or "",
        )
        if len(_TURN_STORE) > 500:
            oldest = min(_TURN_STORE, key=lambda k: _TURN_STORE[k].created_epoch)
            _TURN_STORE.pop(oldest, None)


def resolve_turn_contract(
    turn_id: str,
    principal_emp_id: str,
    principal_persona: str,
) -> Optional[Tuple[Dict[str, Any], str]]:
    """Looks up `turn_id` in `_TURN_STORE` or `SessionManager`.
    Raises `TurnOwnershipError` if the turn belongs to a different principal (SPEC-10 §4.10 item 1 -> 403).
    Returns `(contract, session_id)` or `None` if not found.
    """
    if not turn_id:
        return None
    with _REGISTRY_LOCK:
        entry = _TURN_STORE.get(turn_id)
    if entry is not None:
        if (entry.emp_id and principal_emp_id and entry.emp_id != principal_emp_id) or (
            entry.persona and principal_persona and entry.persona.upper() != principal_persona.upper()
        ):
            raise TurnOwnershipError(f"Turn {turn_id} belongs to another principal")
        return copy.deepcopy(entry.contract), entry.session_id

    # Fallback: check SessionManager turns
    try:
        from app.session_memory import get_session_manager

        sm = get_session_manager()
        for sid, sess in list(sm.sessions.items()):
            for t in reversed(sess.turns):
                if t.get("turn_id") == turn_id:
                    t_persona = str(t.get("persona") or sess.persona or "").upper()
                    if t_persona and principal_persona and t_persona != principal_persona.upper():
                        raise TurnOwnershipError(f"Turn {turn_id} belongs to persona {t_persona}")
                    return copy.deepcopy(t), sid
    except TurnOwnershipError:
        raise
    except Exception as exc:
        logger.debug(f"Session lookup for turn {turn_id} skipped: {exc}")
    return None


def _meta_sidecar_path(exports_dir: Path, export_id: str) -> Path:
    return exports_dir / f".{export_id}.meta.json"


def register_artifact(
    *,
    export_id: str,
    kind: str,
    filename: str,
    disk_path: Path,
    rows: int,
    columns: List[str],
    masked: bool,
    is_aggregate: bool,
    emp_id: str,
    persona: str,
    session_id: str = "",
    turn_id: str = "",
    ttl_seconds: int = DEFAULT_EXPORT_TTL_SECONDS,
    now_ts: Optional[float] = None,
) -> ArtifactRecord:
    """Computes SHA-256 of `disk_path`, stores `ArtifactRecord` in memory and sidecar JSON, and returns it."""
    created_epoch = float(now_ts if now_ts is not None else time.time())
    expires_epoch = created_epoch + float(ttl_seconds)
    created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(created_epoch))
    expires_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(expires_epoch))

    file_bytes = disk_path.read_bytes() if disk_path.exists() else b""
    sha256_hex = hashlib.sha256(file_bytes).hexdigest()

    rec = ArtifactRecord(
        export_id=export_id,
        kind=kind,
        filename=filename,
        url=f"/api/export/{export_id}",
        rows=int(rows),
        columns=list(columns),
        masked=bool(masked),
        created_at=created_at,
        expires_at=expires_at,
        sha256=sha256_hex,
        emp_id=emp_id or "",
        persona=(persona or "CMD").upper(),
        session_id=session_id or "",
        turn_id=turn_id or "",
        is_aggregate=bool(is_aggregate),
        disk_path=str(disk_path),
        created_epoch=created_epoch,
        expires_epoch=expires_epoch,
    )
    with _REGISTRY_LOCK:
        _ARTIFACT_STORE[export_id] = rec
    try:
        sidecar = _meta_sidecar_path(disk_path.parent, export_id)
        sidecar.write_text(json.dumps(asdict(rec), ensure_ascii=False), encoding="utf-8")
    except OSError as exc:
        logger.warning(f"Failed to write artifact sidecar for {export_id}: {exc}")
    return rec


def get_artifact_record(export_id: str, exports_dir: Path = EXPORTS_DIR) -> Optional[ArtifactRecord]:
    """Retrieves an `ArtifactRecord` from memory or disk sidecar."""
    with _REGISTRY_LOCK:
        rec = _ARTIFACT_STORE.get(export_id)
    if rec is not None:
        return rec
    sidecar = _meta_sidecar_path(exports_dir, export_id)
    if sidecar.exists():
        try:
            data = json.loads(sidecar.read_text(encoding="utf-8"))
            rec = ArtifactRecord(**data)
            with _REGISTRY_LOCK:
                _ARTIFACT_STORE[export_id] = rec
            return rec
        except Exception as exc:
            logger.warning(f"Could not load sidecar for {export_id}: {exc}")
    return None


def verify_artifact_access(
    export_id: str,
    principal_emp_id: str,
    principal_persona: str,
    exports_dir: Path = EXPORTS_DIR,
    now_ts: Optional[float] = None,
) -> Optional[ArtifactRecord]:
    """Verifies that `export_id` is not expired and belongs to `(principal_emp_id, principal_persona)`.
    - Raises `TurnOwnershipError` if owned by another principal (-> HTTP 403).
    - Returns `None` if expired (and deletes file + sidecar) so route returns HTTP 404.
    """
    rec = get_artifact_record(export_id, exports_dir=exports_dir)
    if rec is None:
        return None
    now = float(now_ts if now_ts is not None else time.time())
    if rec.expires_epoch > 0 and now > rec.expires_epoch:
        # Expired -> remove file and sidecar
        try:
            if rec.disk_path:
                Path(rec.disk_path).unlink(missing_ok=True)
            _meta_sidecar_path(exports_dir, export_id).unlink(missing_ok=True)
        except OSError:
            pass
        with _REGISTRY_LOCK:
            _ARTIFACT_STORE.pop(export_id, None)
        return None

    if (rec.emp_id and principal_emp_id and rec.emp_id != principal_emp_id) or (
        rec.persona and principal_persona and rec.persona.upper() != principal_persona.upper()
    ):
        raise TurnOwnershipError(f"Export {export_id} belongs to another principal")
    return rec


# ------------------------------------------------------------------ Audit Logger (SPEC-10 §4.10 item 4)
_EXPORT_AUDIT_LOCK = threading.Lock()


def export_audit_path() -> Path:
    env = os.getenv("YUKTI_EXPORT_AUDIT_LOG")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent / "logs" / "export_audit.jsonl"


def hash_client_ip(client_ip: Optional[str]) -> str:
    raw = (client_ip or "127.0.0.1").strip()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def write_export_audit(
    *,
    emp_id: str,
    persona: str,
    session_id: str,
    turn_id: str,
    fmt: str,
    filename: str,
    sha256: str,
    rows: int,
    columns: List[str],
    data_classes: List[str],
    masked: bool,
    delivery: str = "download",
    client_ip: Optional[str] = None,
    now_ts: Optional[float] = None,
) -> Dict[str, Any]:
    """Appends one row matching `hrfin_ops.export_audit` to local JSONL fallback (no bq calls)."""
    ts_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now_ts if now_ts is not None else time.time()))
    deliv = delivery if delivery in ("download", "eml", "drive") else "download"
    row = {
        "ts": ts_str,
        "emp_id": emp_id or f"DEMO-{persona}",
        "persona": (persona or "CMD").upper(),
        "session_id": session_id or "",
        "turn_id": turn_id or "",
        "format": (fmt or "xlsx").lower(),
        "filename": filename,
        "sha256": sha256 or "",
        "rows": int(rows),
        "columns": [str(c) for c in (columns or [])],
        "data_classes": [str(dc) for dc in (data_classes or ["general"])],
        "masked": bool(masked),
        "delivery": deliv,
        "client_ip_hash": hash_client_ip(client_ip),
    }
    try:
        p = export_audit_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        with _EXPORT_AUDIT_LOCK, open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError as exc:
        logger.warning(f"export_audit write failed: {exc}")
    return row


def read_export_audit_rows(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Helper for tests to read back JSONL rows written to `export_audit.jsonl`."""
    p = path or export_audit_path()
    if not p.exists():
        return []
    out: List[Dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out
