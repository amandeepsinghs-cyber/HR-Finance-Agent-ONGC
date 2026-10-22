#!/usr/bin/env python3
"""Builds yukti/backend/certified/library.yaml from the 89 ROOT entries only.
Provenance is strictly tracked: each entry records source SQL file path and SHA-256.
Follow-up SQL and paraphrases.yaml are strictly excluded to preserve evaluation integrity.
"""

from collections import OrderedDict
import hashlib
from pathlib import Path
import re
import yaml

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_BANK_DIR = ROOT_DIR / "data_bank"
ANSWER_KEY_DIR = DATA_BANK_DIR / "answer_key"
SQL_DIR = ANSWER_KEY_DIR / "sql"
QUESTIONS_PATH = DATA_BANK_DIR / "world_bible" / "reference" / "questions.yaml"
INDEX_PATH = ANSWER_KEY_DIR / "INDEX.md"

BACKEND_DIR = Path(__file__).resolve().parent.parent
CERTIFIED_DIR = BACKEND_DIR / "certified"
CERTIFIED_LIBRARY_PATH = CERTIFIED_DIR / "library.yaml"

# Keyword extractor
STOP_WORDS = {
    "what", "is", "our", "the", "in", "by", "and", "or", "to", "for", "of", "a", "an",
    "how", "many", "much", "which", "are", "we", "did", "have", "been", "last", "this",
    "next", "over", "under", "with", "from", "on", "at", "who", "show", "me", "prepare",
    "generate", "list", "does", "can", "if", "would", "will", "per", "vs", "versus"
}


def extract_keywords(qid: str, question: str, group: str) -> list[str]:
    """Generates 3 to 6 high-relevance intent keywords."""
    combined = f"{question} {group}".lower()
    cleaned = re.sub(r"[^a-z0-9\s\-]", " ", combined)
    tokens = [t.strip() for t in cleaned.split() if len(t.strip()) > 2 and t.strip() not in STOP_WORDS]

    # Priority terms by domain
    domain_terms = [
        "delhi", "tenure", "rotation", "continuous_stay", "pnl", "loss-making",
        "lifting_cost", "vacancies", "superannuation", "retirement", "headcount",
        "divestment", "mou", "overtime", "clra", "contract_workers", "capex",
        "cag", "rti", "csr", "ebitda", "pbt", "champang", "mumbai", "tripura",
        "assam", "discipline", "grade", "promotion", "dpc", "refusal", "salary"
    ]

    kw = []
    for dt in domain_terms:
        if dt in combined and dt not in kw:
            kw.append(dt)
            if len(kw) >= 5:
                break

    for t in tokens:
        if t not in kw and len(kw) < 6:
            kw.append(t)

    return kw[:6] if len(kw) >= 3 else (kw + ["ongc", "query"])[:4]


def parameterize_sql(sql_content: str, qid: str) -> tuple[str, dict]:
    """Rewrites SQL into a parameterized template with named @params and default metadata."""
    params = OrderedDict()
    param_sql = sql_content

    # 1. Fiscal Year Parameterization
    if re.search(r"fiscal_year\s*=\s*'FY26'", param_sql, re.IGNORECASE):
        param_sql = re.sub(
            r"(fiscal_year\s*=\s*)'FY26'",
            r"\1@fiscal_year",
            param_sql,
            flags=re.IGNORECASE,
        )
        params["fiscal_year"] = {
            "type": "STRING",
            "default": "FY26",
            "description": "Fiscal year in FYxx format",
            "allowed_values": ["FY21", "FY22", "FY23", "FY24", "FY25", "FY26", "FY27"],
        }
    elif re.search(r"'FY26'", param_sql):
        param_sql = param_sql.replace("'FY26'", "@fiscal_year")
        params["fiscal_year"] = {
            "type": "STRING",
            "default": "FY26",
            "description": "Fiscal year in FYxx format",
            "allowed_values": ["FY21", "FY22", "FY23", "FY24", "FY25", "FY26", "FY27"],
        }

    # 2. Work Centre Parameterization
    wc_matches = re.findall(r"'WC-([A-Z0-9&]+)'", param_sql)
    if wc_matches:
        primary_wc = f"WC-{wc_matches[0]}"
        # Replace the first primary occurrence with @wc_id
        param_sql = re.sub(
            r"(=|\sIN\s*\()\s*'" + re.escape(primary_wc) + r"'",
            r"\1 @wc_id",
            param_sql,
            count=1,
        )
        params["wc_id"] = {
            "type": "STRING",
            "default": primary_wc,
            "description": "ONGC Work Centre code",
            "allowed_values": [
                "WC-DEL", "WC-DDN", "WC-MUM", "WC-TRI", "WC-ASM", "WC-JOR", "WC-AAB",
                "WC-AHM", "WC-ANK", "WC-MEH", "WC-CAM", "WC-RAJ", "WC-EAS", "WC-ROC",
                "WC-ROK", "WC-BOK", "WC-SIL"
            ],
        }

    # 3. Minimum Continuous Stay Months Parameterization
    if re.search(r"continuous_stay_months\s*>=\s*60", param_sql):
        param_sql = re.sub(
            r"continuous_stay_months\s*>=\s*60",
            "continuous_stay_months >= @min_stay_months",
            param_sql,
        )
        params["min_stay_months"] = {
            "type": "INT64",
            "default": 60,
            "description": "Minimum continuous posting duration in months",
            "allowed_values": [12, 24, 36, 48, 60, 72, 84, 96, 120],
        }
    elif re.search(r"continuous_stay_months\s*>=\s*36", param_sql):
        param_sql = re.sub(
            r"continuous_stay_months\s*>=\s*36",
            "continuous_stay_months >= @min_stay_months",
            param_sql,
        )
        params["min_stay_months"] = {
            "type": "INT64",
            "default": 36,
            "description": "Minimum continuous posting duration in months",
            "allowed_values": [12, 24, 36, 48, 60, 72, 84, 96, 120],
        }

    # 4. Field Parameterization
    if "'FLD-CHP'" in param_sql:
        param_sql = param_sql.replace("'FLD-CHP'", "@field_id")
        params["field_id"] = {
            "type": "STRING",
            "default": "FLD-CHP",
            "description": "ONGC Field identifier code",
            "allowed_values": ["FLD-CHP", "FLD-MHN", "FLD-MHS", "FLD-GND", "FLD-ANK", "FLD-BSS"],
        }

    # 5. Grade Parameterization
    if re.search(r"grade_id\s*>=\s*'E7'", param_sql):
        param_sql = re.sub(r"grade_id\s*>=\s*'E7'", "grade_id >= @min_grade", param_sql)
        params["min_grade"] = {
            "type": "STRING",
            "default": "E7",
            "description": "Minimum executive grade threshold",
            "allowed_values": ["E0", "E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9"],
        }

    return param_sql, dict(params)


