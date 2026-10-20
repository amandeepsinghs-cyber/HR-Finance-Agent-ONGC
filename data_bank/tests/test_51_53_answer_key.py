"""test_51_53_answer_key.py — Pytest suite for Phase 5 steps 5.1, 5.2, and 5.3.

Validates:
1. Presence of all 89 root questions across answer_key/sql/, answer_key/expected/, answer_key/answers/
2. Presence of all 267 follow-up questions across answer_key/followups/<parent>__<kind>.{sql,json,md}
3. 267 authentic paraphrases in answer_key/paraphrases.yaml (3 per root question)
4. Follow-up results are non-empty and DIFFERENT from their parent's result set
5. Direct BigQuery execution of answer key SQLs matches stored expected JSONs
6. Comprehensive coverage in answer_key/INDEX.md
"""

from __future__ import annotations

import datetime
from decimal import Decimal
import json
from pathlib import Path
from typing import Any, Dict, List
from concurrent.futures import ThreadPoolExecutor

import pytest
import yaml
from google.cloud import bigquery

PROJECT_ID = "ongc-hr-finance-agent"
LOCATION = "asia-south1"
JOB_LABELS = {"datacloud": "ai-agent"}

DATA_BANK_DIR = Path(__file__).resolve().parent.parent
QUESTIONS_PATH = DATA_BANK_DIR / "world_bible" / "reference" / "questions.yaml"
SQL_DIR = DATA_BANK_DIR / "answer_key" / "sql"
EXPECTED_DIR = DATA_BANK_DIR / "answer_key" / "expected"
ANSWERS_DIR = DATA_BANK_DIR / "answer_key" / "answers"
FOLLOWUPS_DIR = DATA_BANK_DIR / "answer_key" / "followups"
PARAPHRASES_PATH = DATA_BANK_DIR / "answer_key" / "paraphrases.yaml"
INDEX_PATH = DATA_BANK_DIR / "answer_key" / "INDEX.md"


@pytest.fixture(scope="session")
def questions_manifest() -> List[Dict[str, Any]]:
    with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["questions"]


@pytest.fixture(scope="session")
def bq_client() -> bigquery.Client:
    return bigquery.Client(project=PROJECT_ID, location=LOCATION)


def test_01_all_root_entries_present(questions_manifest):
    """Verify all 89 root questions have SQL, expected JSON, and Answer MD."""
    assert len(questions_manifest) == 89

    missing_sql = []
    missing_json = []
    missing_md = []

    for q in questions_manifest:
        qid = q["id"]
        sql_file = SQL_DIR / f"{qid}.sql"
        json_file = EXPECTED_DIR / f"{qid}.json"
        md_file = ANSWERS_DIR / f"{qid}.md"

        if not sql_file.exists():
            missing_sql.append(qid)
        if not json_file.exists():
            missing_json.append(qid)
        if not md_file.exists():
            missing_md.append(qid)

    assert not missing_sql, f"Missing root SQL files: {missing_sql}"
    assert not missing_json, f"Missing root JSON files: {missing_json}"
    assert not missing_md, f"Missing root MD files: {missing_md}"

    sql_files = list(SQL_DIR.glob("*.sql"))
    json_files = list(EXPECTED_DIR.glob("*.json"))
    md_files = list(ANSWERS_DIR.glob("*.md"))

    assert len(sql_files) == 89
    assert len(json_files) == 89
    assert len(md_files) == 89


def test_02_all_followup_entries_present(questions_manifest):
    """Verify all 267 follow-ups have SQL, expected JSON, and Answer MD."""
    expected_fus = []
    for q in questions_manifest:
        qid = q["id"]
        for fu in q.get("followups", []):
            kind = fu["kind"]
            expected_fus.append(f"{qid}__{kind}")

    assert len(expected_fus) == 267

    missing_sql = []
    missing_json = []
    missing_md = []

    for fuid in expected_fus:
        sql_file = FOLLOWUPS_DIR / f"{fuid}.sql"
        json_file = FOLLOWUPS_DIR / f"{fuid}.json"
        md_file = FOLLOWUPS_DIR / f"{fuid}.md"

        if not sql_file.exists():
            missing_sql.append(fuid)
        if not json_file.exists():
            missing_json.append(fuid)
        if not md_file.exists():
            missing_md.append(fuid)

    assert not missing_sql, f"Missing follow-up SQL files: {missing_sql}"
    assert not missing_json, f"Missing follow-up JSON files: {missing_json}"
    assert not missing_md, f"Missing follow-up MD files: {missing_md}"

    fu_sql_files = list(FOLLOWUPS_DIR.glob("*.sql"))
    fu_json_files = list(FOLLOWUPS_DIR.glob("*.json"))
    fu_md_files = list(FOLLOWUPS_DIR.glob("*.md"))

    assert len(fu_sql_files) == 267
    assert len(fu_json_files) == 267
    assert len(fu_md_files) == 267


