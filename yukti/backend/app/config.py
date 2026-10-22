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
YUKTI_DEMO_CACHE = os.getenv("YUKTI_DEMO_CACHE", "0") in ("1", "true", "yes")

# BigQuery Datasets
ALLOWED_DATASETS = {
    "hrfin_gold",
    "hrfin_silver",
    "hrfin_docs",
}

JOB_LABELS = {"datacloud": "ai-agent"}
MAX_BYTES_BILLED = 524_288_000  # 500 MB
FX_INR_PER_USD = float(os.getenv("YUKTI_FX_INR_PER_USD", "88.33"))

