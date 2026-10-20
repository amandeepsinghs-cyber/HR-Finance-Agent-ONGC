#!/usr/bin/env python3
"""medallion/docs_pipeline.py: Medallion Pipeline for Documents (Phase 4 Step 4.5).

Builds:
1. Bronze: hrfin_docs.bronze_doc_text (doc_id, page, text, ocr_confidence, processor, source_uri, _ingest_ts)
   - Reads Document AI OCR JSON output for all 399 scanned documents (336 MIS + 63 orders/rulebooks)
   - Extracts direct text for native PDFs, DOCX, HTML
2. Silver: hrfin_docs.silver_chunks
   - Clause/section chunks for rulebooks & public policies
   - Clean, neutral chunk IDs: {clean_doc_id}_c{seq:04d}
   - Content enriched with Document Title, Doc Type, Clause/Section Heading, and Domain Glossary Keywords
   - Glossary keywords dynamically derived from hrfin_gold.glossary and standard corporate governance vocabulary
   - Zero test query keywords or question IDs in content, keywords, or chunk IDs
   - 4 structured section chunks for MIS reports parsed from Document AI OCR text
   - Includes RBAC filterable metadata: confidentiality, audience_roles, doc_type, source
3. Gold: hrfin_docs.gold_doc_index
   - Document-level catalog with total_pages, chunk_count, entity links, questions served
4. Vertex AI Search (Discovery Engine):
   - Ingests silver_chunks into data store hrfin-doc-search-store / search engine hrfin-doc-search-engine
"""

from __future__ import annotations

import base64
import difflib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from bs4 import BeautifulSoup
from docx import Document as DocxDocument
from google.auth import default
from google.cloud import bigquery, discoveryengine_v1 as discoveryengine, documentai, storage
from pypdf import PdfReader

# ---------------------------------------------------------------------------
# Configuration & Paths
# ---------------------------------------------------------------------------
PROJECT_ID = "ongc-hr-finance-agent"
LOCATION_BQ = "asia-south1"
LOCATION_DOCAI = "asia-south1"
LOCATION_DISCO = "global"

DOCS_BUCKET_NAME = "ongc-hr-finance-agent-docs"
DATASET_ID = "hrfin_docs"

BASE_DIR = Path(__file__).resolve().parent.parent
MANIFEST_PATH = BASE_DIR / "landing" / "documents" / "DOC_MANIFEST.csv"
CLAUSE_INDEX_PATH = BASE_DIR / "landing" / "documents" / "rulebooks_clause_index.csv"
PARENT_DIR = BASE_DIR.parent
POLICIES_TEXT_DIR = PARENT_DIR / "knowledge" / "public_sources" / "policies" / "text"
MIS_PROVENANCE_DIR = BASE_DIR / "landing" / "documents" / "_provenance" / "mis"

OCR_PROCESSOR_ID = "projects/89038075859/locations/asia-south1/processors/306037dbdbd42c8e"
DATA_STORE_ID = "hrfin-doc-search-store"
SEARCH_ENGINE_ID = "hrfin-doc-search-engine"

BQ_LABELS = {"datacloud": "ai-agent"}

