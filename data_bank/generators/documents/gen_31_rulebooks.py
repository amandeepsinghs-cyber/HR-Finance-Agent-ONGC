"""Main generator for Step 3.1: Demo reconstructions of ONGC internal rulebooks.

Generates:
- 7 native DOCX rulebooks under landing/documents/native/
- 7 native PDF rulebooks under landing/documents/native/ (each 8-40 pages, watermarked)
- 3 scanned image-only PDFs under landing/documents/scanned/ (JRTP, BDP, Leave Rules)
- 1 consolidated clause index CSV under landing/documents/rulebooks_clause_index.csv

Usage:
    uv run python generators/documents/gen_31_rulebooks.py
"""

import csv
import hashlib
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

DATA_BANK_ROOT = Path(__file__).resolve().parent.parent.parent
if str(DATA_BANK_ROOT) not in sys.path:
    sys.path.insert(0, str(DATA_BANK_ROOT))

import pypdf

from generators.documents.rulebook_data import get_all_rulebooks
from generators.documents.renderers import render_docx, render_pdf, render_scanned_pdf

DATA_BANK_ROOT = Path(__file__).resolve().parent.parent.parent
NATIVE_DIR = DATA_BANK_ROOT / "landing" / "documents" / "native"
SCANNED_DIR = DATA_BANK_ROOT / "landing" / "documents" / "scanned"
CLAUSE_INDEX_PATH = DATA_BANK_ROOT / "landing" / "documents" / "rulebooks_clause_index.csv"

RULEBOOK_FILENAMES = {
    "JRTP": "ongc_job_rotation_transfer_policy_jrtp",
    "BDP summary": "ongc_book_of_delegated_powers_bdp_summary",
    "Leave Rules": "ongc_leave_rules_1995",
    "R&P/Promotion": "ongc_modified_recruitment_and_promotion_regulations",
    "HR Manual": "ongc_hr_manual_designations_pay_scales_service_conditions",
    "PRBS": "ongc_prbs_superannuation_benefit_scheme_rules",
    "Post-retirement medical": "ongc_post_retirement_medical_benefit_scheme",
}

SCANNED_RULEBOOKS = ["JRTP", "BDP summary", "Leave Rules"]