def test_03_paraphrases_complete_and_valid():
    """Verify paraphrases.yaml has 267 total paraphrases across all 89 questions."""
    assert PARAPHRASES_PATH.exists()
    with open(PARAPHRASES_PATH, "r", encoding="utf-8") as f:
        pdata = yaml.safe_load(f)

    meta = pdata.get("metadata", {})
    assert meta.get("total_questions") == 89
    assert meta.get("total_paraphrases") == 267

    paraphrases = pdata.get("paraphrases", [])
    assert len(paraphrases) == 89

    for p in paraphrases:
        assert p.get("id")
        assert p.get("original")
        assert p.get("formal") and len(p["formal"]) > 10
        assert p.get("casual") and len(p["casual"]) > 10
        assert p.get("hinglish") and len(p["hinglish"]) > 10


def test_04_followup_results_non_empty_and_different_from_parent(questions_manifest):
    """Verify every follow-up returns non-empty results different from its parent."""
    empty_fus = []
    identical_fus = []

    for q in questions_manifest:
        qid = q["id"]
        parent_json_path = EXPECTED_DIR / f"{qid}.json"
        with open(parent_json_path, "r", encoding="utf-8") as f:
            pdata = json.load(f)

        p_rows = pdata.get("rows", [])

        for fu in q.get("followups", []):
            kind = fu["kind"]
            fu_id = f"{qid}__{kind}"
            fu_json_path = FOLLOWUPS_DIR / f"{fu_id}.json"
            with open(fu_json_path, "r", encoding="utf-8") as f:
                fdata = json.load(f)

            fu_rows = fdata.get("rows", [])
            row_count = fdata.get("row_count", 0)

            if row_count == 0 or len(fu_rows) == 0:
                empty_fus.append(fu_id)
            if fu_rows == p_rows:
                identical_fus.append(fu_id)

    assert not empty_fus, f"Found empty follow-up results: {empty_fus}"
    assert not identical_fus, f"Found follow-ups identical to parent: {identical_fus}"


def test_05_index_markdown_integrity(questions_manifest):
    """Verify answer_key/INDEX.md exists and indexes all 356 entries."""
    assert INDEX_PATH.exists()
    content = INDEX_PATH.read_text(encoding="utf-8")

    assert "Total Entries:** `356`" in content
    assert "Audit Status:** `334` Answered, `22` Refusals, `0` Gaps" in content

    # Check sample key entries exist in table
    assert "| `C1` |" in content
    assert "| `C1__drill_down` |" in content
    assert "| `D1` |" in content
    assert "| `P1` |" in content
    assert "| `W1` |" in content
    assert "| `X10__compare_or_so_what` |" in content


def test_06_bigquery_live_rerun_parity_spotcheck(bq_client, questions_manifest):
    """Rerun a representative cross-domain sample of SQL queries against BigQuery and verify exact row count match."""
    sample_ids = [
        ("root", "C1"),
        ("root", "C6"),
        ("root", "C14"),
        ("root", "H1"),
        ("root", "F1"),
        ("root", "D1"),
        ("root", "P1"),
        ("root", "W1"),
        ("followup", "C1__drill_down"),
        ("followup", "C1__why"),
        ("followup", "C1__compare_or_so_what"),
        ("followup", "H1__drill_down"),
        ("followup", "F1__compare_or_so_what"),
        ("followup", "D1__drill_down"),
        ("followup", "P1__drill_down"),
        ("followup", "W1__drill_down")
    ]

    cfg = bigquery.QueryJobConfig(
        default_dataset=f"{PROJECT_ID}.hrfin_silver",
        labels=JOB_LABELS,
        use_query_cache=False
    )

    def verify_one(item):
        cat, eid = item
        if cat == "root":
            sql = (SQL_DIR / f"{eid}.sql").read_text(encoding="utf-8")
            expected_json = json.loads((EXPECTED_DIR / f"{eid}.json").read_text(encoding="utf-8"))
        else:
            sql = (FOLLOWUPS_DIR / f"{eid}.sql").read_text(encoding="utf-8")
            expected_json = json.loads((FOLLOWUPS_DIR / f"{eid}.json").read_text(encoding="utf-8"))

        clean_sql = "\n".join([l for l in sql.splitlines() if not l.strip().startswith("--")]).strip()
        job = bq_client.query(clean_sql, job_config=cfg)
        rows = list(job.result())
        return eid, len(rows), expected_json["row_count"]

    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(verify_one, sample_ids))

    mismatches = []
    for eid, live_count, exp_count in results:
        if live_count != exp_count:
            mismatches.append(f"{eid}: live={live_count} vs exp={exp_count}")

    assert not mismatches, f"Row count mismatches upon live rerun: {mismatches}"


