"""Configuration settings for Yukti AI agent backend.
"""

from pathlib import Path
import os

# Root directory of the project
APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
ROOT_DIR = BACKEND_DIR.parent.parent

# Paths to data bank, contracts, templates, exports
DATA_BANK_DIR = ROOT_DIR / "data_bank"
RULEBOOKS_CSV_PATH = DATA_BANK_DIR / "landing" / "documents" / "rulebooks_clause_index.csv"
TEMPLATES_DIR = DATA_BANK_DIR / "landing" / "documents" / "templates"
CONTRACT_SCHEMA_PATH = ROOT_DIR / "yukti" / "contracts" / "answer_contract.schema.json"
EXPORTS_DIR = BACKEND_DIR / "exports"

EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

# GCP settings
GCP_PROJECT = os.getenv("TARGET_PROJECT") or os.getenv("YUKTI_GCP_PROJECT") or "ongc-hr-finance-agent"
BQ_LOCATION = os.getenv("BQ_LOCATION", "asia-south1")
VERTEX_LOCATION = os.getenv("VERTEX_LOCATION", "us-central1")
VERTEX_TEXT_LOCATION = os.getenv("YUKTI_TEXT_LOCATION", "global")
VERTEX_SEARCH_LOCATION = os.getenv("VERTEX_SEARCH_LOCATION", "global")
VERTEX_SEARCH_ENGINE = "hrfin-doc-search-engine"

# Models and Voices
DEFAULT_TEXT_MODEL = os.getenv("YUKTI_TEXT_MODEL", "gemini-2.5-flash")
DEFAULT_LIVE_MODEL = os.getenv("YUKTI_LIVE_MODEL", "gemini-3.8-live")
FALLBACK_LIVE_MODEL = "gemini-live-2.5-flash-native-audio"
DEFAULT_VOICE = "Leda"
FALLBACK_VOICE = "Aoede"

# Option A Tool-Result Cache: ON by default for demo runs, forced OFF during eval
YUKTI_RESULT_CACHE = os.getenv("YUKTI_RESULT_CACHE", "1") in ("1", "true", "yes")

# Full-answer Demo cache flag: OFF by default (backup switch)
YUKTI_FIN_SSOT_V3 = os.getenv("YUKTI_FIN_SSOT_V3", "1") in ("1", "true", "yes")
YUKTI_DEMO_CACHE = os.getenv("YUKTI_DEMO_CACHE", "0") in ("1", "true", "yes")

# BigQuery Datasets (allow-listed suffix & dataset names to prevent SQL injection via env)
ALLOWED_DATASET_SUFFIXES = {"", "v3", "_v3"}
ALLOWED_DATASET_NAMES = {
    "hrfin_gold",
    "hrfin_gold_v3",
    "hrfin_silver",
    "hrfin_silver_v3",
    "hrfin_bronze",
    "hrfin_bronze_v3",
    "hrfin_stage",
    "hrfin_stage_v3",
    "hrfin_ref",
    "hrfin_ref_v3",
    "hrfin_docs",
}


def _validate_dataset_suffix(raw_suffix: str) -> str:
    sfx = (raw_suffix or "").strip()
    if sfx not in ALLOWED_DATASET_SUFFIXES:
        raise ValueError(f"Disallowed BQ_DATASET_SUFFIX={sfx!r}; must be one of {sorted(ALLOWED_DATASET_SUFFIXES)}")
    return f"_{sfx.lstrip('_')}" if sfx else ""


def _validate_dataset_name(name: str, expected_prefix: str) -> str:
    cleaned = (name or "").strip()
    if cleaned not in ALLOWED_DATASET_NAMES or not cleaned.startswith(expected_prefix):
        raise ValueError(
            f"Disallowed BigQuery dataset identifier {cleaned!r} for {expected_prefix}; "
            f"must be in {sorted(ALLOWED_DATASET_NAMES)}"
        )
    return cleaned


BQ_DATASET_SUFFIX = os.getenv("BQ_DATASET_SUFFIX", os.getenv("YUKTI_DATASET_SUFFIX", "")).strip()
_DS_SFX = _validate_dataset_suffix(BQ_DATASET_SUFFIX)
BQ_GOLD_DATASET = _validate_dataset_name(
    os.getenv("BQ_GOLD_DATASET", os.getenv("YUKTI_GOLD_DATASET", f"hrfin_gold{_DS_SFX}")),
    "hrfin_gold",
)
BQ_SILVER_DATASET = _validate_dataset_name(
    os.getenv("BQ_SILVER_DATASET", os.getenv("YUKTI_SILVER_DATASET", f"hrfin_silver{_DS_SFX}")),
    "hrfin_silver",
)
BQ_BRONZE_DATASET = _validate_dataset_name(
    os.getenv("BQ_BRONZE_DATASET", os.getenv("YUKTI_BRONZE_DATASET", f"hrfin_bronze{_DS_SFX}")),
    "hrfin_bronze",
)
BQ_STAGE_DATASET = _validate_dataset_name(
    os.getenv("BQ_STAGE_DATASET", os.getenv("YUKTI_STAGE_DATASET", f"hrfin_stage{_DS_SFX}")),
    "hrfin_stage",
)
BQ_REF_DATASET = _validate_dataset_name(
    os.getenv("BQ_REF_DATASET", os.getenv("YUKTI_REF_DATASET", f"hrfin_ref{_DS_SFX}")),
    "hrfin_ref",
)
BQ_DOCS_DATASET = _validate_dataset_name(
    os.getenv("BQ_DOCS_DATASET", os.getenv("YUKTI_DOCS_DATASET", "hrfin_docs")),
    "hrfin_docs",
)