def compute_sha256(path: Path) -> str:
    """Computes SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def generate_clause_index(rulebooks: List, output_csv: Path) -> List[Dict]:
    """Generates the consolidated rulebooks_clause_index.csv."""
    rows = []
    for rb in rulebooks:
        for ch in rb.chapters:
            for cl in ch.clauses:
                # Combine plain text of clause and subclauses
                full_text_parts = [cl.clause_text]
                for sc in cl.subclauses:
                    full_text_parts.append(f"({sc.ref}) {sc.title}: {sc.text}")
                plain_text = " ".join(full_text_parts).replace("\n", " ").strip()

                rows.append({
                    "doc_id": rb.doc_id,
                    "clause_ref": cl.clause_ref,
                    "clause_title": cl.clause_title,
                    "clause_text": plain_text,
                    "maps_to_question_ids": cl.maps_to_question_ids,
                    "source_basis": cl.source_basis
                })

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["doc_id", "clause_ref", "clause_title", "clause_text", "maps_to_question_ids", "source_basis"]
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return rows


def main():
    start_time = time.time()
    print("=" * 80)
    print("STEP 3.1: DEMO RECONSTRUCTIONS OF ONGC INTERNAL RULEBOOKS")
    print("=" * 80)

    NATIVE_DIR.mkdir(parents=True, exist_ok=True)
    SCANNED_DIR.mkdir(parents=True, exist_ok=True)

    rulebooks = get_all_rulebooks()
    print(f"Loaded {len(rulebooks)} formal ONGC rulebook specifications.")

    results_summary = []

    # 1. Render Native DOCX & PDF
    for rb in rulebooks:
        base_name = RULEBOOK_FILENAMES[rb.doc_id]
        docx_path = NATIVE_DIR / f"{base_name}.docx"
        pdf_path = NATIVE_DIR / f"{base_name}.pdf"

        print(f"\n[+] Generating {rb.doc_id} -> {base_name}...")
        render_docx(rb, docx_path)
        print(f"    - DOCX saved: {docx_path.name} ({docx_path.stat().st_size:,} bytes)")

        num_pages = render_pdf(rb, pdf_path)
        print(f"    - PDF saved:  {pdf_path.name} ({num_pages} pages, {pdf_path.stat().st_size:,} bytes)")

        assert 8 <= num_pages <= 40, f"Page count out of range (8-40) for {rb.doc_id}: {num_pages} pages"

        results_summary.append({
            "doc_id": rb.doc_id,
            "format": "native_pdf",
            "file": pdf_path.name,
            "path": pdf_path,
            "pages": num_pages,
            "size": pdf_path.stat().st_size,
            "sha256": compute_sha256(pdf_path)
        })
        results_summary.append({
            "doc_id": rb.doc_id,
            "format": "native_docx",
            "file": docx_path.name,
            "path": docx_path,
            "pages": "n/a",
            "size": docx_path.stat().st_size,
            "sha256": compute_sha256(docx_path)
        })

    # 2. Render Scanned image-only PDFs
    print("\n" + "-" * 80)
    print("RENDERING SCANNED IMAGE-ONLY PDFS (NO TEXT LAYER)")
    print("-" * 80)
    for doc_id in SCANNED_RULEBOOKS:
        base_name = RULEBOOK_FILENAMES[doc_id]
        native_pdf = NATIVE_DIR / f"{base_name}.pdf"
        scanned_pdf = SCANNED_DIR / f"{base_name}.pdf"

        print(f"[+] Rasterizing {doc_id} to scanned PDF -> {scanned_pdf.name}...")
        scanned_pages = render_scanned_pdf(native_pdf, scanned_pdf)
        print(f"    - Scanned PDF saved: {scanned_pdf.name} ({scanned_pages} pages, {scanned_pdf.stat().st_size:,} bytes)")

        results_summary.append({
            "doc_id": doc_id,
            "format": "scanned_pdf",
            "file": scanned_pdf.name,
            "path": scanned_pdf,
            "pages": scanned_pages,
            "size": scanned_pdf.stat().st_size,
            "sha256": compute_sha256(scanned_pdf)
        })

    # 3. Generate Clause Index CSV
    print("\n" + "-" * 80)
    print("GENERATING RULEBOOKS CLAUSE INDEX CSV")
    print("-" * 80)
    index_rows = generate_clause_index(rulebooks, CLAUSE_INDEX_PATH)
    index_sha = compute_sha256(CLAUSE_INDEX_PATH)
    print(f"[+] Wrote {len(index_rows)} clauses to {CLAUSE_INDEX_PATH.name} (SHA-256: {index_sha[:16]}...)")

    elapsed = time.time() - start_time
    print("\n" + "=" * 80)
    print(f"GENERATION COMPLETED SUCCESSFULLY IN {elapsed:.2f}s")
    print("=" * 80)

    # Print summary table
    print(f"{'Doc ID':<25} | {'Format':<12} | {'Pages':<6} | {'Size (KB)':<10} | {'SHA-256 (16 chars)':<18}")
    print("-" * 80)
    for r in results_summary:
        sz_kb = f"{r['size'] / 1024:.1f}"
        print(f"{r['doc_id']:<25} | {r['format']:<12} | {str(r['pages']):<6} | {sz_kb:<10} | {r['sha256'][:16]:<18}")
    print(f"{'Clause Index CSV':<25} | {'csv':<12} | {len(index_rows):<6} | {CLAUSE_INDEX_PATH.stat().st_size / 1024:.1f}      | {index_sha[:16]:<18}")


if __name__ == "__main__":
    main()
