"""gen_38_doc_manifest.py: Unified document metadata manifest generator (Step 3.8).

Unifies:
1. landing/documents/DOC_MANIFEST_3x.csv (Office orders, circulars, confidential board notes, parliament replies)
2. landing/documents/DOC_MANIFEST_34_37.csv (336 MIS reports + 4 governance templates)
3. Step 3.1 rulebooks (14 native docx/pdf, 3 scanned pdf, 1 rulebooks_clause_index.csv)
4. 78 real public policy raw files under knowledge/public_sources/policies/raw/

Output:
- landing/documents/DOC_MANIFEST.csv
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import pandas as pd
import pypdf
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_DIR = BASE_DIR.parent
DOCS_DIR = BASE_DIR / "landing" / "documents"
NATIVE_DIR = DOCS_DIR / "native"
SCANNED_DIR = DOCS_DIR / "scanned"
TEMPLATES_DIR = DOCS_DIR / "templates"
PROVENANCE_DIR = DOCS_DIR / "_provenance"
POLICIES_RAW_DIR = PROJECT_DIR / "knowledge" / "public_sources" / "policies" / "raw"
POLICY_MAP_PATH = BASE_DIR / "world_bible" / "policy_question_map.yaml"


def get_pdf_page_count(pdf_path: Path) -> int:
    """Extract page count from PDF using pypdf safely."""
    try:
        reader = pypdf.PdfReader(str(pdf_path))
        return len(reader.pages)
    except Exception:
        return 1


def build_3x_entries() -> List[Dict[str, Any]]:
    """Build manifest entries from DOC_MANIFEST_3x.csv."""
    manifest_3x_path = DOCS_DIR / "DOC_MANIFEST_3x.csv"
    assert manifest_3x_path.exists(), f"Missing {manifest_3x_path}"
    df = pd.read_csv(manifest_3x_path)

    entries = []
    for _, row in df.iterrows():
        d_id = str(row["doc_id"]).strip()
        fmt = str(row["format"]).strip().lower()
        conf = str(row["confidentiality"]).strip().lower().replace(" ", "_")

        # Determine file path on disk
        ext = ".pdf" if "pdf" in fmt else ".docx"
        scanned_path = SCANNED_DIR / f"{d_id}{ext}"
        native_path = NATIVE_DIR / f"{d_id}{ext}"

        if scanned_path.exists():
            rel_path = f"landing/documents/scanned/{d_id}{ext}"
            actual_path = scanned_path
        elif native_path.exists():
            rel_path = f"landing/documents/native/{d_id}{ext}"
            actual_path = native_path
        else:
            raise FileNotFoundError(f"File for 3x doc {d_id} not found on disk")

        # Page count
        pages_cnt = get_pdf_page_count(actual_path) if "pdf" in fmt else 2

        # Role consistency check for strictly_confidential
        roles = str(row["audience_roles"]).strip()
        if conf == "strictly_confidential" and "all" in roles.lower():
            roles = "CMD;Director (HR);Director (Finance);Chief Vigilance Officer"

        entry = {
            "doc_id": d_id,
            "title": str(row["title"]).strip(),
            "doc_type": str(row["type"]).strip(),
            "issuer": str(row["issuer"]).strip(),
            "effective_date": str(row["date"]).strip(),
            "confidentiality": conf,
            "audience_roles": roles,
            "source": str(row["source"]).strip(),
            "format": fmt,
            "path": rel_path,
            "pages": pages_cnt,
            "linked_entity_ids": "" if pd.isna(row["linked_entity_ids"]) else str(row["linked_entity_ids"]).strip(),
            "questions_served": "" if pd.isna(row["questions_served"]) else str(row["questions_served"]).strip(),
            "provenance_sql": "" if pd.isna(row["provenance_sql"]) else str(row["provenance_sql"]).strip(),
        }
        entries.append(entry)

    return entries


def build_34_37_entries() -> List[Dict[str, Any]]:
    """Build manifest entries from DOC_MANIFEST_34_37.csv."""
    manifest_34_37_path = DOCS_DIR / "DOC_MANIFEST_34_37.csv"
    assert manifest_34_37_path.exists(), f"Missing {manifest_34_37_path}"
    df = pd.read_csv(manifest_34_37_path)

    entries = []
    template_paths = {
        "DOC-TMPL-BOARD-NOTE": ("landing/documents/templates/template_board_note.docx", TEMPLATES_DIR / "template_board_note.docx"),
        "DOC-TMPL-AGT-PROPOSAL": ("landing/documents/templates/template_annual_general_transfer_proposal.xlsx", TEMPLATES_DIR / "template_annual_general_transfer_proposal.xlsx"),
        "DOC-TMPL-PARLIAMENT-REPLY": ("landing/documents/templates/template_parliament_reply_format.docx", TEMPLATES_DIR / "template_parliament_reply_format.docx"),
        "DOC-TMPL-QUARTERLY-PNL": ("landing/documents/templates/template_quarterly_asset_pnl.xlsx", TEMPLATES_DIR / "template_quarterly_asset_pnl.xlsx"),
    }

    for _, row in df.iterrows():
        d_id = str(row["doc_id"]).strip()
        m_type = str(row["type"]).strip()
        fmt = str(row["format"]).strip().lower()

        if m_type == "mis_report":
            wc = str(row["asset_wc_id"]).strip()
            mo = str(row["month"]).strip()
            rel_path = f"landing/documents/scanned/mis/MIS_{wc}_{mo}.pdf"
            actual_path = DOCS_DIR / f"scanned/mis/MIS_{wc}_{mo}.pdf"
            assert actual_path.exists(), f"Missing MIS report file: {actual_path}"
            pages_cnt = get_pdf_page_count(actual_path)

            entry = {
                "doc_id": d_id,
                "title": str(row["title"]).strip(),
                "doc_type": "mis_report",
                "issuer": f"Asset Management Directorate ({wc})",
                "effective_date": f"{mo}-01",
                "confidentiality": "internal",
                "audience_roles": "Asset Manager;Key Executive;Director (Exploration);Director (Production);Director (Finance);CMD",
                "source": "synthetic",
                "format": fmt,
                "path": rel_path,
                "pages": pages_cnt,
                "linked_entity_ids": wc,
                "questions_served": str(row["questions_served"]).replace(",", ";").strip(),
                "provenance_sql": str(row["provenance_sql"]).strip(),
            }
            entries.append(entry)

        elif m_type == "template":
            assert d_id in template_paths, f"Unknown template {d_id}"
            rel_path, actual_path = template_paths[d_id]
            assert actual_path.exists(), f"Missing template file: {actual_path}"

            entry = {
                "doc_id": d_id,
                "title": str(row["title"]).strip(),
                "doc_type": "template",
                "issuer": "Corporate Governance & Compliance",
                "effective_date": "2026-04-01",
                "confidentiality": "internal",
                "audience_roles": "all",
                "source": "synthetic",
                "format": fmt,
                "path": rel_path,
                "pages": 1,
                "linked_entity_ids": "",
                "questions_served": str(row["questions_served"]).replace(",", ";").strip(),
                "provenance_sql": str(row["provenance_sql"]).strip(),
            }
            entries.append(entry)

    return entries


def build_31_rulebook_entries() -> List[Dict[str, Any]]:
    """Build manifest entries for Step 3.1 rulebooks (native docx/pdf, scanned pdf, clause index)."""
    clause_index_path = DOCS_DIR / "rulebooks_clause_index.csv"
    rule_q_map: Dict[str, Set[str]] = {}
    if clause_index_path.exists():
        ci_df = pd.read_csv(clause_index_path)
        for _, r in ci_df.iterrows():
            rb_id = str(r["doc_id"]).strip()
            q_ids = str(r["maps_to_question_ids"]).split(";")
            for q in q_ids:
                q_clean = q.strip()
                if q_clean:
                    rule_q_map.setdefault(rb_id, set()).add(q_clean)

    rulebook_catalog = [
        {
            "code": "JRTP",
            "title": "ONGC Job Rotation and Transfer Policy (JRTP, Rev 4)",
            "base_name": "ongc_job_rotation_transfer_policy_jrtp",
            "effective_date": "2024-04-01",
            "has_scanned": True,
            "q_default": "E2; P1; P2; P11; D5; H10; T2_FU2",
        },
        {
            "code": "BDP summary",
            "title": "ONGC Book of Delegated Powers (BDP 2015 - Governance Summary)",
            "base_name": "ongc_book_of_delegated_powers_bdp_summary",
            "effective_date": "2015-05-15",
            "has_scanned": True,
            "q_default": "P1-18; P3; P15; F1; F5",
        },
        {
            "code": "Leave Rules",
            "title": "ONGC Leave Rules, 1995 (Consolidated Provisions)",
            "base_name": "ongc_leave_rules_1995",
            "effective_date": "1995-01-01",
            "has_scanned": True,
            "q_default": "J-01; J-02; J-06; J-07; J-08; P4; E4",
        },
        {
            "code": "R&P/Promotion",
            "title": "ONGC Modified Recruitment & Promotion Regulations, 1980",
            "base_name": "ongc_modified_recruitment_and_promotion_regulations",
            "effective_date": "1980-01-01",
            "has_scanned": False,
            "q_default": "J-15; J-16; J-17; H5_FU3; P5",
        },
        {
            "code": "HR Manual",
            "title": "ONGC HR Manual - Standard Designations, Levels & Scales of Pay",
            "base_name": "ongc_hr_manual_designations_pay_scales_service_conditions",
            "effective_date": "2017-01-01",
            "has_scanned": False,
            "q_default": "M3_FU1; P1-02; H1; H3",
        },
        {
            "code": "PRBS",
            "title": "ONGC Self-Contributory Post-Retirement & Death-in-Service Benefit Scheme (PRBS)",
            "base_name": "ongc_prbs_superannuation_benefit_scheme_rules",
            "effective_date": "2018-04-18",
            "has_scanned": False,
            "q_default": "P1-10; J-09; J-10; J-11; J-12; J-13; P7",
        },
        {
            "code": "Post-retirement medical",
            "title": "ONGC Post-Retirement Medical Benefit Scheme (PRMBS)",
            "base_name": "ongc_post_retirement_medical_benefit_scheme",
            "effective_date": "2015-01-01",
            "has_scanned": False,
            "q_default": "P1-11; P1-12; P1-13; P1-14; P1-15; J-21; P8",
        },
    ]

    entries = []

    for item in rulebook_catalog:
        code = item["code"]
        title = item["title"]
        base = item["base_name"]
        eff_date = item["effective_date"]

        # Questions served
        qs = rule_q_map.get(code, set())
        if qs:
            qs_str = "; ".join(sorted(qs))
        else:
            qs_str = item["q_default"]

        # Native DOCX
        docx_path = NATIVE_DIR / f"{base}.docx"
        assert docx_path.exists(), f"Missing native docx: {docx_path}"
        id_suffix = code.replace(" ", "-").replace("/", "-").replace("&", "").upper()
        entries.append({
            "doc_id": f"DOC-RB-{id_suffix}-DOCX",
            "title": f"{title} (Master DOCX Edition)",
            "doc_type": "rulebook",
            "issuer": "Corporate HR Administration",
            "effective_date": eff_date,
            "confidentiality": "internal",
            "audience_roles": "all",
            "source": "reconstruction",
            "format": "docx",
            "path": f"landing/documents/native/{base}.docx",
            "pages": 12,
            "linked_entity_ids": "",
            "questions_served": qs_str,
            "provenance_sql": "",
        })

        # Native PDF
        pdf_path = NATIVE_DIR / f"{base}.pdf"
        assert pdf_path.exists(), f"Missing native pdf: {pdf_path}"
        pdf_pages = get_pdf_page_count(pdf_path)
        entries.append({
            "doc_id": f"DOC-RB-{id_suffix}-PDF",
            "title": f"{title} (Official Native PDF)",
            "doc_type": "rulebook",
            "issuer": "Corporate HR Administration",
            "effective_date": eff_date,
            "confidentiality": "internal",
            "audience_roles": "all",
            "source": "reconstruction",
            "format": "pdf",
            "path": f"landing/documents/native/{base}.pdf",
            "pages": pdf_pages,
            "linked_entity_ids": "",
            "questions_served": qs_str,
            "provenance_sql": "",
        })

        # Scanned PDF if exists
        if item["has_scanned"]:
            scan_path = SCANNED_DIR / f"{base}.pdf"
            assert scan_path.exists(), f"Missing scanned pdf: {scan_path}"
            entries.append({
                "doc_id": f"DOC-RB-{id_suffix}-SCAN",
                "title": f"{title} (Archival Scanned Edition)",
                "doc_type": "rulebook",
                "issuer": "Corporate HR Administration",
                "effective_date": eff_date,
                "confidentiality": "internal",
                "audience_roles": "all",
                "source": "reconstruction",
                "format": "scanned_pdf",
                "path": f"landing/documents/scanned/{base}.pdf",
                "pages": pdf_pages,
                "linked_entity_ids": "",
                "questions_served": qs_str,
                "provenance_sql": "",
            })

    # Clause Index CSV
    assert clause_index_path.exists(), f"Missing clause index: {clause_index_path}"
    entries.append({
        "doc_id": "DOC-RB-CLAUSE-INDEX",
        "title": "ONGC Internal Rulebooks - Master Clause & Section Index",
        "doc_type": "clause_index",
        "issuer": "Corporate HR Administration & Legal",
        "effective_date": "2026-10-19",
        "confidentiality": "internal",
        "audience_roles": "all",
        "source": "reconstruction",
        "format": "csv",
        "path": "landing/documents/rulebooks_clause_index.csv",
        "pages": 1,
        "linked_entity_ids": "",
        "questions_served": "E2; P1; P2; P3; P4; P5; P11; D5; H5_FU3; H10; T2_FU2",
        "provenance_sql": "",
    })

    return entries


def build_78_public_policy_entries() -> List[Dict[str, Any]]:
    """Build manifest entries for the 78 authentic public policy raw files."""
    assert POLICIES_RAW_DIR.exists(), f"Missing raw policies dir: {POLICIES_RAW_DIR}"
    assert POLICY_MAP_PATH.exists(), f"Missing policy map: {POLICY_MAP_PATH}"

    with open(POLICY_MAP_PATH, "r", encoding="utf-8") as f:
        policy_data = yaml.safe_load(f)

    # Build question mapping for docs
    doc_q_map: Dict[str, Set[str]] = {}
    for q_item in policy_data.get("question_map", []):
        qid = q_item.get("id", "")
        for d_id in q_item.get("doc_ids", []):
            doc_q_map.setdefault(d_id, set()).add(qid)

    # Map raw files to doc metadata
    raw_files = sorted(os.listdir(POLICIES_RAW_DIR))
    assert len(raw_files) == 78, f"Expected 78 raw policy files, found {len(raw_files)}"

    docs_metadata = policy_data.get("documents", [])
    doc_by_raw_fname = {}
    for d in docs_metadata:
        rp = d.get("raw_path")
        if rp:
            doc_by_raw_fname[os.path.basename(str(rp))] = d
        else:
            tp = d.get("text_path", "")
            base = os.path.splitext(os.path.basename(tp))[0]
            doc_by_raw_fname[f"{base}.html"] = d

    entries = []
    for rf in raw_files:
        assert rf in doc_by_raw_fname, f"Raw policy file {rf} missing metadata in policy_question_map.yaml"
        meta = doc_by_raw_fname[rf]

        d_id = meta["doc_id"]
        title = meta.get("title", rf)
        issuer = meta.get("issuer", "Government of India / ONGC")
        year = str(meta.get("year", "2024"))
        eff_date = f"{year}-01-01" if len(year) == 4 else year
        conf = "public"
        roles = "all"
        src = "public"
        fmt = "html" if rf.endswith(".html") else "pdf"
        rel_path = f"knowledge/public_sources/policies/raw/{rf}"
        actual_path = POLICIES_RAW_DIR / rf

        if fmt == "pdf":
            pages_cnt = get_pdf_page_count(actual_path)
        else:
            pages_cnt = 1

        qs = doc_q_map.get(d_id, set())
        qs_str = "; ".join(sorted(qs)) if qs else "P1-P20"

        doc_type = "court_judgment" if d_id.startswith("J-") else "policy"

        entry = {
            "doc_id": d_id,
            "title": title,
            "doc_type": doc_type,
            "issuer": issuer,
            "effective_date": eff_date,
            "confidentiality": conf,
            "audience_roles": roles,
            "source": src,
            "format": fmt,
            "path": rel_path,
            "pages": pages_cnt,
            "linked_entity_ids": "",
            "questions_served": qs_str,
            "provenance_sql": "",
        }
        entries.append(entry)

    return entries


def main() -> None:
    """Unify all document records into landing/documents/DOC_MANIFEST.csv."""
    print("Building 3x entries...")
    entries_3x = build_3x_entries()
    print(f"  3x entries: {len(entries_3x)}")

    print("Building 34_37 entries...")
    entries_34_37 = build_34_37_entries()
    print(f"  34_37 entries: {len(entries_34_37)}")

    print("Building 3.1 rulebook entries...")
    entries_31 = build_31_rulebook_entries()
    print(f"  3.1 rulebook entries: {len(entries_31)}")

    print("Building 78 public policy entries...")
    entries_pub = build_78_public_policy_entries()
    print(f"  Public policy entries: {len(entries_pub)}")

    all_entries = entries_3x + entries_34_37 + entries_31 + entries_pub
    print(f"Total unified entries: {len(all_entries)}")

    df = pd.DataFrame(all_entries)

    # Assert column ordering
    col_order = [
        "doc_id",
        "title",
        "doc_type",
        "issuer",
        "effective_date",
        "confidentiality",
        "audience_roles",
        "source",
        "format",
        "path",
        "pages",
        "linked_entity_ids",
        "questions_served",
        "provenance_sql",
    ]
    df = df[col_order]

    out_csv = DOCS_DIR / "DOC_MANIFEST.csv"
    df.to_csv(out_csv, index=False, encoding="utf-8")
    print(f"Successfully generated {out_csv} ({len(df)} rows)")


if __name__ == "__main__":
    main()
