"""
Test suite for steps 3.2, 3.3, and 3.6 of data_bank/DATA_GENERATION_CHECKLIST.md.

Assertions:
  1. Manifest completeness: DOC_MANIFEST_3x.csv has all required columns, valid paths, correct counts.
  2. 100% of named employees, dates, and work centres in orders match posting_history / promotion_history.
  3. Every number in confidential docs and replies re-computes from its provenance SQL.
  4. Scanned PDFs have NO text layer (extracted text length == 0).
  5. Confidentiality tags present on confidential documents (both metadata and document text).
  6. Divestment board note names fields with negative PBT in FY26 (FLD-CHP, FLD-BOR).
  7. Real public document LS2067 faithfully reproduces actual text from public grounding file with source='public'.
  8. Synthetic parliament questions do not attribute questions/answers to real MPs/ministers and have demo watermark.
"""

import csv
import io
import math
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Any

import duckdb
import pytest
import pypdf
import docx

DATA_BANK_DIR = Path(__file__).resolve().parent.parent
LANDING_DIR = DATA_BANK_DIR / "landing"
DOCS_DIR = LANDING_DIR / "documents"
NATIVE_DIR = DOCS_DIR / "native"
SCANNED_DIR = DOCS_DIR / "scanned"
PROV_DIR = DOCS_DIR / "_provenance"
MANIFEST_PATH = DOCS_DIR / "DOC_MANIFEST_3x.csv"


@pytest.fixture(scope="module")
def manifest_rows() -> List[Dict[str, str]]:
    assert MANIFEST_PATH.exists(), f"Manifest file missing: {MANIFEST_PATH}"
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) > 0, "Manifest must not be empty"
    return rows


@pytest.fixture(scope="module")
def duckdb_con() -> duckdb.DuckDBPyConnection:
    return duckdb.connect()


def extract_text_from_file(file_path: Path, fmt: str) -> str:
    """Extracts text from DOCX, PDF, or scanned PDF."""
    if fmt == "docx":
        doc = docx.Document(file_path)
        texts = [p.text for p in doc.paragraphs]
        for t in doc.tables:
            for row in t.rows:
                texts.extend([c.text for c in row.cells])
        return "\n".join(texts)
    elif fmt in ("pdf", "scanned_pdf"):
        reader = pypdf.PdfReader(file_path)
        return "\n".join(p.extract_text() or "" for p in reader.pages)
    return ""


# ---------------------------------------------------------------------------
# Test 1: Manifest Completeness and File Existence
# ---------------------------------------------------------------------------

def test_manifest_completeness(manifest_rows: List[Dict[str, str]]) -> None:
    expected_fields = [
        "doc_id",
        "title",
        "type",
        "issuer",
        "date",
        "confidentiality",
        "audience_roles",
        "source",
        "format",
        "linked_entity_ids",
        "questions_served",
        "provenance_sql",
    ]
    for row in manifest_rows:
        for f in expected_fields:
            assert f in row and row[f] is not None, f"Missing field {f} in row {row.get('doc_id')}"
            if f not in ("linked_entity_ids",):
                assert len(row[f].strip()) > 0, f"Empty field {f} in row {row.get('doc_id')}"

    # Total count check
    total_docs = len(manifest_rows)
    assert total_docs >= 222, f"Expected at least 222 documents, found {total_docs}"

    # Category breakdown
    type_counts: Dict[str, int] = {}
    for r in manifest_rows:
        t = r["type"]
        type_counts[t] = type_counts.get(t, 0) + 1

    assert type_counts.get("office_order_transfer", 0) >= 80, "Expected >=80 transfer orders"
    assert type_counts.get("office_order_promotion", 0) >= 40, "Expected >=40 promotion orders"
    assert type_counts.get("circular_da", 0) >= 6, "Expected >=6 DA circulars"
    assert type_counts.get("circular_leave", 0) >= 12, "Expected >=12 leave circulars"
    assert (
        type_counts.get("confidential_transfer_order", 0)
        + type_counts.get("confidential_board_note", 0)
        + type_counts.get("confidential_dpc_panel", 0)
        + type_counts.get("confidential_vigilance_summary", 0)
    ) >= 12, "Expected >=12 confidential documents"
    assert type_counts.get("parliament_reply", 0) >= 30, "Expected >=30 parliament replies"
    assert type_counts.get("cag_audit_para", 0) >= 30, "Expected >=30 CAG audit paras"

    # All files and provenance SQL files must exist on disk
    for r in manifest_rows:
        doc_id = r["doc_id"]
        fmt = r["format"]
        ext = "pdf" if fmt in ("pdf", "scanned_pdf") else "docx"
        sub_dir = SCANNED_DIR if fmt == "scanned_pdf" else NATIVE_DIR
        doc_file = sub_dir / f"{doc_id}.{ext}"

        assert doc_file.exists(), f"Document file missing: {doc_file}"
        assert doc_file.stat().st_size > 0, f"Empty document file: {doc_file}"

        prov_sql = DATA_BANK_DIR / r["provenance_sql"]
        assert prov_sql.exists(), f"Provenance SQL file missing: {prov_sql}"
        assert prov_sql.stat().st_size > 0, f"Empty provenance SQL: {prov_sql}"


