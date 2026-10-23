"""Automated verification test suite for Step 3.1: Demo reconstructions of ONGC internal rulebooks.

Asserts:
1. All 7 native DOCX rulebooks exist and are non-empty.
2. All 7 native PDF rulebooks exist, have page counts between 8 and 40 pages, and carry watermarks on every page.
3. Scanned PDFs for JRTP, BDP, and Leave Rules exist and have ZERO text layer (pure image raster).
4. rulebooks_clause_index.csv contains every required clause from policy_question_map.yaml reconstruction_requirements.
5. Every policy question mapped 'needs_reconstruction' resolves to at least one clause in rulebooks_clause_index.csv.
6. Numeric rules in rulebooks match world_bible reference definitions (clusters, hard stations, pay scales, BDP limits).
7. Rules are consistent with empirical data patterns computed from PA0001.csv (median executive stint ~3 years, moves within 3 years of retirement ~0).
"""

import csv
import re
from pathlib import Path
import pytest
import pypdf
import yaml
import docx
import pandas as pd

DATA_BANK_ROOT = Path(__file__).resolve().parent.parent
NATIVE_DIR = DATA_BANK_ROOT / "landing" / "documents" / "native"
SCANNED_DIR = DATA_BANK_ROOT / "landing" / "documents" / "scanned"
CLAUSE_INDEX_PATH = DATA_BANK_ROOT / "landing" / "documents" / "rulebooks_clause_index.csv"
POLICY_MAP_PATH = DATA_BANK_ROOT / "world_bible" / "policy_question_map.yaml"
WORK_CENTRES_PATH = DATA_BANK_ROOT / "world_bible" / "reference" / "work_centres.yaml"
GRADES_PATH = DATA_BANK_ROOT / "world_bible" / "reference" / "grades.yaml"
PA0001_PATH = DATA_BANK_ROOT / "landing" / "sap" / "PA0001.csv"
PA0002_PATH = DATA_BANK_ROOT / "landing" / "sap" / "PA0002_PA0001.csv"

RULEBOOKS_META = {
    "JRTP": "ongc_job_rotation_transfer_policy_jrtp",
    "BDP summary": "ongc_book_of_delegated_powers_bdp_summary",
    "Leave Rules": "ongc_leave_rules_1995",
    "R&P/Promotion": "ongc_modified_recruitment_and_promotion_regulations",
    "HR Manual": "ongc_hr_manual_designations_pay_scales_service_conditions",
    "PRBS": "ongc_prbs_superannuation_benefit_scheme_rules",
    "Post-retirement medical": "ongc_post_retirement_medical_benefit_scheme",
}

SCANNED_DOCS = ["JRTP", "BDP summary", "Leave Rules"]