def build():
    """Main build routine for certified/library.yaml."""
    CERTIFIED_DIR.mkdir(parents=True, exist_ok=True)

    with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
        questions = yaml.safe_load(f)["questions"]

    # Read INDEX.md headlines and metadata
    index_meta = {}
    if INDEX_PATH.exists():
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("| `"):
                    parts = [p.strip().replace("`", "") for p in line.split("|")]
                    if len(parts) >= 10 and parts[3] == "root":
                        index_meta[parts[1]] = {
                            "status": parts[5],
                            "gold_objects": parts[7],
                            "headline": parts[9],
                        }

    library_entries = []

    print(f"Building certified query library from {len(questions)} root questions...")

    for q in questions:
        qid = q["id"]
        # Ensure only roots are processed
        if "__" in qid:
            continue

        sql_path = SQL_DIR / f"{qid}.sql"
        if not sql_path.exists():
            raise FileNotFoundError(f"Missing root SQL file: {sql_path}")

        raw_sql = sql_path.read_text(encoding="utf-8").strip()
        sha256_hash = hashlib.sha256(raw_sql.encode("utf-8")).hexdigest()

        param_sql, params = parameterize_sql(raw_sql, qid)

        meta = index_meta.get(qid, {})
        headline = meta.get("headline", q["question"])

        # Determine visual kind
        exp_out = q.get("expected_output", "table")
        if exp_out == "refusal":
            visual_kind = "refusal"
        elif exp_out == "document":
            visual_kind = "document"
        elif exp_out == "number":
            visual_kind = "kpi_card"
        elif any(k in q["question"].lower() for k in ["break down", "compare", "ranking", "top"]):
            visual_kind = "bar_chart"
        else:
            visual_kind = "table"

        entry = {
            "id": qid,
            "group": q.get("group", ""),
            "canonical_question": q["question"],
            "intent_keywords": extract_keywords(qid, q["question"], q.get("group", "")),
            "intent_description": headline[:140],
            "parameterized_sql": param_sql,
            "params": params,
            "visual_kind": visual_kind,
            "provenance": {
                "source_file": f"data_bank/answer_key/sql/{qid}.sql",
                "sha256": sha256_hash,
                "gold_objects": meta.get("gold_objects", ""),
            },
        }
        library_entries.append(entry)

    # Sort deterministically by id
    library_data = {
        "version": "1.0",
        "description": "Certified parameterized query library for Yukti AI Track C engine (89 Root Queries).",
        "provenance_policy": "Strict derivation from verified answer_key/sql roots. Follow-ups and paraphrases held out.",
        "queries": library_entries,
    }

    with open(CERTIFIED_LIBRARY_PATH, "w", encoding="utf-8") as f:
        yaml.dump(library_data, f, sort_keys=False, width=120, allow_unicode=True)

    print(f"✓ Successfully wrote {len(library_entries)} certified queries to {CERTIFIED_LIBRARY_PATH}")
    assert len(library_entries) == 89, f"Expected 89 entries, got {len(library_entries)}"


if __name__ == "__main__":
    build()