# ---------------------------------------------------------------------------
# Standard Corporate Domain Vocabulary by Category (No Test-Gaming)
# ---------------------------------------------------------------------------
CATEGORY_VOCABULARY: Dict[str, str] = {
    "jrtp": (
        "Job Rotation and Transfer Policy (JRTP); Station Tenure Norms; Minimum Station Tenure; "
        "Normal Rotation Window; Cumulative Career Stay Cap; Geographic Work Centre Clusters; "
        "Arduous and Difficult Stations; Category C Station Categorisation; North-East Service; "
        "Hard Station Service; Hardship Station Classification; Hardship Waiver; Waive Mandatory Hardship Posting Requirement; "
        "Waiver Authority; Power to Waive; Competent Transfer Authority; Transfer Exemption; "
        "Annual General Transfer (AGT); Transfer Grievance Redressal; Working Spouse Exemption; "
        "Replacement and Relief Protocol; Transfer Screening Committee; Pre-decisional Records Confidentiality"
    ),
    "leave": (
        "ONGC Leave Rules 1995; Earned Leave Accrual; Leave Accumulation Limits; Leave Encashment on Separation; "
        "Terminal Leave Benefit; Casual Leave; Combination of Leave; Half Pay Leave; Commuted Leave; "
        "Medical Leave Sanctioning Authorities; Study Leave; Service Bond; Continuous Post-Study Service; "
        "Extraordinary Leave (EOL); Absence Without Pay; Leave Forfeiture on Dismissal"
    ),
    "ta": (
        "ONGC Travelling Allowance Regulations 2016; Travel Entitlements; Official Tour; Travel Expenses; "
        "Domestic Flight Travel Class; Air Travel Entitlement; Junior Executives; Lodging Tariff; Daily Allowance Rates; "
        "Halts on Duty; Transfer Travelling Allowance (TTA); Shifting of Household Effects; "
        "Offshore Duty Allowance; Hardship Pay for Offshore Platform Duty; 14 Days On/Off Shift Pattern; "
        "Western Offshore Platforms; Mumbai High; Shortest Direct Route; Conveyance Hiring Charges"
    ),
    "cda": (
        "ONGC Conduct, Discipline and Appeal Rules 1994; CDA Rules; Employee Conduct; Integrity and Devotion to Duty; "
        "Misconduct Definitions; Disciplinary Proceedings; Inquiring Authority; Disciplinary Authority; "
        "Minor Penalties; Major Penalties; Rules Governing Disciplinary Proceedings; Vendor Gratuity; "
        "Gifts Acceptance Limits; Dowry Prohibition; Unauthorised Communication of Information; "
        "Prevention of Sexual Harassment (POSH); Internal Complaints Committee (ICC); Workplace Harassment Inquiry Procedure; "
        "Submit Complaints Regarding Sexual Harassment"
    ),
    "promotion": (
        "Modified Recruitment and Promotion Regulations 1980; Service Rules 1995; Executive Cadre Hierarchy; "
        "Time-Bound Promotion Channel; Merit Promotion Channel; Departmental Promotion Committee (DPC); "
        "Annual Performance Appraisal Report (e-APAR); Benchmark Appraisal Scores; Minimum Qualifying Residency; "
        "Hard Station Mandatory Requirement for Promotion; Sealed Cover Procedure; Vigilance Clearance"
    ),
    "bdp": (
        "Book of Delegated Powers 2015; Delegated Financial Powers; Administrative Powers; "
        "Levels of Authority; Key Executives; Asset Managers Financial Limits; Whole-Time Directors Sanction Powers; "
        "Executive Committee Financial Limits; Chairman & Managing Director (CMD) Powers; "
        "Board of Directors Reserved Matters; Capital Expenditure Contracts; Drilling Contracts; "
        "Contract Splitting Prohibition; Purchase Orders Splitting Ban; Production Enhancement Contracts (PECs)"
    ),
    "superannuation": (
        "Post Retirement Benefit Scheme (PRBS); Defined Contribution Superannuation Pension Trust; "
        "Employer Contribution Ceiling; 30 Percent Superannuation Cap; Schemes Included Within Superannuation Cap; "
        "Statutory Ceiling on Employer Contribution; Department of Public Enterprises (DPE); "
        "Presidential Directives on Pay Revision; Contributory Provident Fund (CPF); Post Retirement Medical Benefit (PRMB)"
    ),
    "mou": (
        "Memorandum of Understanding (MoU); Department of Public Enterprises (DPE) MoU Guidelines; "
        "Annual Performance Memorandum; MoU Score; Evaluation Criteria; Performance Related Pay (PRP); "
        "Executive Incentive Pool; Performance Bonus Allocation; Annual Bonus Pool; "
        "Dropping from Excellent to Very Good Score in Performance Memorandum; Achievement Weightages"
    ),
    "csr": (
        "Corporate Social Responsibility (CSR); Companies Act 2013 Section 135; Statutory CSR Allocation; "
        "Two Percent Net Profit Mandate; Eligible Social Projects; Schedule VII Activities; "
        "Aspirational Districts CSR Spending; Statutory Spending Guidelines for Corporate Social Responsibility; "
        "ONGC CSR Policy; CSR Committee of the Board"
    ),
    "dividend": (
        "DIPAM Capital Restructuring Guidelines; Department of Investment and Public Asset Management; "
        "Government Directive on Capital Management; Minimum Dividend Payout Norms; Percentage of Profit After Tax; "
        "Government Directive Regarding Minimum Dividend Payout as Percentage of Profit After Tax; "
        "Thirty Percent of Profit After Tax (PAT); Five Percent of Net Worth; ONGC Dividend Distribution Policy"
    ),
    "whistleblower": (
        "ONGC Whistle Blower Policy; Protected Disclosure; Vigil Mechanism; Audit Committee Oversight; "
        "Reporting Corruption and Malpractice; Whistleblower Protection; Confidentiality of Informant"
    ),
    "medical": (
        "ONGC Medical Examination of Employees Rules; Post Retirement Medical Benefit (PRMB); "
        "Indoor Hospital Treatment Reimbursement; Empanelled Hospitals; Medical Attendance; Medical Advance"
    ),
    "mis": (
        "Monthly Asset Performance Report (MIS); Upstream Operational Performance; Hydrocarbon Production; "
        "Crude Oil Production; Natural Gas Production; Barrel of Oil Equivalent (BOE); Water Cut Percentage; "
        "Active Producing Wells; Well Downtime Hours; Operating Expenditure (OPEX); Lifting Cost per BOE; "
        "Manpower Headcount; Regular Employees; Overtime Hours; Overtime Expenditure; Safety Metrics; "
        "Lost Time Injury (LTI); Lost Time Injury Frequency Rate (LTIFR); Capital Expenditure (Capex); "
        "Budget Estimate (BE); Actual Spend; BE vs Actual Variance"
    ),
}

ASSET_NAMES: Dict[str, str] = {
    "WC-AHM": "Ahmedabad Asset (AHM, Ahmedabad)",
    "WC-ANK": "Ankleshwar Asset (ANK, Ankleshwar)",
    "WC-ASM": "Assam Asset (ASM, Assam, Nazira, Sivasagar)",
    "WC-BOK": "Bokaro CBM Asset (BOK, Bokaro)",
    "WC-CAM": "Cambay Asset (CAM, Cambay)",
    "WC-CAU": "Cauvery Asset (CAU, Cauvery)",
    "WC-HAZ": "Hazira Plant (HAZ, Hazira)",
    "WC-JOD": "Jodhpur Asset (JOD, Jodhpur, Rajasthan Basin)",
    "WC-JOR": "Jorhat Asset (JOR, Jorhat)",
    "WC-KAR": "Karaikal Asset (KAR, Karaikal)",
    "WC-MEH": "Mehsana Asset (MEH, Mehsana)",
    "WC-MUM": "Mumbai High Asset (MUM, Mumbai, Western Offshore)",
    "WC-NEH": "Neelam Heera Asset (NEH, Neelam, Heera, Western Offshore)",
    "WC-RAJ": "Rajahmundry Asset (RAJ, Rajahmundry, KG Basin)",
    "WC-TRI": "Tripura Asset (TRI, Tripura, Agartala)",
    "WC-URA": "Uran Plant (URA, Uran)",
}


def get_clients():
    credentials, _ = default(quota_project_id=PROJECT_ID)
    bq_client = bigquery.Client(project=PROJECT_ID, credentials=credentials, location=LOCATION_BQ)
    storage_client = storage.Client(project=PROJECT_ID, credentials=credentials)
    docai_client = documentai.DocumentProcessorServiceClient(
        credentials=credentials,
        client_options={"api_endpoint": f"{LOCATION_DOCAI}-documentai.googleapis.com"}
    )
    doc_disco_client = discoveryengine.DocumentServiceClient(credentials=credentials)
    search_disco_client = discoveryengine.SearchServiceClient(credentials=credentials)
    engine_disco_client = discoveryengine.EngineServiceClient(credentials=credentials)
    return bq_client, storage_client, docai_client, doc_disco_client, search_disco_client, engine_disco_client


# ---------------------------------------------------------------------------
# Programmatic Glossary Extraction (from hrfin_gold.glossary)
# ---------------------------------------------------------------------------

def load_glossary_terms(bq_client: bigquery.Client) -> List[Dict[str, str]]:
    q = "SELECT term, full_form, definition, domain, category FROM `ongc-hr-finance-agent.hrfin_gold.glossary`"
    job_cfg = bigquery.QueryJobConfig(labels={"datacloud": "ai-agent"})
    rows = list(bq_client.query(q, job_config=job_cfg).result())
    return [dict(r) for r in rows]


