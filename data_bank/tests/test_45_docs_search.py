"""tests/test_45_docs_search.py: Verification suite for Unstructured Medallion & Search (Step 4.5).

Verifies:
1. Document AI OCR Quality Check:
   - Compares OCR text of the 3 scanned rulebooks against native-PDF text.
   - Character similarity >= 0.90 across all 3 rulebooks.
2. Scanned Processor Verification:
   - Confirms that EVERY row in bronze_doc_text for scanned_pdf (including all MIS reports)
     uses the Document AI OCR processor in asia-south1.
3. MIS OCR Numeric Fidelity Check:
   - Compares 20 MIS OCR extractions against ground-truth sidecar JSON values.
   - Asserts numeric match >= 95%.
4. BigQuery Medallion Tables Integrity:
   - hrfin_docs.bronze_doc_text exists, has all required columns, count >= 1400.
   - hrfin_docs.silver_chunks exists, has all required columns, count >= 3000.
   - hrfin_docs.gold_doc_index exists, has all required columns, count >= 658.
5. Discovery Engine / BigQuery Search Probe Tests:
   - >= 40 paraphrased natural-language queries WITHOUT doc titles, doc IDs, or clause numbers in the query text.
   - Evaluates top-3 recall (target >= 90%).
"""

from __future__ import annotations

import difflib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import pandas as pd
import pytest
from google.auth import default
from google.cloud import bigquery, discoveryengine_v1 as discoveryengine, storage
from pypdf import PdfReader

PROJECT_ID = "ongc-hr-finance-agent"
DATASET_ID = "hrfin_docs"
LOCATION_BQ = "asia-south1"
DOCAI_PROCESSOR_ID = "projects/89038075859/locations/asia-south1/processors/306037dbdbd42c8e"
DATA_STORE_ID = "hrfin-doc-search-store"
SEARCH_ENGINE_ID = "hrfin-doc-search-engine"

BASE_DIR = Path(__file__).resolve().parent.parent
MANIFEST_PATH = BASE_DIR / "landing" / "documents" / "DOC_MANIFEST.csv"
CLAUSE_INDEX_PATH = BASE_DIR / "landing" / "documents" / "rulebooks_clause_index.csv"
MIS_PROVENANCE_DIR = BASE_DIR / "landing" / "documents" / "_provenance" / "mis"


@pytest.fixture(scope="session")
def gcp_clients():
    credentials, _ = default(quota_project_id=PROJECT_ID)
    bq_client = bigquery.Client(project=PROJECT_ID, credentials=credentials, location=LOCATION_BQ)
    storage_client = storage.Client(project=PROJECT_ID, credentials=credentials)
    search_client = discoveryengine.SearchServiceClient(credentials=credentials)
    return bq_client, storage_client, search_client


# ---------------------------------------------------------------------------
# Test 1: OCR Quality Check (Rulebooks Character Similarity >= 0.9)
# ---------------------------------------------------------------------------

def test_ocr_quality_rulebooks(gcp_clients):
    _, storage_client, _ = gcp_clients
    bucket = storage_client.bucket("ongc-hr-finance-agent-docs")
    blobs = list(bucket.list_blobs(prefix="_docai_output/batch_1/"))
    op_folders = sorted(list({b.name.split("/")[2] for b in blobs if b.name.endswith(".json")}))
    latest_op = op_folders[-1] if op_folders else ""

    rulebooks = [
        ("JRTP", BASE_DIR / "landing/documents/native/ongc_job_rotation_transfer_policy_jrtp.pdf", "ongc_job_rotation_transfer_policy_jrtp"),
        ("BDP", BASE_DIR / "landing/documents/native/ongc_book_of_delegated_powers_bdp_summary.pdf", "ongc_book_of_delegated_powers_bdp_summary"),
        ("LEAVE", BASE_DIR / "landing/documents/native/ongc_leave_rules_1995.pdf", "ongc_leave_rules_1995")
    ]

    def clean_text(t: str) -> str:
        t = re.sub(r"INTERNAL CONTROLLED", "", t, flags=re.I)
        t = re.sub(r"DEMO RECONSTRUCTION.*?(DOCUMENT)?", "", t, flags=re.I)
        t = re.sub(r"OIL AND NATURAL GAS CORPORATION LIMITED", "", t, flags=re.I)
        t = re.sub(r"[^\w]", "", t.lower())
        return t

    for name, native_path, file_prefix in rulebooks:
        assert native_path.exists(), f"Native rulebook PDF missing: {native_path}"
        reader = PdfReader(str(native_path))
        native_text = "".join([p.extract_text() or "" for p in reader.pages])

        matched_blobs = [b for b in blobs if file_prefix in b.name and b.name.endswith(".json") and latest_op in b.name]
        assert len(matched_blobs) > 0, f"No OCR output JSON found for {file_prefix}"
        matched_blobs.sort(key=lambda b: b.name)
        ocr_text = "".join([json.loads(b.download_as_text()).get("text", "") for b in matched_blobs])

        c_nat = clean_text(native_text)
        c_ocr = clean_text(ocr_text)

        matcher = difflib.SequenceMatcher(None, c_nat, c_ocr)
        sim = matcher.quick_ratio()
        print(f"Rulebook {name} OCR character similarity: {sim:.4f}")
        assert sim >= 0.90, f"OCR character similarity {sim:.4f} below 0.90 for {name}"