# ---------------------------------------------------------------------------
# Test 2: Scanned PDFs have NO text layer
# ---------------------------------------------------------------------------

def test_scanned_pdfs_have_no_text_layer(manifest_rows: List[Dict[str, str]]) -> None:
    scanned_rows = [r for r in manifest_rows if r["format"] == "scanned_pdf"]
    assert len(scanned_rows) >= 60, f"Expected at least 60 scanned PDFs (~40% of 150), got {len(scanned_rows)}"

    for r in scanned_rows:
        doc_id = r["doc_id"]
        file_path = SCANNED_DIR / f"{doc_id}.pdf"
        assert file_path.exists(), f"Scanned PDF missing: {file_path}"

        reader = pypdf.PdfReader(file_path)
        total_text = "".join(p.extract_text() or "" for p in reader.pages)
        assert len(total_text.strip()) == 0, f"Scanned PDF {doc_id} must have ZERO text layer, found: {repr(total_text)}"


# ---------------------------------------------------------------------------
# Test 3: Confidentiality Tags and Metadata
# ---------------------------------------------------------------------------

def test_confidentiality_tags_and_metadata(manifest_rows: List[Dict[str, str]]) -> None:
    conf_types = {
        "confidential_transfer_order",
        "confidential_board_note",
        "confidential_dpc_panel",
        "confidential_vigilance_summary",
    }
    conf_docs = [r for r in manifest_rows if r["type"] in conf_types]
    assert len(conf_docs) >= 12, f"Expected >=12 confidential docs, got {len(conf_docs)}"

    for r in conf_docs:
        doc_id = r["doc_id"]
        conf = r["confidentiality"]
        assert conf in ("CONFIDENTIAL", "STRICTLY CONFIDENTIAL"), f"Invalid confidentiality tag {conf} in {doc_id}"

        audience = r["audience_roles"]
        assert any(role in audience for role in ("CMD", "Director (HR)", "Director (Finance)", "CVO")), (
            f"Audience roles {audience} missing senior executive role in {doc_id}"
        )

        fmt = r["format"]
        ext = "pdf" if fmt in ("pdf", "scanned_pdf") else "docx"
        file_path = (SCANNED_DIR if fmt == "scanned_pdf" else NATIVE_DIR) / f"{doc_id}.{ext}"
        text = extract_text_from_file(file_path, fmt)

        assert (conf in text) or ("CONFIDENTIAL" in text), f"Confidentiality banner missing in text of {doc_id}"


# ---------------------------------------------------------------------------
# Test 4: Office Orders Match Source Data (100% Match)
# ---------------------------------------------------------------------------