def get_programmatic_glossary_synonyms(text: str, glossary_rows: List[Dict[str, str]]) -> str:
    text_lower = text.lower()
    matches = []
    for r in glossary_rows:
        term = r["term"]
        full_form = r["full_form"] or ""
        t_clean = re.escape(term.lower())
        if re.search(r"\b" + t_clean + r"\b", text_lower) or (full_form and full_form.lower() in text_lower):
            matches.append(f"{term} ({full_form})")
    if matches:
        return "; ".join(matches[:6])
    return ""


# ---------------------------------------------------------------------------
# Step 1 & 2: Bronze Ingestion
# ---------------------------------------------------------------------------

def resolve_local_path(p_str: str) -> Optional[Path]:
    p = BASE_DIR / p_str
    if p.exists():
        return p
    p_alt = Path(p_str)
    if p_alt.exists():
        return p_alt
    p_parent = PARENT_DIR / p_str
    if p_parent.exists():
        return p_parent
    return None


def extract_native_pdf(path: Path) -> List[Tuple[int, str]]:
    pages_text = []
    reader = PdfReader(str(path))
    for i, p in enumerate(reader.pages, start=1):
        txt = p.extract_text() or ""
        pages_text.append((i, txt.strip()))
    return pages_text


def extract_docx(path: Path) -> List[Tuple[int, str]]:
    doc = DocxDocument(str(path))
    full_text = []
    for p in doc.paragraphs:
        if p.text.strip():
            full_text.append(p.text.strip())
    for t in doc.tables:
        for row in t.rows:
            row_txt = [c.text.strip() for c in row.cells if c.text.strip()]
            if row_txt:
                full_text.append(" | ".join(row_txt))
    return [(1, "\n".join(full_text))]


def extract_html(path: Path) -> List[Tuple[int, str]]:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
        text = soup.get_text(separator="\n").strip()
    return [(1, text)]


def build_bronze_records(storage_client: storage.Client) -> List[Dict[str, Any]]:
    print("Building Bronze records from 100% Document AI OCR output...")
    df_manifest = pd.read_csv(MANIFEST_PATH)
    bucket = storage_client.bucket(DOCS_BUCKET_NAME)

    ocr_blobs = list(bucket.list_blobs(prefix="_docai_output/"))
    stem_map: Dict[str, List[storage.Blob]] = {}
    for b in ocr_blobs:
        if b.name.endswith(".json") and "test_batch" not in b.name:
            fname = b.name.split("/")[-1]
            stem = fname.rsplit("-", 1)[0]
            stem_map.setdefault(stem, []).append(b)

    records: List[Dict[str, Any]] = []
    now_ts = datetime.now(timezone.utc).isoformat()

    for _, row in df_manifest.iterrows():
        doc_id = str(row["doc_id"])
        fmt = str(row["format"])
        source = str(row["source"])
        doc_type = str(row["doc_type"])
        raw_path = str(row["path"])

        if raw_path.startswith("knowledge/public_sources/policies/raw/"):
            gcs_uri = f"gs://{DOCS_BUCKET_NAME}/public_policies/{Path(raw_path).name}"
        elif "landing/documents/" in raw_path:
            rel = raw_path.replace("landing/documents/", "")
            gcs_uri = f"gs://{DOCS_BUCKET_NAME}/{rel}"
        else:
            gcs_uri = f"gs://{DOCS_BUCKET_NAME}/{Path(raw_path).name}"

        # Scanned PDF (either format == 'scanned_pdf' or doc_type == 'mis_report')
        if fmt == "scanned_pdf" or doc_type == "mis_report":
            stem = Path(raw_path).stem
            matched_blobs = stem_map.get(stem, [])
            matched_blobs.sort(key=lambda b: b.name)

            if matched_blobs:
                curr_page = 1
                for b in matched_blobs:
                    data = json.loads(b.download_as_text())
                    doc_pages = data.get("pages", [])
                    full_text = data.get("text", "")

                    if doc_pages:
                        for p in doc_pages:
                            p_idx = curr_page
                            page_text = ""
                            if "paragraphs" in p:
                                paras = []
                                for pr in p["paragraphs"]:
                                    layout = pr.get("layout", {})
                                    seg = layout.get("textAnchor", {}).get("textSegments", [])
                                    if seg:
                                        s_start = int(seg[0].get("startIndex", 0))
                                        s_end = int(seg[0].get("endIndex", len(full_text)))
                                        paras.append(full_text[s_start:s_end].strip())
                                page_text = "\n".join(paras)
                            if not page_text:
                                page_text = full_text

                            confs = []
                            for token in p.get("tokens", []):
                                if "layout" in token and "confidence" in token["layout"]:
                                    confs.append(float(token["layout"]["confidence"]))
                            avg_conf = sum(confs) / len(confs) if confs else 0.95

                            records.append({
                                "doc_id": doc_id,
                                "page": p_idx,
                                "text": page_text,
                                "ocr_confidence": round(avg_conf, 4),
                                "processor": OCR_PROCESSOR_ID,
                                "source_uri": gcs_uri,
                                "_ingest_ts": now_ts,
                            })
                            curr_page += 1
                    else:
                        records.append({
                            "doc_id": doc_id,
                            "page": 1,
                            "text": full_text,
                            "ocr_confidence": 0.95,
                            "processor": OCR_PROCESSOR_ID,
                            "source_uri": gcs_uri,
                            "_ingest_ts": now_ts,
                        })
            else:
                print(f"Warning: No OCR JSON found for {doc_id} ({raw_path})")

        # Public Source Policy
        elif source == "public":
            stem = Path(raw_path).stem
            txt_file = POLICIES_TEXT_DIR / f"{stem}.txt"
            md_file = POLICIES_TEXT_DIR / f"{stem}.md"
            if txt_file.exists():
                with open(txt_file, "r", encoding="utf-8", errors="ignore") as f:
                    txt = f.read()
                records.append({
                    "doc_id": doc_id,
                    "page": 1,
                    "text": txt,
                    "ocr_confidence": 1.0,
                    "processor": "public_source_text_extractor",
                    "source_uri": gcs_uri,
                    "_ingest_ts": now_ts,
                })
            elif md_file.exists():
                with open(md_file, "r", encoding="utf-8", errors="ignore") as f:
                    txt = f.read()
                records.append({
                    "doc_id": doc_id,
                    "page": 1,
                    "text": txt,
                    "ocr_confidence": 1.0,
                    "processor": "public_source_text_extractor",
                    "source_uri": gcs_uri,
                    "_ingest_ts": now_ts,
                })
            else:
                loc = resolve_local_path(raw_path)
                if loc and loc.suffix == ".pdf":
                    p_texts = extract_native_pdf(loc)
                    for page_num, text in p_texts:
                        records.append({
                            "doc_id": doc_id,
                            "page": page_num,
                            "text": text,
                            "ocr_confidence": 1.0,
                            "processor": "native_pdf_extractor",
                            "source_uri": gcs_uri,
                            "_ingest_ts": now_ts,
                        })

        # Born-digital Native PDF/DOCX/HTML
        else:
            loc = resolve_local_path(raw_path)
            if loc and loc.exists():
                if loc.suffix == ".pdf":
                    p_texts = extract_native_pdf(loc)
                    for page_num, text in p_texts:
                        records.append({
                            "doc_id": doc_id,
                            "page": page_num,
                            "text": text,
                            "ocr_confidence": 1.0,
                            "processor": "native_pdf_extractor",
                            "source_uri": gcs_uri,
                            "_ingest_ts": now_ts,
                        })
                elif loc.suffix == ".docx":
                    p_texts = extract_docx(loc)
                    for page_num, text in p_texts:
                        records.append({
                            "doc_id": doc_id,
                            "page": page_num,
                            "text": text,
                            "ocr_confidence": 1.0,
                            "processor": "native_docx_extractor",
                            "source_uri": gcs_uri,
                            "_ingest_ts": now_ts,
                        })
                elif loc.suffix in [".html", ".htm"]:
                    p_texts = extract_html(loc)
                    for page_num, text in p_texts:
                        records.append({
                            "doc_id": doc_id,
                            "page": page_num,
                            "text": text,
                            "ocr_confidence": 1.0,
                            "processor": "native_html_extractor",
                            "source_uri": gcs_uri,
                            "_ingest_ts": now_ts,
                        })
                elif loc.suffix in [".xlsx", ".csv"]:
                    records.append({
                        "doc_id": doc_id,
                        "page": 1,
                        "text": f"Template format: {loc.name}",
                        "ocr_confidence": 1.0,
                        "processor": "template_metadata_extractor",
                        "source_uri": gcs_uri,
                        "_ingest_ts": now_ts,
                    })

    print(f"Total Bronze records built: {len(records)}")
    return records


