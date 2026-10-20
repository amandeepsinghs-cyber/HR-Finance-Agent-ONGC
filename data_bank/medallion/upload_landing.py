#!/usr/bin/env python3
"""medallion/upload_landing.py: Upload landing files to GCS and produce upload_manifest.csv (Step 4.1).

Uploads:
1. gs://ongc-hr-finance-agent-landing/{source}/{batch_date}/...
   - landing/sap/ -> sap/20261019/...
   - landing/db_exports/ -> db_exports/20261019/...
   - landing/excel/ (excluding _clean/) -> excel/20261019/...
   - landing/governance/ -> governance/20261019/...
2. gs://ongc-hr-finance-agent-landing/_provenance/...
   - landing/documents/_provenance/** -> _provenance/...
3. gs://ongc-hr-finance-agent-docs/...
   - landing/documents/** (excluding _provenance/) -> {relpath}
   - knowledge/public_sources/policies/raw/* -> public_policies/{filename}

Writes:
- medallion/upload_manifest.csv (local_path,gs_uri,size,md5)
Verifies:
- Object count and MD5 equality against GCS.
"""

from __future__ import annotations

import base64
import csv
import hashlib
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Tuple

from google.cloud import storage

PROJECT_ID = "ongc-hr-finance-agent"
LANDING_BUCKET_NAME = "ongc-hr-finance-agent-landing"
DOCS_BUCKET_NAME = "ongc-hr-finance-agent-docs"
BATCH_DATE = "20261019"

# Non-canonical duplicate sources in landing/ (generator bug; dropped per Lead instructions)
NON_CANONICAL_DUPLICATES = {
    "landing/db_exports/corporate_financial_summary.csv",
    "landing/db_exports/subsidiary_group_financials.csv",
    "landing/governance/rti_applications_export.csv",
}

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent
MANIFEST_PATH = BASE_DIR / "medallion" / "upload_manifest.csv"


def calculate_md5_and_size(file_path: Path) -> Tuple[str, int]:
    """Calculate MD5 (hex) and byte size of a local file."""
    h = hashlib.md5()
    size = 0
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
            size += len(chunk)
    return h.hexdigest(), size


def collect_upload_items() -> List[Dict[str, str | int]]:
    """Scan local directory structure and determine GCS target URIs."""
    items: List[Dict[str, str | int]] = []

    # 1. Structured sources in landing/ -> landing bucket
    for src in ["sap", "db_exports", "excel", "governance"]:
        src_dir = BASE_DIR / "landing" / src
        if not src_dir.exists():
            continue
        for root, dirs, files in os.walk(src_dir):
            if src == "excel" and "_clean" in root:
                continue
            for f in files:
                p = Path(root) / f
                rel_to_base = p.relative_to(BASE_DIR)
                if str(rel_to_base) in NON_CANONICAL_DUPLICATES:
                    continue
                rel_to_src = p.relative_to(src_dir)
                gs_uri = f"gs://{LANDING_BUCKET_NAME}/{src}/{BATCH_DATE}/{rel_to_src}"
                items.append({
                    "local_path": str(rel_to_base),
                    "full_path": str(p),
                    "bucket": LANDING_BUCKET_NAME,
                    "blob_name": f"{src}/{BATCH_DATE}/{rel_to_src}",
                    "gs_uri": gs_uri,
                })

    # 2. Provenance -> landing bucket _provenance/
    prov_dir = BASE_DIR / "landing" / "documents" / "_provenance"
    if prov_dir.exists():
        for root, dirs, files in os.walk(prov_dir):
            for f in files:
                p = Path(root) / f
                rel_to_prov = p.relative_to(prov_dir)
                gs_uri = f"gs://{LANDING_BUCKET_NAME}/_provenance/{rel_to_prov}"
                rel_to_base = p.relative_to(BASE_DIR)
                items.append({
                    "local_path": str(rel_to_base),
                    "full_path": str(p),
                    "bucket": LANDING_BUCKET_NAME,
                    "blob_name": f"_provenance/{rel_to_prov}",
                    "gs_uri": gs_uri,
                })

    # 3. Documents (native, scanned, templates, root docs files) -> docs bucket
    docs_dir = BASE_DIR / "landing" / "documents"
    if docs_dir.exists():
        for root, dirs, files in os.walk(docs_dir):
            if "_provenance" in root:
                continue
            for f in files:
                p = Path(root) / f
                rel_to_docs = p.relative_to(docs_dir)
                gs_uri = f"gs://{DOCS_BUCKET_NAME}/{rel_to_docs}"
                rel_to_base = p.relative_to(BASE_DIR)
                items.append({
                    "local_path": str(rel_to_base),
                    "full_path": str(p),
                    "bucket": DOCS_BUCKET_NAME,
                    "blob_name": str(rel_to_docs),
                    "gs_uri": gs_uri,
                })

    # 4. Public policy raw files -> docs bucket public_policies/
    pub_dir = PROJECT_ROOT / "knowledge" / "public_sources" / "policies" / "raw"
    if not pub_dir.exists():
        pub_dir = BASE_DIR / "knowledge" / "public_sources" / "policies" / "raw"
    if pub_dir.exists():
        for f in os.listdir(pub_dir):
            p = pub_dir / f
            if p.is_file():
                gs_uri = f"gs://{DOCS_BUCKET_NAME}/public_policies/{f}"
                try:
                    rel_to_base = p.relative_to(BASE_DIR)
                except ValueError:
                    rel_to_base = Path("..") / p.relative_to(PROJECT_ROOT)
                items.append({
                    "local_path": str(rel_to_base),
                    "full_path": str(p),
                    "bucket": DOCS_BUCKET_NAME,
                    "blob_name": f"public_policies/{f}",
                    "gs_uri": gs_uri,
                })

    return items