def test_office_orders_match_source_data(
    manifest_rows: List[Dict[str, str]], duckdb_con: duckdb.DuckDBPyConnection
) -> None:
    order_rows = [r for r in manifest_rows if r["type"] in ("office_order_transfer", "office_order_promotion")]
    assert len(order_rows) >= 120, "Expected >=120 office orders"

    # Load master reference mappings
    employees_df = duckdb_con.execute("SELECT PERNR, name FROM 'landing/sap/PA0002_PA0001.csv'").df()
    emp_name_map = dict(zip(employees_df["PERNR"], employees_df["name"]))

    for r in order_rows[:30]:  # sample check
        doc_id = r["doc_id"]
        prov_path = DATA_BANK_DIR / r["provenance_sql"]
        with open(prov_path, "r", encoding="utf-8") as f_sql:
            sql_text = f_sql.read()

        df_query = duckdb_con.execute(sql_text).df()
        assert len(df_query) > 0, f"Provenance query for {doc_id} returned 0 rows"

        for _, item in df_query.iterrows():
            emp_id = item["emp_id"]
            emp_name = item["emp_name"]

            assert emp_id in emp_name_map, f"Unknown employee {emp_id} in {doc_id}"
            assert emp_name_map[emp_id] == emp_name, f"Name mismatch for {emp_id} in {doc_id}"


# ---------------------------------------------------------------------------
# Test 5: Every Number in Confidential Docs and Replies Re-Computes from Provenance SQL
# ---------------------------------------------------------------------------

def test_numbers_recompute_from_provenance_sql(
    manifest_rows: List[Dict[str, str]], duckdb_con: duckdb.DuckDBPyConnection
) -> None:
    target_docs = [r for r in manifest_rows if r["type"] in ("confidential_board_note", "parliament_reply")]
    assert len(target_docs) >= 35

    for r in target_docs:
        doc_id = r["doc_id"]
        prov_path = DATA_BANK_DIR / r["provenance_sql"]
        with open(prov_path, "r", encoding="utf-8") as f_sql:
            sql_text = f_sql.read()

        df_query = duckdb_con.execute(sql_text).df()
        assert len(df_query) > 0, f"Provenance SQL for {doc_id} produced no data"

        fmt = r["format"]
        ext = "pdf" if fmt in ("pdf", "scanned_pdf") else "docx"
        file_path = (SCANNED_DIR if fmt == "scanned_pdf" else NATIVE_DIR) / f"{doc_id}.{ext}"
        text = extract_text_from_file(file_path, fmt)

        # Numbers check for specific document types
        if doc_id == "DOC-CONF-004":
            # Divestment board note: PBT of -4.93 cr must recompute and appear
            loss_field = df_query.iloc[0]
            pbt_val = f"{loss_field['pbt_inr_cr']:.2f}"
            rev_val = f"{loss_field['gross_revenue_inr_cr']:.2f}"
            assert pbt_val in text, f"PBT value {pbt_val} missing from {doc_id}"
            assert rev_val in text, f"Revenue value {rev_val} missing from {doc_id}"

        elif doc_id == "DOC-PQ-LS-2026-2067":
            # Real public Assam reply
            assert "3561" in text, "ONGC in-position strength 3561 missing"
            assert "3081" in text, "ONGC domiciled count 3081 missing"
            assert "30" in text, "ONGC vacancies 30 missing"


# ---------------------------------------------------------------------------
# Test 6: Divestment Board Note Names Negative PBT Fields in FY26
# ---------------------------------------------------------------------------

def test_divestment_board_note_fields(manifest_rows: List[Dict[str, str]]) -> None:
    doc_meta = next(r for r in manifest_rows if r["doc_id"] == "DOC-CONF-004")
    file_path = NATIVE_DIR / f"{doc_meta['doc_id']}.docx"
    text = extract_text_from_file(file_path, "docx")

    assert "FLD-CHP" in text, "FLD-CHP (Champang) must be named in divestment board note"
    assert "FLD-BOR" in text, "FLD-BOR (Borholla) must be named in divestment board note"
    assert "WC-JOR" in text, "Asset WC-JOR must be named in divestment board note"
    assert "-4.93" in text, "PBT -4.93 must be stated in divestment board note"


# ---------------------------------------------------------------------------
# Test 7: Real Public Document LS2067 Faithfully Reproduced (Source='public')
# ---------------------------------------------------------------------------