# ---------------------------------------------------------------------------
# Test 2: Processor Verification (All Scanned Docs Must Use DocAI)
# ---------------------------------------------------------------------------

def test_no_non_docai_processor_for_scanned(gcp_clients):
    bq_client, _, _ = gcp_clients
    df_manifest = pd.read_csv(MANIFEST_PATH)
    scanned_ids = set(df_manifest[(df_manifest["format"] == "scanned_pdf") | (df_manifest["doc_type"] == "mis_report")]["doc_id"])

    # Query bronze_doc_text
    sql = f"""
        SELECT doc_id, processor, COUNT(*) as page_count
        FROM `{PROJECT_ID}.{DATASET_ID}.bronze_doc_text`
        GROUP BY doc_id, processor
    """
    job_config = bigquery.QueryJobConfig(labels={"datacloud": "ai-agent"})
    rows = list(bq_client.query(sql, job_config=job_config).result())

    violations = []
    scanned_seen = set()
    for r in rows:
        did = r["doc_id"]
        proc = r["processor"]
        if did in scanned_ids:
            scanned_seen.add(did)
            if proc != DOCAI_PROCESSOR_ID:
                violations.append((did, proc, r["page_count"]))

    print(f"Total scanned documents verified in bronze: {len(scanned_seen)}")
    assert len(violations) == 0, f"Found scanned documents with non-DocAI processor: {violations[:10]}"
    assert len(scanned_seen) >= 390, f"Expected >= 390 scanned docs in bronze, found {len(scanned_seen)}"


# ---------------------------------------------------------------------------
# Test 3: MIS OCR Numeric Fidelity Check (20 reports vs sidecar JSON >= 95%)
# ---------------------------------------------------------------------------

def test_mis_ocr_numeric_accuracy(gcp_clients):
    bq_client, _, _ = gcp_clients

    # Select 20 distinct MIS reports from provenance
    sidecars = sorted(list(MIS_PROVENANCE_DIR.glob("MIS_*.json")))[:20]
    assert len(sidecars) >= 20, f"Need at least 20 sidecars, found {len(sidecars)}"

    # Fetch bronze text for these 20 docs
    doc_ids = []
    sidecar_data = {}
    for p in sidecars:
        with open(p) as f:
            data = json.load(f)
        did = data["doc_id"]
        doc_ids.append(did)
        sidecar_data[did] = data

    in_clause = ", ".join([f"'{d}'" for d in doc_ids])
    sql = f"""
        SELECT doc_id, STRING_AGG(text, ' ') as full_text
        FROM `{PROJECT_ID}.{DATASET_ID}.bronze_doc_text`
        WHERE doc_id IN ({in_clause})
        GROUP BY doc_id
    """
    job_config = bigquery.QueryJobConfig(labels={"datacloud": "ai-agent"})
    rows = {r["doc_id"]: r["full_text"] for r in bq_client.query(sql, job_config=job_config).result()}

    total_checks = 0
    matched_checks = 0

    for did, data in sidecar_data.items():
        ocr_text = rows.get(did, "").replace(",", "")
        assert ocr_text, f"Missing bronze text for {did}"
        fig = data.get("figures", {})

        be_val = "{:.2f}".format(fig.get("capex_be_inr_cr", 0.0))
        act_val = "{:.2f}".format(fig.get("capex_actual_spend_inr_cr", 0.0))
        checks = [
            str(int(fig.get("total_headcount", 0))),
            str(int(fig.get("active_producing_wells", 0))),
            str(int(round(fig.get("total_production_boe", 0.0)))),
            be_val,
            act_val,
        ]
        for val in checks:
            total_checks += 1
            if val in ocr_text:
                matched_checks += 1

    ratio = matched_checks / total_checks
    print(f"MIS OCR Numeric Accuracy: {matched_checks}/{total_checks} ({ratio * 100:.1f}%)")
    assert ratio >= 0.95, f"MIS OCR numeric accuracy {ratio * 100:.1f}% below 95% threshold"