def upload_single_item(client: storage.Client, item: Dict[str, str | int]) -> Dict[str, Any]:
    """Upload a single file to GCS and verify MD5."""
    bucket = client.bucket(item["bucket"])
    blob = bucket.blob(item["blob_name"])

    local_path = Path(item["full_path"])
    md5_hex, size = calculate_md5_and_size(local_path)
    item["size"] = size
    item["md5"] = md5_hex

    # Check if already exists with matching MD5
    if blob.exists():
        blob.reload()
        remote_md5 = base64.b64decode(blob.md5_hash).hex()
        if remote_md5 == md5_hex and blob.size == size:
            return {"status": "skipped", "item": item, "error": None}

    # Upload
    blob.upload_from_filename(str(local_path))
    blob.reload()
    remote_md5 = base64.b64decode(blob.md5_hash).hex()

    if remote_md5 != md5_hex or blob.size != size:
        return {
            "status": "failed",
            "item": item,
            "error": f"MD5/Size mismatch: remote={remote_md5}/{blob.size} vs local={md5_hex}/{size}",
        }

    return {"status": "uploaded", "item": item, "error": None}


def main():
    print(f"[{time.strftime('%X')}] Collecting items for GCS upload...")
    items = collect_upload_items()
    print(f"Total files identified: {len(items)}")

    # Group by bucket
    landing_items = [it for it in items if it["bucket"] == LANDING_BUCKET_NAME]
    docs_items = [it for it in items if it["bucket"] == DOCS_BUCKET_NAME]
    print(f"  - Landing bucket ({LANDING_BUCKET_NAME}): {len(landing_items)} files")
    print(f"  - Docs bucket ({DOCS_BUCKET_NAME}): {len(docs_items)} files")

    client = storage.Client(project=PROJECT_ID)
    start_time = time.time()

    print(f"[{time.strftime('%X')}] Starting concurrent upload (16 workers)...")
    results = []
    failed_count = 0
    uploaded_count = 0
    skipped_count = 0

    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = {executor.submit(upload_single_item, client, item): item for item in items}
        for i, future in enumerate(as_completed(futures), start=1):
            res = future.result()
            results.append(res)
            if res["status"] == "failed":
                failed_count += 1
                print(f"ERROR: {res['item']['gs_uri']} failed: {res['error']}")
            elif res["status"] == "uploaded":
                uploaded_count += 1
            else:
                skipped_count += 1
            if i % 200 == 0 or i == len(items):
                print(f"Progress: {i}/{len(items)} processed (uploaded: {uploaded_count}, skipped: {skipped_count}, failed: {failed_count})")

    elapsed = time.time() - start_time
    print(f"[{time.strftime('%X')}] Upload finished in {elapsed:.1f}s. Uploaded: {uploaded_count}, Skipped: {skipped_count}, Failed: {failed_count}")

    if failed_count > 0:
        print("Upload had failures. Aborting manifest write.")
        sys.exit(1)

    # Sort results by local_path for determinism
    items_sorted = sorted(items, key=lambda x: str(x["local_path"]))

    # Write upload_manifest.csv
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["local_path", "gs_uri", "size", "md5"])
        for it in items_sorted:
            writer.writerow([it["local_path"], it["gs_uri"], it["size"], it["md5"]])

    print(f"[{time.strftime('%X')}] Wrote {len(items_sorted)} records to {MANIFEST_PATH}")

    # Full verification check
    print(f"[{time.strftime('%X')}] Verifying all objects in manifest against GCS...")
    verify_client = storage.Client(project=PROJECT_ID)
    landing_bucket = verify_client.bucket(LANDING_BUCKET_NAME)
    docs_bucket = verify_client.bucket(DOCS_BUCKET_NAME)

    landing_blobs = {b.name: b for b in landing_bucket.list_blobs()}
    docs_blobs = {b.name: b for b in docs_bucket.list_blobs()}
    print(f"Total blobs in landing bucket: {len(landing_blobs)}")
    print(f"Total blobs in docs bucket: {len(docs_blobs)}")

    mismatches = []
    for it in items_sorted:
        b_name = str(it["blob_name"])
        bucket_dict = landing_blobs if it["bucket"] == LANDING_BUCKET_NAME else docs_blobs
        if b_name not in bucket_dict:
            mismatches.append(f"Missing in GCS: {it['gs_uri']}")
            continue
        blob = bucket_dict[b_name]
        remote_md5 = base64.b64decode(blob.md5_hash).hex()
        if remote_md5 != it["md5"]:
            mismatches.append(f"MD5 mismatch for {it['gs_uri']}: expected {it['md5']}, got {remote_md5}")
        if blob.size != it["size"]:
            mismatches.append(f"Size mismatch for {it['gs_uri']}: expected {it['size']}, got {blob.size}")

    if mismatches:
        print(f"FAILED: {len(mismatches)} mismatches detected!")
        for m in mismatches[:10]:
            print(" ", m)
        sys.exit(1)

    print(f"SUCCESS: 100% of {len(items_sorted)} objects verified with identical MD5 and size in GCS!")


if __name__ == "__main__":
    main()