ALLOWED_DATASETS = {
    "hrfin_gold",
    "hrfin_silver",
    "hrfin_docs",
    "hrfin_ref",
    BQ_GOLD_DATASET,
    BQ_SILVER_DATASET,
    BQ_REF_DATASET,
    BQ_DOCS_DATASET,
}


def rewrite_dataset_sql(sql: str) -> str:
    """Rewrite canonical dataset names to the configured dataset names (e.g. _v3) when overridden."""
    if not sql:
        return sql
    import re
    out = sql
    replacements = (
        ("hrfin_gold", BQ_GOLD_DATASET),
        ("hrfin_silver", BQ_SILVER_DATASET),
        ("hrfin_ref", BQ_REF_DATASET),
        ("hrfin_bronze", BQ_BRONZE_DATASET),
        ("hrfin_stage", BQ_STAGE_DATASET),
    )
    for base_ds, target_ds in replacements:
        _validate_dataset_name(target_ds, base_ds)
        if target_ds != base_ds:
            out = re.sub(rf"\b{base_ds}\b", target_ds, out)
    if BQ_GOLD_DATASET == "hrfin_gold_v3":
        # Route unqualified field_pnl_annual (e.g. C6) to the RAS-reconciled v3 view in hrfin_gold_v3
        out = re.sub(
            r"(?<![.\w`])field_pnl_annual\b",
            f"`{GCP_PROJECT}.hrfin_gold_v3.v_field_pnl_v3`",
            out,
        )
        # Route annual field_pnl queries on ssot_field_economics_360 (field_id IS NOT NULL) to v_field_pnl_v3 (over v_field_economics_fy)
        if "hrfin_gold_v3.ssot_field_economics_360" in out and "field_id IS NOT NULL" in out:
            out = (
                out.replace(
                    f"`{GCP_PROJECT}.hrfin_gold_v3.ssot_field_economics_360`",
                    f"`{GCP_PROJECT}.hrfin_gold_v3.v_field_pnl_v3`",
                )
                .replace(
                    "WHERE field_id IS NOT NULL",
                    "WHERE field_id IS NOT NULL AND LOWER(line_type) = 'field'",
                )
                .replace(
                    "AND pnl.field_id IS NOT NULL",
                    "AND pnl.field_id IS NOT NULL AND LOWER(pnl.line_type) = 'field'",
                )
            )
    return out


JOB_LABELS = {"datacloud": os.getenv("YUKTI_JOB_LABEL_VALUE", "ai-agent")}
MAX_BYTES_BILLED = int(os.getenv("YUKTI_MAX_BYTES_BILLED", "524288000"))  # 500 MB
FX_INR_PER_USD = float(os.getenv("YUKTI_FX_INR_PER_USD", "88.33"))

# P0.5 (BUG-32, SPEC-06 §4.7): deployment environment, admin routes and CORS allow-list
YUKTI_ENV = os.getenv("YUKTI_ENV", "dev").strip().lower()
YUKTI_ENABLE_ADMIN = os.getenv("YUKTI_ENABLE_ADMIN", "0").strip() == "1"
DEFAULT_ALLOWED_ORIGINS = "http://localhost:3300,http://127.0.0.1:3300,http://localhost:3200,http://127.0.0.1:3200"


def allowed_origins() -> list:
    """Comma list from YUKTI_ALLOWED_ORIGINS. A wildcard is never allowed (credentials are on): it is logged and dropped."""
    import logging
    env_val = os.getenv("YUKTI_ALLOWED_ORIGINS")
    if env_val is None and os.getenv("YUKTI_ENV", "dev").strip().lower() == "prod":
        # P0.5 r2 (G4 minor): prod never trusts the localhost dev origins by default
        logging.getLogger("yukti.config").warning("YUKTI_ENV=prod and YUKTI_ALLOWED_ORIGINS unset: no cross-origin callers allowed")
        return []
    raw = env_val if env_val is not None else DEFAULT_ALLOWED_ORIGINS
    items = [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]
    if "*" in items:
        logging.getLogger("yukti.config").error("YUKTI_ALLOWED_ORIGINS contains '*'; dropped (never '*' with credentials)")
        items = [o for o in items if o != "*"]
    return items

def v3_field_enabled(field: str) -> bool:
    fields = [x.strip() for x in os.getenv("YUKTI_CONTRACT_V3_FIELDS", "").split(",") if x.strip()]
    return field in fields