def test_07_full_356_entries_rerun_audit(bq_client):
    """Execute all 356 SQL queries (89 root + 267 follow-ups) in BigQuery and verify 100% row count match with expected JSON."""
    sql_files = list(SQL_DIR.glob("*.sql")) + list(FOLLOWUPS_DIR.glob("*.sql"))
    assert len(sql_files) == 356

    cfg = bigquery.QueryJobConfig(
        default_dataset=f"{PROJECT_ID}.hrfin_silver",
        labels=JOB_LABELS,
        use_query_cache=False
    )

    def verify_query(sf):
        is_fu = "__" in sf.stem
        if not is_fu:
            json_path = EXPECTED_DIR / f"{sf.stem}.json"
        else:
            json_path = FOLLOWUPS_DIR / f"{sf.stem}.json"

        exp_data = json.loads(json_path.read_text(encoding="utf-8"))
        exp_count = exp_data["row_count"]

        sql = "\n".join([l for l in sf.read_text(encoding="utf-8").splitlines() if not l.strip().startswith("--")]).strip()
        try:
            job = bq_client.query(sql, job_config=cfg)
            rows = list(job.result())
            return sf.stem, True, len(rows), exp_count
        except Exception as e:
            return sf.stem, False, str(e), exp_count

    with ThreadPoolExecutor(max_workers=20) as ex:
        results = list(ex.map(verify_query, sql_files))

    failed_exec = [r for r in results if not r[1]]
    mismatched_count = [r for r in results if r[1] and r[2] != r[3]]

    assert not failed_exec, f"Failed SQL executions in BigQuery: {failed_exec[:5]}"
    assert not mismatched_count, f"Row count mismatches upon full rerun: {mismatched_count[:5]}"


def test_08_w1_formula_reproduces_v_field_pnl_ebitda(bq_client):
    """Verify that at FY26 actual prices, the W1 simulation formula reproduces v_field_pnl EBITDA within 0.5% for every field."""
    q_check = f"""
    WITH price_params AS (
        SELECT
            AVG(brent_usd_bbl) AS avg_brent,
            AVG(ongc_crude_net_realisation_usd_bbl) AS avg_realisation,
            AVG(brent_usd_bbl - ongc_crude_net_realisation_usd_bbl) AS avg_discount
        FROM `{PROJECT_ID}.hrfin_silver.price_fx_monthly`
        WHERE fiscal_year IN ('FY26', '2026')
    ),
    sim_actual AS (
        SELECT
            pnl.field_id,
            f.name AS field_name,
            pnl.ebitda_inr_cr AS actual_ebitda,
            (pnl.oil_revenue_inr_cr * ((params.avg_brent - params.avg_discount) / params.avg_realisation) + pnl.gas_revenue_inr_cr) AS sim_gross_rev,
            SAFE_DIVIDE(pnl.statutory_royalty_inr_cr, NULLIF(pnl.gross_revenue_inr_cr, 0)) AS eff_royalty_rate,
            SAFE_DIVIDE(pnl.statutory_cess_inr_cr, NULLIF(pnl.gross_revenue_inr_cr, 0)) AS eff_cess_rate,
            pnl.total_opex_inr_cr AS total_opex_inr_cr
        FROM `{PROJECT_ID}.hrfin_silver.field_pnl_annual` pnl
        JOIN `{PROJECT_ID}.hrfin_silver.dim_field` f ON pnl.field_id = f.field_id
        CROSS JOIN price_params params
        WHERE pnl.fiscal_year IN ('FY26', '2026') AND pnl.line_type = 'field'
    )
    SELECT
        field_name,
        actual_ebitda,
        ROUND(sim_gross_rev * (1.0 - eff_royalty_rate - eff_cess_rate) - total_opex_inr_cr, 2) AS formula_ebitda,
        ROUND(ABS(actual_ebitda - (sim_gross_rev * (1.0 - eff_royalty_rate - eff_cess_rate) - total_opex_inr_cr)), 2) AS diff,
        SAFE_DIVIDE(ABS(actual_ebitda - (sim_gross_rev * (1.0 - eff_royalty_rate - eff_cess_rate) - total_opex_inr_cr)), NULLIF(ABS(actual_ebitda), 0)) * 100.0 AS diff_pct
    FROM sim_actual
    """
    rows = list(bq_client.query(q_check, job_config=bigquery.QueryJobConfig(labels=JOB_LABELS, use_query_cache=False)).result())
    assert len(rows) == 53
    for r in rows:
        diff_pct = r.diff_pct or 0.0
        assert diff_pct <= 0.5, f"Field {r.field_name} diff {diff_pct:.3f}% exceeds 0.5% tolerance! Actual={r.actual_ebitda}, Formula={r.formula_ebitda}"