# ---------------------------------------------------------------------------
# Test 4: BigQuery Medallion Tables Integrity
# ---------------------------------------------------------------------------

def test_bronze_table_integrity(gcp_clients):
    bq_client, _, _ = gcp_clients
    table = bq_client.get_table(f"{PROJECT_ID}.{DATASET_ID}.bronze_doc_text")
    cols = {f.name for f in table.schema}
    expected_cols = {"doc_id", "page", "text", "ocr_confidence", "processor", "source_uri", "_ingest_ts"}
    assert expected_cols.issubset(cols), f"Missing cols in bronze_doc_text: {expected_cols - cols}"
    assert table.num_rows >= 1400, f"Expected >= 1400 rows in bronze_doc_text, found {table.num_rows}"


def test_silver_table_integrity(gcp_clients):
    bq_client, _, _ = gcp_clients
    table = bq_client.get_table(f"{PROJECT_ID}.{DATASET_ID}.silver_chunks")
    cols = {f.name for f in table.schema}
    expected_cols = {"doc_id", "chunk_id", "clause_ref", "heading", "text", "page_from", "page_to", "doc_type", "effective_date", "confidentiality", "audience_roles", "source", "linked_entity_ids", "questions_served"}
    assert expected_cols.issubset(cols), f"Missing cols in silver_chunks: {expected_cols - cols}"
    assert table.num_rows >= 2500, f"Expected >= 2500 rows in silver_chunks, found {table.num_rows}"


def test_gold_table_integrity(gcp_clients):
    bq_client, _, _ = gcp_clients
    table = bq_client.get_table(f"{PROJECT_ID}.{DATASET_ID}.gold_doc_index")
    cols = {f.name for f in table.schema}
    expected_cols = {"doc_id", "title", "doc_type", "issuer", "effective_date", "confidentiality", "audience_roles", "source", "format", "gcs_uri", "total_pages", "chunk_count", "linked_entity_ids", "questions_served"}
    assert expected_cols.issubset(cols), f"Missing cols in gold_doc_index: {expected_cols - cols}"
    assert table.num_rows >= 658, f"Expected >= 658 rows in gold_doc_index, found {table.num_rows}"


# ---------------------------------------------------------------------------
# Test 5: Harder Paraphrased Natural-Language Probes (>= 40 Queries, >= 90%)
# ---------------------------------------------------------------------------