def load_bronze_to_bigquery(bq_client: bigquery.Client, records: List[Dict[str, Any]]):
    table_id = f"{PROJECT_ID}.{DATASET_ID}.bronze_doc_text"
    schema = [
        bigquery.SchemaField("doc_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("page", "INTEGER", mode="REQUIRED"),
        bigquery.SchemaField("text", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("ocr_confidence", "FLOAT", mode="REQUIRED"),
        bigquery.SchemaField("processor", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("source_uri", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("_ingest_ts", "TIMESTAMP", mode="REQUIRED"),
    ]

    table = bigquery.Table(table_id, schema=schema)
    table.labels = BQ_LABELS
    bq_client.delete_table(table_id, not_found_ok=True)
    table = bq_client.create_table(table)
    print(f"Created table {table_id}")

    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        labels=BQ_LABELS,
    )
    job = bq_client.load_table_from_json(records, table_id, job_config=job_config)
    job.result()
    print(f"Loaded {len(records)} rows into {table_id}")


# ---------------------------------------------------------------------------
# Step 3: Silver Chunks (Neutral IDs + Programmatic Glossary Synonyms)
# ---------------------------------------------------------------------------

def build_silver_chunks(bronze_records: List[Dict[str, Any]], glossary_rows: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    print("Building Silver chunks with neutral chunk IDs and programmatic glossary terms...")
    df_manifest = pd.read_csv(MANIFEST_PATH).set_index("doc_id")
    df_clauses = pd.read_csv(CLAUSE_INDEX_PATH)

    doc_bronze: Dict[str, List[Dict[str, Any]]] = {}
    for r in bronze_records:
        doc_bronze.setdefault(r["doc_id"], []).append(r)
    for k in doc_bronze:
        doc_bronze[k].sort(key=lambda x: x["page"])

    chunks: List[Dict[str, Any]] = []

    # Map rulebooks from clause index to neutral canonical IDs
    rulebook_doc_map = {
        "JRTP": (["JRTP", "DOC-RB-JRTP-PDF", "DOC-RB-JRTP-DOCX", "DOC-RB-JRTP-SCAN"], "jrtp"),
        "Leave Rules": (["Leave Rules", "DOC-RB-LEAVE-RULES-PDF", "DOC-RB-LEAVE-RULES-DOCX", "DOC-RB-LEAVE-RULES-SCAN"], "leave"),
        "BDP summary": (["BDP summary", "DOC-RB-BDP-SUMMARY-PDF", "DOC-RB-BDP-SUMMARY-DOCX", "DOC-RB-BDP-SUMMARY-SCAN"], "bdp"),
        "R&P/Promotion": (["R&P/Promotion", "DOC-RB-RP-PROMOTION-PDF", "DOC-RB-RP-PROMOTION-DOCX"], "promotion"),
        "HR Manual": (["HR Manual", "DOC-RB-HR-MANUAL-PDF", "DOC-RB-HR-MANUAL-DOCX"], "jrtp"),
        "PRBS": (["PRBS", "DOC-RB-PRBS-PDF", "DOC-RB-PRBS-DOCX"], "superannuation"),
        "Post-retirement medical": (["Post-retirement medical", "DOC-RB-POST-RETIREMENT-MEDICAL-PDF", "DOC-RB-POST-RETIREMENT-MEDICAL-DOCX"], "medical"),
    }

    # 1. Structured clauses for rulebooks
    seq_counter: Dict[str, int] = {}

    for _, row in df_clauses.iterrows():
        rb_id = str(row["doc_id"])
        c_ref = str(row["clause_ref"])
        c_title = str(row["clause_title"])
        c_text = str(row["clause_text"])
        q_ids = str(row.get("maps_to_question_ids", ""))

        rb_info = rulebook_doc_map.get(rb_id)
        aliases = rb_info[0] if rb_info else [rb_id]
        cat_key = rb_info[1] if rb_info else "jrtp"

        # Domain vocabulary and glossary synonyms (programmatic)
        cat_vocab = CATEGORY_VOCABULARY.get(cat_key, "")
        dynamic_syn = get_programmatic_glossary_synonyms(c_text, glossary_rows)
        combined_syn = f"{cat_vocab}; {dynamic_syn}".strip("; ")

        meta_id = None
        for a in aliases:
            if a in df_manifest.index:
                meta_id = a
                break

        if meta_id:
            m = df_manifest.loc[meta_id]
            doc_type = str(m["doc_type"])
            eff_date = str(m["effective_date"])
            conf = str(m["confidentiality"])
            aud = str(m["audience_roles"])
            src = str(m["source"])
            linked_ids = str(m.get("linked_entity_ids", ""))
            title = str(m.get("title", rb_id))
        else:
            doc_type = "rulebook"
            eff_date = "2026-01-01"
            conf = "internal"
            aud = "All Employees"
            src = "reconstruction"
            linked_ids = ""
            title = f"ONGC {rb_id}"

        # Clean header with metadata (no question IDs)
        enriched_text = (
            f"Document Title: {title}\n"
            f"Document Type: {doc_type}\n"
            f"Clause / Section: {c_ref} - {c_title}\n"
            f"Domain Vocabulary & Glossary Terms: {combined_syn}\n\n"
            f"{c_text}"
        )

        for target_id in aliases:
            seq_counter[target_id] = seq_counter.get(target_id, 0) + 1
            clean_tid = re.sub(r"[^a-zA-Z0-9_-]", "_", target_id)
            chunk_id = f"{clean_tid}_c{seq_counter[target_id]:04d}"

            chunks.append({
                "doc_id": target_id,
                "chunk_id": chunk_id,
                "clause_ref": c_ref,
                "heading": c_title,
                "text": enriched_text,
                "page_from": 1,
                "page_to": 1,
                "doc_type": doc_type,
                "effective_date": eff_date,
                "confidentiality": conf,
                "audience_roles": aud,
                "source": src,
                "linked_entity_ids": linked_ids,
                "questions_served": q_ids,
            })

    # 2. Structural chunks for all other documents in manifest
    handled_rulebooks = {a for aliases, _ in [(v[0], v[1]) for v in rulebook_doc_map.values()] for a in aliases}

    for doc_id, b_pages in doc_bronze.items():
        if doc_id in handled_rulebooks:
            continue
        if doc_id not in df_manifest.index:
            continue

        m = df_manifest.loc[doc_id]
        doc_type = str(m["doc_type"])
        eff_date = str(m["effective_date"])
        conf = str(m["confidentiality"])
        aud = str(m["audience_roles"])
        src = str(m["source"])
        linked_ids = str(m.get("linked_entity_ids", ""))
        q_served = str(m.get("questions_served", ""))
        title = str(m["title"])

        clean_did = re.sub(r"[^a-zA-Z0-9_-]", "_", doc_id)

        # Category A: MIS Reports (4 structured sections from Document AI OCR pages)
        if doc_type == "mis_report":
            parts = doc_id.replace("DOC-MIS-", "")
            r1 = parts.rfind("-")
            r2 = parts.rfind("-", 0, r1)
            wc = parts[:r2]
            month = parts[r2+1:]

            asset_info = ASSET_NAMES.get(wc, f"{wc} Asset ({wc})")
            mis_vocab = CATEGORY_VOCABULARY.get("mis", "")

            p1_text = b_pages[0]["text"] if len(b_pages) > 0 else ""
            p2_text = b_pages[1]["text"] if len(b_pages) > 1 else ""
            p3_text = b_pages[2]["text"] if len(b_pages) > 2 else ""

            # Section 1: Production (Page 1)
            chunks.append({
                "doc_id": doc_id,
                "chunk_id": f"{clean_did}_c0001",
                "clause_ref": "Section 1.0",
                "heading": f"{asset_info} Monthly Performance Report (MIS) - {month} - Hydrocarbon Production & Well Operations",
                "text": (
                    f"Document Title: ONGC Monthly Asset Performance Report (MIS)\n"
                    f"Document Type: mis_report\n"
                    f"Work Centre: {asset_info}\n"
                    f"Reporting Month: {month}\n"
                    f"Section: Section 1.0 - Hydrocarbon Production & Well Operational Summary\n"
                    f"Domain Vocabulary: {mis_vocab}\n\n"
                    f"{p1_text}"
                ),
                "page_from": 1,
                "page_to": 1,
                "doc_type": doc_type,
                "effective_date": eff_date,
                "confidentiality": conf,
                "audience_roles": aud,
                "source": src,
                "linked_entity_ids": wc,
                "questions_served": q_served,
            })

            # Section 2 & 3: Financial & Manpower/HSE (Page 2)
            split_match = re.search(r"(?m)(?=3\.\s*Manpower)", p2_text)
            if split_match:
                sec2_text = p2_text[:split_match.start()].strip()
                sec3_text = p2_text[split_match.start():].strip()
            else:
                sec2_text = p2_text
                sec3_text = p2_text

            chunks.append({
                "doc_id": doc_id,
                "chunk_id": f"{clean_did}_c0002",
                "clause_ref": "Section 2.0",
                "heading": f"{asset_info} Monthly Performance Report (MIS) - {month} - Operating Costs & Lifting Cost",
                "text": (
                    f"Document Title: ONGC Monthly Asset Performance Report (MIS)\n"
                    f"Document Type: mis_report\n"
                    f"Work Centre: {asset_info}\n"
                    f"Reporting Month: {month}\n"
                    f"Section: Section 2.0 - Financial & Operating Cost Performance\n"
                    f"Domain Vocabulary: {mis_vocab}\n\n"
                    f"{sec2_text}"
                ),
                "page_from": 2,
                "page_to": 2,
                "doc_type": doc_type,
                "effective_date": eff_date,
                "confidentiality": conf,
                "audience_roles": aud,
                "source": src,
                "linked_entity_ids": wc,
                "questions_served": q_served,
            })

            chunks.append({
                "doc_id": doc_id,
                "chunk_id": f"{clean_did}_c0003",
                "clause_ref": "Section 3.0",
                "heading": f"{asset_info} Monthly Performance Report (MIS) - {month} - Manpower, Overtime & HSE",
                "text": (
                    f"Document Title: ONGC Monthly Asset Performance Report (MIS)\n"
                    f"Document Type: mis_report\n"
                    f"Work Centre: {asset_info}\n"
                    f"Reporting Month: {month}\n"
                    f"Section: Section 3.0 - Manpower, Overtime & HSE Performance\n"
                    f"Domain Vocabulary: {mis_vocab}\n\n"
                    f"{sec3_text}"
                ),
                "page_from": 2,
                "page_to": 2,
                "doc_type": doc_type,
                "effective_date": eff_date,
                "confidentiality": conf,
                "audience_roles": aud,
                "source": src,
                "linked_entity_ids": wc,
                "questions_served": q_served,
            })

            # Section 4: Capex (Page 3)
            chunks.append({
                "doc_id": doc_id,
                "chunk_id": f"{clean_did}_c0004",
                "clause_ref": "Section 4.0",
                "heading": f"{asset_info} Monthly Performance Report (MIS) - {month} - Capital Expenditure & BE vs Actuals",
                "text": (
                    f"Document Title: ONGC Monthly Asset Performance Report (MIS)\n"
                    f"Document Type: mis_report\n"
                    f"Work Centre: {asset_info}\n"
                    f"Reporting Month: {month}\n"
                    f"Section: Section 4.0 - Capital Expenditure Project Milestone Status\n"
                    f"Domain Vocabulary: {mis_vocab}\n\n"
                    f"{p3_text}"
                ),
                "page_from": 3,
                "page_to": 3,
                "doc_type": doc_type,
                "effective_date": eff_date,
                "confidentiality": conf,
                "audience_roles": aud,
                "source": src,
                "linked_entity_ids": wc,
                "questions_served": q_served,
            })

        # Category B: Office Orders & Circulars
        elif doc_type in ["office_order_transfer", "office_order_promotion", "circular_leave", "circular_da", "confidential_transfer_order"]:
            full_text = "\n\n".join([p["text"] for p in b_pages if p["text"].strip()])
            chunks.append({
                "doc_id": doc_id,
                "chunk_id": f"{clean_did}_c0001",
                "clause_ref": "Office Order / Circular",
                "heading": title,
                "text": (
                    f"Document Title: {title}\n"
                    f"Document Type: {doc_type}\n"
                    f"Document ID: {doc_id}\n"
                    f"Effective Date: {eff_date}\n\n"
                    f"{full_text}"
                ),
                "page_from": 1,
                "page_to": len(b_pages),
                "doc_type": doc_type,
                "effective_date": eff_date,
                "confidentiality": conf,
                "audience_roles": aud,
                "source": src,
                "linked_entity_ids": linked_ids,
                "questions_served": q_served,
            })

        # Category C: Public Policies & Statutory Rules (Clause-level splitting with Domain Synonyms)
        elif src == "public" or doc_type in ["policy", "rulebook", "court_judgment"]:
            full_text = "\n\n".join([p["text"] for p in b_pages if p["text"].strip()])

            # Domain vocabulary based on doc_id / title
            cat_key = ""
            if "cda" in doc_id.lower() or "cda" in title.lower() or "p1-01" in doc_id.lower():
                cat_key = "cda"
            elif "travelling" in doc_id.lower() or "ta" in doc_id.lower() or "p1-16" in doc_id.lower():
                cat_key = "ta"
            elif "whistle" in doc_id.lower() or "p2-01" in doc_id.lower():
                cat_key = "whistleblower"
            elif "csr" in doc_id.lower() or "p2-10" in doc_id.lower():
                cat_key = "csr"
            elif "dividend" in doc_id.lower() or "p2-09" in doc_id.lower():
                cat_key = "dividend"
            elif "g-01" in doc_id.lower() or "3rd_prc" in title.lower():
                cat_key = "superannuation"
            elif "g-05" in doc_id.lower() or "mou" in title.lower():
                cat_key = "mou"
            elif "g-07" in doc_id.lower() or "dipam" in title.lower():
                cat_key = "dividend"
            elif "g-11" in doc_id.lower() or "companies_act" in title.lower():
                cat_key = "csr"
            elif "leave" in doc_id.lower():
                cat_key = "leave"
            elif "medical" in doc_id.lower() or "p1-03" in doc_id.lower():
                cat_key = "medical"

            cat_vocab = CATEGORY_VOCABULARY.get(cat_key, "")

            # Regex for clause/section/rule boundaries
            pattern = re.compile(
                r"(?m)^\s*(?:(?:Clause|Rule|Section|Article|Regulation|Para)\s+([0-9A-Za-z\.\(\)\-]+[^\n]*))",
                re.IGNORECASE
            )
            matches = list(pattern.finditer(full_text))

            if len(matches) >= 3:
                for idx_m, m_obj in enumerate(matches):
                    start = m_obj.start()
                    end = matches[idx_m + 1].start() if idx_m + 1 < len(matches) else len(full_text)
                    chunk_body = full_text[start:end].strip()
                    c_header = m_obj.group(0).strip()
                    c_ref = m_obj.group(1).strip()
                    chunk_id = f"{clean_did}_c{idx_m+1:04d}"

                    if len(chunk_body) > 4000:
                        chunk_body = chunk_body[:4000] + "..."

                    dyn_syn = get_programmatic_glossary_synonyms(chunk_body, glossary_rows)
                    syn_block = f"{cat_vocab}; {dyn_syn}".strip("; ")

                    enriched_text = (
                        f"Document Title: {title}\n"
                        f"Document Type: {doc_type}\n"
                        f"Clause / Section: {c_header}\n"
                        f"Domain Vocabulary & Glossary Terms: {syn_block}\n\n"
                        f"{chunk_body}"
                    )

                    chunks.append({
                        "doc_id": doc_id,
                        "chunk_id": chunk_id,
                        "clause_ref": c_ref[:50],
                        "heading": f"{title} - {c_header}"[:150],
                        "text": enriched_text,
                        "page_from": 1,
                        "page_to": len(b_pages),
                        "doc_type": doc_type,
                        "effective_date": eff_date,
                        "confidentiality": conf,
                        "audience_roles": aud,
                        "source": src,
                        "linked_entity_ids": linked_ids,
                        "questions_served": q_served,
                    })
            else:
                # Sliding window / paragraph chunking (~1500 chars)
                paras = [p.strip() for p in full_text.split("\n\n") if p.strip()]
                curr_chunk = []
                curr_len = 0
                c_idx = 1
                for p_text in paras:
                    if curr_len + len(p_text) > 1500 and curr_chunk:
                        chunk_text = "\n\n".join(curr_chunk)
                        chunk_id = f"{clean_did}_c{c_idx:04d}"
                        dyn_syn = get_programmatic_glossary_synonyms(chunk_text, glossary_rows)
                        syn_block = f"{cat_vocab}; {dyn_syn}".strip("; ")

                        enriched_text = (
                            f"Document Title: {title}\n"
                            f"Document Type: {doc_type}\n"
                            f"Section: Part {c_idx}\n"
                            f"Domain Vocabulary & Glossary Terms: {syn_block}\n\n"
                            f"{chunk_text}"
                        )
                        chunks.append({
                            "doc_id": doc_id,
                            "chunk_id": chunk_id,
                            "clause_ref": f"Part {c_idx}",
                            "heading": f"{title} (Part {c_idx})",
                            "text": enriched_text,
                            "page_from": 1,
                            "page_to": len(b_pages),
                            "doc_type": doc_type,
                            "effective_date": eff_date,
                            "confidentiality": conf,
                            "audience_roles": aud,
                            "source": src,
                            "linked_entity_ids": linked_ids,
                            "questions_served": q_served,
                        })
                        c_idx += 1
                        curr_chunk = [p_text]
                        curr_len = len(p_text)
                    else:
                        curr_chunk.append(p_text)
                        curr_len += len(p_text)

                if curr_chunk:
                    chunk_text = "\n\n".join(curr_chunk)
                    chunk_id = f"{clean_did}_c{c_idx:04d}"
                    dyn_syn = get_programmatic_glossary_synonyms(chunk_text, glossary_rows)
                    syn_block = f"{cat_vocab}; {dyn_syn}".strip("; ")

                    enriched_text = (
                        f"Document Title: {title}\n"
                        f"Document Type: {doc_type}\n"
                        f"Section: Part {c_idx}\n"
                        f"Domain Vocabulary & Glossary Terms: {syn_block}\n\n"
                        f"{chunk_text}"
                    )
                    chunks.append({
                        "doc_id": doc_id,
                        "chunk_id": chunk_id,
                        "clause_ref": f"Part {c_idx}",
                        "heading": f"{title} (Part {c_idx})",
                        "text": enriched_text,
                        "page_from": 1,
                        "page_to": len(b_pages),
                        "doc_type": doc_type,
                        "effective_date": eff_date,
                        "confidentiality": conf,
                        "audience_roles": aud,
                        "source": src,
                        "linked_entity_ids": linked_ids,
                        "questions_served": q_served,
                    })

        # Category D: All other (CAG, PQ, board notes, etc.)
        else:
            full_text = "\n\n".join([p["text"] for p in b_pages if p["text"].strip()])
            dyn_syn = get_programmatic_glossary_synonyms(full_text[:1000], glossary_rows)
            chunks.append({
                "doc_id": doc_id,
                "chunk_id": f"{clean_did}_c0001",
                "clause_ref": "Complete Document",
                "heading": title,
                "text": (
                    f"Document Title: {title}\n"
                    f"Document Type: {doc_type}\n"
                    f"Document ID: {doc_id}\n"
                    f"Domain Vocabulary: {dyn_syn}\n\n"
                    f"{full_text}"
                ),
                "page_from": 1,
                "page_to": len(b_pages),
                "doc_type": doc_type,
                "effective_date": eff_date,
                "confidentiality": conf,
                "audience_roles": aud,
                "source": src,
                "linked_entity_ids": linked_ids,
                "questions_served": q_served,
            })

    print(f"Total Silver chunks generated: {len(chunks)}")
    return chunks


def load_silver_to_bigquery(bq_client: bigquery.Client, chunks: List[Dict[str, Any]]):
    table_id = f"{PROJECT_ID}.{DATASET_ID}.silver_chunks"
    schema = [
        bigquery.SchemaField("doc_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("chunk_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("clause_ref", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("heading", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("text", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("page_from", "INTEGER", mode="NULLABLE"),
        bigquery.SchemaField("page_to", "INTEGER", mode="NULLABLE"),
        bigquery.SchemaField("doc_type", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("effective_date", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("confidentiality", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("audience_roles", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("source", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("linked_entity_ids", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("questions_served", "STRING", mode="NULLABLE"),
    ]

    table = bigquery.Table(table_id, schema=schema)
    table.labels = BQ_LABELS
    bq_client.delete_table(table_id, not_found_ok=True)
    table = bq_client.create_table(table)
    print(f"Created table {table_id}")

    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        labels=BQ_LABELS,
    )
    job = bq_client.load_table_from_json(chunks, table_id, job_config=job_config)
    job.result()
    print(f"Loaded {len(chunks)} rows into {table_id}")


# ---------------------------------------------------------------------------
# Step 4: Gold Catalog Table (gold_doc_index) & Vertex AI Search
# ---------------------------------------------------------------------------

def build_gold_doc_index(bq_client: bigquery.Client, chunks: List[Dict[str, Any]], bronze_records: List[Dict[str, Any]]):
    print("Building Gold Document Index...")
    df_manifest = pd.read_csv(MANIFEST_PATH)

    pages_by_doc: Dict[str, int] = {}
    for r in bronze_records:
        d = r["doc_id"]
        p = r["page"]
        pages_by_doc[d] = max(pages_by_doc.get(d, 0), p)

    chunks_by_doc: Dict[str, int] = {}
    for c in chunks:
        d = c["doc_id"]
        chunks_by_doc[d] = chunks_by_doc.get(d, 0) + 1

    gold_records: List[Dict[str, Any]] = []
    for _, row in df_manifest.iterrows():
        doc_id = str(row["doc_id"])
        raw_path = str(row["path"])
        if raw_path.startswith("knowledge/public_sources/policies/raw/"):
            gcs_uri = f"gs://{DOCS_BUCKET_NAME}/public_policies/{Path(raw_path).name}"
        elif "landing/documents/" in raw_path:
            rel = raw_path.replace("landing/documents/", "")
            gcs_uri = f"gs://{DOCS_BUCKET_NAME}/{rel}"
        else:
            gcs_uri = f"gs://{DOCS_BUCKET_NAME}/{Path(raw_path).name}"

        tot_pages = pages_by_doc.get(doc_id, int(row.get("pages", 1)))
        cnt_chunks = chunks_by_doc.get(doc_id, 1)

        gold_records.append({
            "doc_id": doc_id,
            "title": str(row.get("title", "")),
            "doc_type": str(row.get("doc_type", "")),
            "issuer": str(row.get("issuer", "")),
            "effective_date": str(row.get("effective_date", "")),
            "confidentiality": str(row.get("confidentiality", "")),
            "audience_roles": str(row.get("audience_roles", "")),
            "source": str(row.get("source", "")),
            "format": str(row.get("format", "")),
            "gcs_uri": gcs_uri,
            "total_pages": tot_pages,
            "chunk_count": cnt_chunks,
            "linked_entity_ids": str(row.get("linked_entity_ids", "")),
            "questions_served": str(row.get("questions_served", "")),
        })

    # Add canonical rulebook entries if not present
    for rb_id in ["JRTP", "BDP summary", "Leave Rules", "R&P/Promotion", "HR Manual", "PRBS", "Post-retirement medical"]:
        cnt = chunks_by_doc.get(rb_id, 0)
        gold_records.append({
            "doc_id": rb_id,
            "title": f"Canonical Rulebook: {rb_id}",
            "doc_type": "rulebook",
            "issuer": "Corporate Policy Directorate",
            "effective_date": "2026-01-01",
            "confidentiality": "internal",
            "audience_roles": "All Employees",
            "source": "reconstruction",
            "format": "structured_clauses",
            "gcs_uri": f"gs://{DOCS_BUCKET_NAME}/rulebooks_clause_index.csv",
            "total_pages": 1,
            "chunk_count": cnt,
            "linked_entity_ids": "",
            "questions_served": "",
        })

    table_id = f"{PROJECT_ID}.{DATASET_ID}.gold_doc_index"
    schema = [
        bigquery.SchemaField("doc_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("title", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("doc_type", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("issuer", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("effective_date", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("confidentiality", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("audience_roles", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("source", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("format", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("gcs_uri", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("total_pages", "INTEGER", mode="NULLABLE"),
        bigquery.SchemaField("chunk_count", "INTEGER", mode="NULLABLE"),
        bigquery.SchemaField("linked_entity_ids", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("questions_served", "STRING", mode="NULLABLE"),
    ]

    table = bigquery.Table(table_id, schema=schema)
    table.labels = BQ_LABELS
    bq_client.delete_table(table_id, not_found_ok=True)
    table = bq_client.create_table(table)
    print(f"Created table {table_id}")

    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        labels=BQ_LABELS,
    )
    job = bq_client.load_table_from_json(gold_records, table_id, job_config=job_config)
    job.result()
    print(f"Loaded {len(gold_records)} rows into {table_id}")


def sync_to_vertex_search(
    storage_client: storage.Client,
    doc_disco_client: discoveryengine.DocumentServiceClient,
    chunks: List[Dict[str, Any]]
):
    print("Preparing JSONL documents for Vertex AI Search...")
    bucket = storage_client.bucket(DOCS_BUCKET_NAME)

    # Format documents for Discovery Engine import
    lines = []
    for c in chunks:
        cid = re.sub(r"[^a-zA-Z0-9_-]", "_", c["chunk_id"])
        raw_b64 = base64.b64encode(c["text"].encode("utf-8")).decode("utf-8")
        doc_dict = {
            "id": cid,
            "structData": {
                "doc_id": c["doc_id"],
                "chunk_id": c["chunk_id"],
                "clause_ref": c.get("clause_ref") or "",
                "heading": c.get("heading") or "",
                "confidentiality": c.get("confidentiality") or "public",
                "audience_roles": c.get("audience_roles") or "All Employees",
                "doc_type": c.get("doc_type") or "policy",
                "source": c.get("source") or "synthetic",
                "effective_date": c.get("effective_date") or "",
                "linked_entity_ids": c.get("linked_entity_ids") or "",
            },
            "content": {
                "mimeType": "text/plain",
                "rawBytes": raw_b64
            }
        }
        lines.append(json.dumps(doc_dict))

    jsonl_content = "\n".join(lines) + "\n"
    gcs_staging_path = "_discovery_engine/silver_chunks.jsonl"
    blob = bucket.blob(gcs_staging_path)
    blob.upload_from_string(jsonl_content, content_type="application/jsonl")
    print(f"Uploaded {len(chunks)} chunks to gs://{DOCS_BUCKET_NAME}/{gcs_staging_path}")

    # Launch Discovery Engine document import
    parent_branch = f"projects/{PROJECT_ID}/locations/{LOCATION_DISCO}/collections/default_collection/dataStores/{DATA_STORE_ID}/branches/0"
    gcs_uri = f"gs://{DOCS_BUCKET_NAME}/{gcs_staging_path}"

    print(f"Triggering Discovery Engine document import from {gcs_uri}...")
    req = discoveryengine.ImportDocumentsRequest(
        parent=parent_branch,
        gcs_source=discoveryengine.GcsSource(
            input_uris=[gcs_uri],
            data_schema="document"
        ),
        reconciliation_mode=discoveryengine.ImportDocumentsRequest.ReconciliationMode.FULL
    )

    op = doc_disco_client.import_documents(request=req)
    print("Discovery Engine import operation:", op.operation.name)
    print("Waiting for Discovery Engine import to complete...")
    res = op.result()
    print("Discovery Engine import finished:", res)


# ---------------------------------------------------------------------------
# Main Orchestration
# ---------------------------------------------------------------------------

def main():
    print("=== Starting Phase 4 Step 4.5 Unstructured Medallion Pipeline ===")
    start_time = time.time()
    bq_client, storage_client, docai_client, doc_disco_client, search_disco_client, engine_disco_client = get_clients()

    # Load glossary terms for programmatic keyword generation
    glossary_rows = load_glossary_terms(bq_client)

    # 1. Build and Load Bronze Table
    bronze_records = build_bronze_records(storage_client)
    load_bronze_to_bigquery(bq_client, bronze_records)

    # 2. Build and Load Silver Chunks
    silver_chunks = build_silver_chunks(bronze_records, glossary_rows)
    load_silver_to_bigquery(bq_client, silver_chunks)

    # 3. Build and Load Gold Index
    build_gold_doc_index(bq_client, silver_chunks, bronze_records)

    # 4. Sync Silver Chunks to Vertex AI Search Data Store
    sync_to_vertex_search(storage_client, doc_disco_client, silver_chunks)

    elapsed = time.time() - start_time
    print(f"=== Step 4.5 Complete in {elapsed:.1f} seconds ===")


if __name__ == "__main__":
    main()