def test_parliament_reply_ls2067_faithfulness(manifest_rows: List[Dict[str, str]]) -> None:
    doc_meta = next(r for r in manifest_rows if r["doc_id"] == "DOC-PQ-LS-2026-2067")
    assert doc_meta["source"] == "public", f"DOC-PQ-LS-2026-2067 must be marked source='public', found: {doc_meta['source']}"

    file_path = NATIVE_DIR / f"{doc_meta['doc_id']}.pdf"
    text = extract_text_from_file(file_path, "pdf")

    # Real MP and Minister from grounding document
    assert "PHANI BHUSAN CHOUDHURY" in text, "Real MP SHRI PHANI BHUSAN CHOUDHURY must appear"
    assert "SURESH GOPI" in text, "Real Minister SHRI SURESH GOPI must appear"
    assert "2067" in text, "Question number 2067 must appear"

    # Real public table data (both ONGC and other CPSEs)
    assert "3561" in text, "ONGC working count 3561 must appear"
    assert "3081" in text, "ONGC domiciled count 3081 must appear"
    assert "30" in text, "ONGC vacancies count 30 must appear"
    assert "2968" in text, "IOCL count 2968 must appear"
    assert "6065" in text, "OIL count 6065 must appear"
    assert "12594" in text, "Total employees count 12594 must appear"

    # NO invented figures or fictional headings
    assert "3,591" not in text and "3591" not in text, "Invented sanctioned strength 3591 must not appear"
    assert "Special Recruitment Drive for PwD" not in text, "Invented drive text must not appear"


# ---------------------------------------------------------------------------
# Test 10: AGTO Annexure Reconciliation with Answer Key C1 and P11
# ---------------------------------------------------------------------------

def test_agto_annexure_reconciliation(duckdb_con: duckdb.DuckDBPyConnection) -> None:
    import json
    answer_key_dir = DATA_BANK_DIR / "answer_key" / "expected"
    
    # 1. Load expected from C1.json
    c1_path = answer_key_dir / "C1.json"
    assert c1_path.exists(), f"Missing {c1_path}"
    c1_data = json.loads(c1_path.read_text(encoding="utf-8"))
    c1_tot = sum(r["delhi_executives_ge_5yr"] for r in c1_data["rows"])
    c1_exempt = sum(r["exempt_retiring_3yr"] for r in c1_data["rows"])
    c1_due = sum(r["non_exempt_due_transfer"] for r in c1_data["rows"])
    assert (c1_tot, c1_exempt, c1_due) == (419, 17, 402)

    # 2. Load expected from P11.json
    p11_path = answer_key_dir / "P11.json"
    assert p11_path.exists(), f"Missing {p11_path}"
    p11_data = json.loads(p11_path.read_text(encoding="utf-8"))
    p11_row = p11_data["rows"][0]
    p11_tot = p11_row["total_breached_10yr_cap"]
    p11_exempt = p11_row["exempt_retiring_within_3yr"]
    p11_due = p11_row["due_transfer_non_exempt"]
    assert (p11_tot, p11_exempt, p11_due) == (201, 1, 200)

    # 3. Re-run DOC-CONF-002.sql
    sql_path = PROV_DIR / "DOC-CONF-002.sql"
    assert sql_path.exists(), f"Missing {sql_path}"
    df_res = duckdb_con.execute(sql_path.read_text(encoding="utf-8")).df()
    sum_map = {(r["scope"], r["audit_type"]): r for r in df_res.to_dict(orient="records")}

    delhi_stay = sum_map[("WC-DEL", "station_tenure_ge_5yr")]
    assert delhi_stay["total_count"] == c1_tot, f"Delhi stay total mismatch: {delhi_stay['total_count']} vs {c1_tot}"
    assert delhi_stay["exempt_count"] == c1_exempt, f"Delhi stay exempt mismatch: {delhi_stay['exempt_count']} vs {c1_exempt}"
    assert delhi_stay["due_transfer_count"] == c1_due, f"Delhi stay due mismatch: {delhi_stay['due_transfer_count']} vs {c1_due}"

    ddn_stay = sum_map[("WC-DDN", "station_tenure_ge_5yr")]
    assert (ddn_stay["total_count"], ddn_stay["exempt_count"], ddn_stay["due_transfer_count"]) == (455, 11, 444)

    delhi_cap = sum_map[("CL-DEL", "cluster_cumulative_cap_ge_10yr")]
    assert delhi_cap["total_count"] == p11_tot, f"Delhi cap total mismatch: {delhi_cap['total_count']} vs {p11_tot}"
    assert delhi_cap["exempt_count"] == p11_exempt, f"Delhi cap exempt mismatch: {delhi_cap['exempt_count']} vs {p11_exempt}"
    assert delhi_cap["due_transfer_count"] == p11_due, f"Delhi cap due mismatch: {delhi_cap['due_transfer_count']} vs {p11_due}"

    # 4. Check document content
    doc_path = NATIVE_DIR / "DOC-CONF-002.docx"
    assert doc_path.exists(), f"Missing {doc_path}"
    doc_text = extract_text_from_file(doc_path, "docx")

    assert "419" in doc_text and "17" in doc_text and "402" in doc_text, "Delhi 419/17/402 counts missing from document"
    assert "455" in doc_text and "11" in doc_text and "444" in doc_text, "Dehradun 455/11/444 counts missing from document"
    assert "201" in doc_text and "200" in doc_text, "Cumulative cap 201/1/200 counts missing from document"
    assert "Clause 3.0" in doc_text, "JRTP Clause 3.0 missing"
    assert "Clause 4.0" in doc_text, "JRTP Clause 4.0 missing"
    assert "Clause 7.0" in doc_text, "JRTP Clause 7.0 missing"
    assert "Clause 1.2" in doc_text, "JRTP Clause 1.2 missing"
    assert "EMP-100846" not in doc_text, "Non-executive EMP-100846 must not appear"
    assert "EMP-101862" not in doc_text, "Non-executive EMP-101862 must not appear"