@pytest.fixture(scope="module")
def policy_map_data():
    assert POLICY_MAP_PATH.exists(), f"Missing policy map: {POLICY_MAP_PATH}"
    with open(POLICY_MAP_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def clause_index_rows():
    assert CLAUSE_INDEX_PATH.exists(), f"Missing clause index: {CLAUSE_INDEX_PATH}"
    rows = []
    with open(CLAUSE_INDEX_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


# ---------------------------------------------------------------------------
# TEST 1: File Existence & Non-Emptiness
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("doc_id, base_name", RULEBOOKS_META.items())
def test_native_files_exist_and_non_empty(doc_id: str, base_name: str):
    docx_file = NATIVE_DIR / f"{base_name}.docx"
    pdf_file = NATIVE_DIR / f"{base_name}.pdf"

    assert docx_file.exists(), f"Missing native DOCX for {doc_id}: {docx_file}"
    assert docx_file.stat().st_size > 10000, f"DOCX too small for {doc_id}: {docx_file.stat().st_size} bytes"

    assert pdf_file.exists(), f"Missing native PDF for {doc_id}: {pdf_file}"
    assert pdf_file.stat().st_size > 10000, f"PDF too small for {doc_id}: {pdf_file.stat().st_size} bytes"


@pytest.mark.parametrize("doc_id", SCANNED_DOCS)
def test_scanned_files_exist_and_non_empty(doc_id: str):
    base_name = RULEBOOKS_META[doc_id]
    scanned_file = SCANNED_DIR / f"{base_name}.pdf"

    assert scanned_file.exists(), f"Missing scanned PDF for {doc_id}: {scanned_file}"
    assert scanned_file.stat().st_size > 500000, f"Scanned PDF surprisingly small: {scanned_file.stat().st_size} bytes"


def test_clause_index_file_exists_and_schema(clause_index_rows):
    assert len(clause_index_rows) >= 50, f"Expected at least 50 clauses in index, found {len(clause_index_rows)}"
    expected_cols = {"doc_id", "clause_ref", "clause_title", "clause_text", "maps_to_question_ids", "source_basis",
                     "provenance"}  # v3 P0.7 (D-35, BUG-31): real | illustrative
    assert set(clause_index_rows[0].keys()) == expected_cols
    assert all(r["provenance"] in ("real", "illustrative") for r in clause_index_rows)


# ---------------------------------------------------------------------------
# TEST 2: Page Counts within 8 to 40 pages
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("doc_id, base_name", RULEBOOKS_META.items())
def test_native_pdf_page_counts(doc_id: str, base_name: str):
    pdf_file = NATIVE_DIR / f"{base_name}.pdf"
    reader = pypdf.PdfReader(str(pdf_file))
    num_pages = len(reader.pages)
    assert 8 <= num_pages <= 40, f"Rulebook {doc_id} has {num_pages} pages; must be between 8 and 40 pages"


@pytest.mark.parametrize("doc_id", SCANNED_DOCS)
def test_scanned_pdf_page_count_matches_native(doc_id: str):
    base_name = RULEBOOKS_META[doc_id]
    native_file = NATIVE_DIR / f"{base_name}.pdf"
    scanned_file = SCANNED_DIR / f"{base_name}.pdf"

    native_reader = pypdf.PdfReader(str(native_file))
    scanned_reader = pypdf.PdfReader(str(scanned_file))

    assert len(scanned_reader.pages) == len(native_reader.pages), (
        f"Scanned page count ({len(scanned_reader.pages)}) does not match native ({len(native_reader.pages)}) for {doc_id}"
    )


# ---------------------------------------------------------------------------
# TEST 3: Watermark Present on Every Page
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("doc_id, base_name", RULEBOOKS_META.items())
def test_watermark_present_on_every_page_of_native_pdf(doc_id: str, base_name: str):
    pdf_file = NATIVE_DIR / f"{base_name}.pdf"
    reader = pypdf.PdfReader(str(pdf_file))

    for idx, page in enumerate(reader.pages):
        text = page.extract_text()
        assert "DEMO RECONSTRUCTION" in text, (
            f"Missing watermark 'DEMO RECONSTRUCTION' on page {idx + 1} of {doc_id}"
        )
        assert "not an official ongc document" in text.lower(), (
            f"Missing 'not an official ongc document' on page {idx + 1} of {doc_id}"
        )


@pytest.mark.parametrize("doc_id, base_name", RULEBOOKS_META.items())
def test_watermark_present_in_docx(doc_id: str, base_name: str):
    docx_file = NATIVE_DIR / f"{base_name}.docx"
    doc = docx.Document(str(docx_file))

    # Check footer text
    footer_text = ""
    for sec in doc.sections:
        for p in sec.footer.paragraphs:
            footer_text += p.text + " "

    assert "DEMO RECONSTRUCTION" in footer_text, f"Missing DEMO RECONSTRUCTION in DOCX footer of {doc_id}"


# ---------------------------------------------------------------------------
# TEST 4: Scanned PDFs Have Zero Text Layer
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("doc_id", SCANNED_DOCS)
def test_scanned_pdfs_have_no_text_layer(doc_id: str):
    base_name = RULEBOOKS_META[doc_id]
    scanned_file = SCANNED_DIR / f"{base_name}.pdf"

    reader = pypdf.PdfReader(str(scanned_file))
    total_extracted_text = "".join(p.extract_text() for p in reader.pages)

    assert total_extracted_text.strip() == "", (
        f"Scanned PDF for {doc_id} has unexpected text layer: {repr(total_extracted_text[:100])}"
    )


# ---------------------------------------------------------------------------
# TEST 5: Every reconstruction_requirements Clause Present
# ---------------------------------------------------------------------------

def test_all_reconstruction_requirements_clauses_present(policy_map_data, clause_index_rows):
    recon_reqs = policy_map_data.get("reconstruction_requirements", {})

    # Group index clauses by doc_id
    index_by_doc = {}
    for r in clause_index_rows:
        index_by_doc.setdefault(r["doc_id"], []).append(r)

    errors = []
    for rb_name, rb_spec in recon_reqs.items():
        assert rb_name in index_by_doc, f"Rulebook '{rb_name}' missing entirely from clause index!"
        indexed_clauses = index_by_doc[rb_name]

        for req_clause in rb_spec.get("required_clauses", []):
            c_num = req_clause["clause_number"]
            c_title = req_clause["title"]

            # Match by clause number/ref (e.g. '1.0' in 'Clause 1.0') and partial title match
            found = False
            for ic in indexed_clauses:
                ref_num = ic["clause_ref"].replace("Clause", "").strip()
                if ref_num == c_num or c_num in ic["clause_ref"]:
                    # Check title similarity
                    norm_ic_title = re.sub(r"[^\w\s]", "", ic["clause_title"].lower())
                    norm_req_title = re.sub(r"[^\w\s]", "", c_title.lower())
                    # Check token overlap
                    ic_words = set(norm_ic_title.split())
                    req_words = set(norm_req_title.split())
                    overlap = ic_words.intersection(req_words)
                    if len(overlap) >= 1 or norm_req_title in norm_ic_title or norm_ic_title in norm_req_title:
                        found = True
                        break

            if not found:
                errors.append(f"Missing required clause in '{rb_name}': Clause {c_num} - '{c_title}'")

    assert not errors, f"Failed to match required clauses:\n" + "\n".join(errors)


# ---------------------------------------------------------------------------
# TEST 6: Every 'needs_reconstruction' Question Resolves to a Clause
# ---------------------------------------------------------------------------

def test_every_needs_reconstruction_question_resolves(policy_map_data, clause_index_rows):
    qmap = policy_map_data.get("question_map", [])
    needs_recon_items = [e for e in qmap if e.get("status") == "needs_reconstruction"]

    # Build set of all question IDs mapped in clause index
    mapped_qids_in_index = set()
    for r in clause_index_rows:
        raw_qids = r.get("maps_to_question_ids", "")
        for q in re.split(r"[;, ]+", raw_qids):
            q_clean = q.strip()
            if q_clean:
                mapped_qids_in_index.add(q_clean)

    missing_resolutions = []
    for item in needs_recon_items:
        qid = item["id"]
        if qid not in mapped_qids_in_index:
            missing_resolutions.append(f"Question '{qid}' ({item.get('question_text', '')[:40]})")

    assert not missing_resolutions, (
        f"The following {len(missing_resolutions)} 'needs_reconstruction' questions are not resolved in the clause index:\n"
        + "\n".join(missing_resolutions)
    )


# ---------------------------------------------------------------------------
# TEST 7: Numeric Rules Consistent with world_bible
# ---------------------------------------------------------------------------

def test_numeric_rules_consistent_with_world_bible(clause_index_rows):
    with open(WORK_CENTRES_PATH, "r", encoding="utf-8") as f:
        wc_data = yaml.safe_load(f)

    # 1. Geographic clusters in JRTP
    jrtp_text = " ".join(r["clause_text"] for r in clause_index_rows if r["doc_id"] == "JRTP")
    assert "CL-DEL" in jrtp_text or "Delhi National Capital Region" in jrtp_text
    assert "CL-MUM" in jrtp_text or "Mumbai–Panvel–Uran" in jrtp_text
    assert "CL-NE-ASSAM" in jrtp_text or "Nazira–Jorhat–Silchar" in jrtp_text
    assert "10" in jrtp_text and ("cumulative" in jrtp_text.lower() or "cap" in jrtp_text.lower())
    assert "3" in jrtp_text and "minimum" in jrtp_text.lower()

    # 2. Hard Station Category C in JRTP / R&P
    rp_text = " ".join(r["clause_text"] for r in clause_index_rows if r["doc_id"] == "R&P/Promotion")
    assert "Category 'C'" in jrtp_text or "Category C" in jrtp_text
    assert "Category 'C'" in rp_text or "Category C" in rp_text

    # 3. Pay scales in HR Manual
    with open(GRADES_PATH, "r", encoding="utf-8") as f:
        grades_data = yaml.safe_load(f)
    hrm_text = " ".join(r["clause_text"] for r in clause_index_rows if r["doc_id"] == "HR Manual")
    assert "30,000" in hrm_text and "1,20,000" in hrm_text  # E0 scale
    assert "60,000" in hrm_text and "1,80,000" in hrm_text  # E1 scale
    assert "1,50,000" in hrm_text and "3,00,000" in hrm_text  # E9 scale

    # 4. BDP limits
    bdp_text = " ".join(r["clause_text"] for r in clause_index_rows if r["doc_id"] == "BDP summary")
    assert "10 Crore" in bdp_text or "₹10 Crore" in bdp_text  # Asset manager limit
    assert "50 Crore" in bdp_text or "₹50 Crore" in bdp_text  # Director limit
    assert "100 Crore" in bdp_text or "₹100 Crore" in bdp_text  # CMD / EC limit

    # 5. Leave limits
    leave_text = " ".join(r["clause_text"] for r in clause_index_rows if r["doc_id"] == "Leave Rules")
    assert "300" in leave_text and "days" in leave_text.lower()  # 300 days ceiling
    assert "30" in leave_text and "earned leave" in leave_text.lower()  # 30 days EL
    assert "20" in leave_text and "half pay leave" in leave_text.lower()  # 20 days HPL
    assert "5" in leave_text and "study leave" in leave_text.lower()  # 5 years service

    # 6. PRBS limits
    prbs_text = " ".join(r["clause_text"] for r in clause_index_rows if r["doc_id"] == "PRBS")
    assert "30%" in prbs_text and "superannuation" in prbs_text.lower()
    assert "Circular 73" in prbs_text or "01.01.2017" in prbs_text

    # 7. Post-retirement medical
    med_text = " ".join(r["clause_text"] for r in clause_index_rows if r["doc_id"] == "Post-retirement medical")
    assert "15" in med_text and "service" in med_text.lower()
    assert "30/2015" in med_text or "Office Order" in med_text


# ---------------------------------------------------------------------------
# TEST 8: Consistency with Observed Data Patterns in PA0001 / PA0002
# ---------------------------------------------------------------------------

def test_rules_consistent_with_observed_data_patterns():
    assert PA0001_PATH.exists(), f"Missing PA0001.csv: {PA0001_PATH}"
    assert PA0002_PATH.exists(), f"Missing PA0002_PA0001.csv: {PA0002_PATH}"

    # 1. Median executive stint
    df_pa1 = pd.read_csv(PA0001_PATH, low_memory=False)
    exec_mask = df_pa1["PERSK"].isin(["E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9"])
    median_stint_months = df_pa1[exec_mask]["tenure_months"].median()

    # Median stint in months should be ~36-40 months (~3 to 3.5 years), consistent with JRTP Clause 3.0 (3-year min tenure)
    assert 30 <= median_stint_months <= 45, (
        f"Observed median executive stint is {median_stint_months} months; expected ~3 years (30-45 months)"
    )

    # 2. Share of moves within 3 years of superannuation
    df_pa2 = pd.read_csv(PA0002_PATH, low_memory=False)[["PERNR", "retirement_date"]]
    merged = df_pa1.merge(df_pa2, on="PERNR")
    moves = merged[merged["MASSN"] != "initial"].copy()
    moves["BEGDA"] = pd.to_datetime(moves["BEGDA"])
    moves["retirement_date"] = pd.to_datetime(moves["retirement_date"])
    moves["days_to_retire"] = (moves["retirement_date"] - moves["BEGDA"]).dt.days

    moves_within_3y = (moves["days_to_retire"] <= 3 * 365).sum()
    share_within_3y = moves_within_3y / len(moves)

    # Should be very low (< 3.0%), reflecting the pre-retirement exemption rule (JRTP Clause 7.0)
    assert share_within_3y < 0.03, (
        f"Observed share of moves within 3 years of retirement is {share_within_3y * 100:.2f}%; expected < 3%"
    )