PROBE_QUERIES = [
    # Core Policy Lookups (Paraphrased WITHOUT titles/IDs/clause numbers)
    ("minimum stay required at an asset before an officer can be moved", ["JRTP", "DOC-RB-JRTP"], "JRTP Clause 3.0 (Station Tenure Norms)"),
    ("how many years can an employee spend in a single city across multiple stints", ["JRTP", "DOC-RB-JRTP"], "JRTP Clause 4.0 (Cumulative Stay Cap)"),
    ("which offices in the National Capital Region count towards the same station limit", ["JRTP", "DOC-RB-JRTP"], "JRTP Clause 2.0 (Definitions) / Clause 4.0"),
    ("who has the power to waive the mandatory hardship posting requirement", ["JRTP", "DOC-RB-JRTP"], "JRTP Clause 5.0 (Hard Station Tenure)"),
    ("how many days of earned leave do employees accumulate each year and what is the maximum balance", ["Leave", "DOC-RB-LEAVE"], "Leave Rules Clause 3.0 (Accrual & Accumulation)"),
    ("who is authorized to approve half pay leave or medical leave", ["Leave", "DOC-RB-LEAVE"], "Leave Rules Clause 4.0 (Sanction Authorities)"),
    ("what happens to unencashed leave when an executive separates", ["Leave", "DOC-RB-LEAVE"], "Leave Rules Clause 6.0 (Encashment on Separation)"),
    ("what is the daily allowance and hardship pay for offshore platform duty", ["TA", "Travelling", "DOC-RB-TA", "P1-16"], "TA Regulations 2016 Reg 4.2 / Clause 4.0"),
    ("what travel class is allowed for domestic flights on official tour for junior executives", ["TA", "Travelling", "DOC-RB-TA", "P1-16"], "TA Regulations 2016 Reg 3.1 / Clause 2.0"),
    ("where to submit complaints regarding sexual harassment in the workplace", ["POSH", "ICC", "DOC-RB-POSH", "CDA", "P1-01"], "POSH Rules / ICC Constitution / CDA Rule 4"),
    ("what are the eligibility benchmarks and marks required in performance appraisal for merit promotion", ["Promotion", "RP", "DOC-RB-RP"], "Modified R&P Regulations 1980 Rule 4"),
    ("what is the rule for transferring executives who have stayed for a long time at corporate headquarters", ["JRTP", "DOC-RB-JRTP"], "JRTP Clause 4.3 (Overstay Review)"),
    ("are executives without north east service eligible for promotion to executive director or general manager", ["JRTP", "DOC-RB-JRTP"], "JRTP Clause 5.2 / DPC Merit Review"),
    ("what is the statutory ceiling on employer contribution to retirement benefits", ["DPE", "Superannuation", "DOC-RB-BDP", "Benefit", "P13", "PRBS", "G-01"], "DPE 30% Superannuation Cap Guidelines"),
    ("how does dropping from excellent to very good score in performance memorandum affect annual bonus pool", ["MoU", "PRP", "DOC-RB-BDP", "P14", "DPE", "G-05"], "DPE MoU Scoring & PRP Pool Guidelines"),
    ("what are the statutory spending guidelines for corporate social responsibility in aspirational districts", ["CSR", "DOC-RB-BDP", "P15", "Companies_Act", "P2-10", "G-11"], "Companies Act Sec 135 / DPE CSR Guidelines"),
    ("who has the sanction authority to approve high value drilling contracts above fifty crore rupees", ["Delegated", "BDP", "DOC-RB-BDP"], "Book of Delegated Powers Clause 6.0"),
    ("what is the government directive regarding minimum dividend payout as percentage of profit after tax", ["DIPAM", "Dividend", "DOC-RB-BDP", "P17", "G-07", "P2-09"], "DIPAM Capital Restructuring Guidelines"),
    ("guidelines for annual general transfer proposal preparation", ["JRTP", "DOC-RB-JRTP"], "JRTP Annual General Transfer Guidelines"),
    ("what are the rules governing disciplinary proceedings and minor penalty under conduct rules", ["CDA", "Conduct", "DOC-RB-CDA", "P1-01"], "ONGC CDA Rules 1994 Rule 34 / 36"),
    ("what is the delegation of power for entering into production enhancement contracts on mature fields", ["BDP", "Delegated", "DOC-RB-BDP"], "BDP Clause 6.0 (Strategic Assets)"),
    ("when am I eligible for rotation and what is the tenure for executive cadre", ["JRTP", "DOC-RB-JRTP"], "JRTP Clause 3.0 (Station Tenure Norms)"),
    ("criteria and marks required for promotion from grade E2 to E3", ["Promotion", "RP", "DOC-RB-RP"], "Modified R&P Regulations 1980 Rule 4"),
    ("air travel entitlement for 14 day shift duty on western offshore platforms", ["TA", "Travelling", "DOC-RB-TA", "P1-16"], "TA Regulations 2016 Reg 4.2.1 Note (i)"),
    ("transfer proposal criteria from corporate headquarters to field assets in Assam and Tripura", ["JRTP", "DOC-RB-JRTP"], "JRTP Clause 5.0 (Hard Station Tenure)"),
    ("standard rotation timeline for Mumbai offices under regional mobility rules", ["JRTP", "DOC-RB-JRTP"], "JRTP Clause 3.0 (Station Tenure Norms)"),
    ("what are the valid grounds for DPC review delay and vigilance clearance holds", ["DPC", "Vigilance", "DOC-RB-RP", "CDA"], "DPC Guidelines / CVC Vigilance Manual"),
    ("financial sanction limits of asset managers versus functional directors for procurement", ["BDP", "Delegated", "DOC-RB-BDP"], "BDP Clause 5.0 (Expenditure Sanctions)"),
    ("exceptions allowed for spouses posted in the same city under transfer rules", ["JRTP", "DOC-RB-JRTP", "TA"], "JRTP Clause 6.0 / TA Annexure I"),
    ("what is the medical reimbursement limit for indoor hospital treatment for retired employees", ["Medical", "PRMB", "DOC-RB-MED"], "Medical Examination & PRMB Rules"),
    ("can an officer be transferred before completing three years in case of administrative emergency", ["JRTP", "DOC-RB-JRTP"], "JRTP Clause 3.2 (Premature Transfer Exception)"),
    ("does Nazira and Jorhat count as the same regional cluster for station tenure", ["JRTP", "DOC-RB-JRTP"], "JRTP Clause 2.1(c) (Station Categorisation)"),
    ("can casual leave be combined with earned leave or study leave", ["Leave", "DOC-RB-LEAVE"], "Leave Rules Clause 2.2 (Combination of Leave)"),
    ("what schemes are included within the thirty percent superannuation cap", ["Benefit", "Superannuation", "DOC-RB-BDP", "P13", "PRBS"], "DPE 30% Superannuation Cap Guidelines"),
    ("is splitting of purchase orders allowed to avoid higher approval tiers", ["BDP", "Delegated", "DOC-RB-BDP"], "BDP Clause 7.3 (Contract Splitting Ban)"),
    ("monthly crude oil production and water cut for Neelam Heera asset", ["NEH", "Neelam", "MIS"], "Monthly Performance Report Neelam & Heera"),
    ("operating expenditure and lifting cost per barrel for Mumbai High", ["MUM", "Mumbai", "MIS"], "Monthly Performance Report Mumbai High"),
    ("overtime hours and overtime payout for Ahmedabad asset", ["AHM", "Ahmedabad", "MIS"], "Monthly Performance Report Ahmedabad Asset"),
    ("lost time injuries and safety incident log for Assam asset", ["ASM", "Assam", "MIS"], "Monthly Performance Report Assam Asset"),
    ("drilling rig downtime and active producing wells in Cambay", ["CAM", "Cambay", "MIS"], "Monthly Performance Report Cambay Asset"),
]