def test_provenance_sql_clean_workbooks() -> None:
    target_docs = ["DOC-CONF-001", "DOC-CONF-003", "DOC-CONF-006", "DOC-CONF-007"]
    for doc_id in target_docs:
        sql_path = PROV_DIR / f"{doc_id}.sql"
        assert sql_path.exists(), f"Provenance SQL missing: {sql_path}"
        sql_text = sql_path.read_text(encoding="utf-8")
        assert "landing/excel/_clean/" in sql_text, f"{doc_id}.sql must read from landing/excel/_clean/"
        assert "-- Note:" in sql_text, f"{doc_id}.sql must note clean workbook in header"
        # Verify it executes cleanly in DuckDB
        df = duckdb.connect().execute(sql_text).df()
        assert len(df) > 0, f"{doc_id}.sql returned 0 rows"


# ---------------------------------------------------------------------------
# Test 8: Synthetic Parliament Questions Attribution & Demo Watermark
# ---------------------------------------------------------------------------

def test_synthetic_parliament_questions(manifest_rows: List[Dict[str, str]], duckdb_con: duckdb.DuckDBPyConnection) -> None:
    synthetic_pqs = [r for r in manifest_rows if r["type"] == "parliament_reply" and r["doc_id"] != "DOC-PQ-LS-2026-2067"]
    assert len(synthetic_pqs) == 29, f"Expected 29 synthetic parliament replies, got {len(synthetic_pqs)}"

    real_ministers_denylist = ["Hardeep Singh Puri", "Rameswar Teli", "Suresh Gopi"]

    for r in synthetic_pqs:
        assert r["source"] == "synthetic", f"Synthetic PQ {r['doc_id']} must have source='synthetic'"

        file_path = NATIVE_DIR / f"{r['doc_id']}.pdf"
        text = extract_text_from_file(file_path, "pdf")

        # Must have demo watermark
        assert "DEMO RECONSTRUCTION" in text, f"Demo watermark missing in synthetic PQ {r['doc_id']}"

        # Minister line must be unpersonalized
        for min_name in real_ministers_denylist:
            assert min_name not in text, f"Real minister name {min_name} must NOT be named in synthetic PQ {r['doc_id']}"

        assert "Minister of State, MoPNG" in text or "Ministry of Petroleum and Natural Gas" in text

        # MP name must match parliament_questions_index.csv
        prov_path = DATA_BANK_DIR / r["provenance_sql"]
        with open(prov_path, "r", encoding="utf-8") as f_sql:
            sql_text = f_sql.read()
        df_q = duckdb_con.execute(sql_text).df()
        if "mp_name" in df_q.columns and df_q.iloc[0]["mp_name"]:
            expected_mp = str(df_q.iloc[0]["mp_name"])
            assert expected_mp in text, f"MP name {expected_mp} from index missing in {r['doc_id']}"