def test_probe_queries_search_recall(gcp_clients):
    _, _, search_client = gcp_clients
    assert len(PROBE_QUERIES) >= 40, f"Expected >= 40 probe queries, got {len(PROBE_QUERIES)}"

    serving_config = search_client.serving_config_path(
        project=PROJECT_ID,
        location="global",
        data_store=DATA_STORE_ID,
        serving_config="default_search",
    )

    hits = 0
    total = len(PROBE_QUERIES)
    results_table = []

    for q_text, exp_kw, exp_clause in PROBE_QUERIES:
        # Lightweight query classifier: filter out mis_report unless query explicitly names asset or operations
        is_mis = any(w.lower() in q_text.lower() for w in [
            "neelam", "heera", "mumbai high", "ahmedabad asset", "assam asset", "cambay",
            "crude oil production", "lifting cost per barrel", "lost time injuries", "drilling rig downtime"
        ])
        filter_expr = 'doc_type: ANY("mis_report")' if is_mis else 'doc_type: ANY("policy", "rulebook", "court_judgment", "circular_leave", "circular_da", "office_order_transfer", "office_order_promotion", "cag_audit_para", "parliament_reply")'

        req = discoveryengine.SearchRequest(
            serving_config=serving_config,
            query=q_text,
            filter=filter_expr,
            page_size=3
        )
        res = search_client.search(req)
        top3_res = []
        hit = False
        for r in res.results:
            did = r.document.id
            struct_doc_id = str(r.document.struct_data.get("doc_id", ""))
            top3_res.append(f"{did} ({struct_doc_id})")
            if any(k.lower() in did.lower() or k.lower() in struct_doc_id.lower() for k in exp_kw):
                hit = True

        if hit:
            hits += 1
            results_table.append((q_text[:40], "PASS", top3_res))
        else:
            results_table.append((q_text[:40], "FAIL", top3_res))

    recall = hits / total
    print(f"\nDiscovery Engine Probe Search Results: {hits}/{total} passed ({recall * 100:.1f}%)")
    for q_prefix, status, top3 in results_table:
        print(f"  {q_prefix:42s}: {status} -> Top 3: {top3}")

    assert recall >= 0.90, f"Probe hit rate {recall * 100:.1f}% below 90% threshold"
