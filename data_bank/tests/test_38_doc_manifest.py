"""test_38_doc_manifest.py: Verification suite for unified document manifest (Step 3.8).

Validates that:
1. landing/documents/DOC_MANIFEST.csv exists, is non-empty, and has all 14 required columns.
2. Every file under landing/documents (excluding _provenance and DOC_MANIFEST*.csv) is listed exactly once.
3. Every real policy raw file under knowledge/public_sources/policies/raw/ is listed exactly once.
4. Total documents = 658 (580 landing + 78 real public policies).
5. All file paths listed in the manifest exist on disk.
6. All required columns are non-empty across all rows.
7. doc_id is globally unique across the manifest.
8. Confidentiality and audience RBAC rules are consistent:
   - strictly_confidential documents NEVER have audience_roles == 'all' or contain 'all'.
   - confidentiality is in {'public', 'internal', 'confidential', 'strictly_confidential'}.
   - source is in {'public', 'reconstruction', 'synthetic'}.
   - format is in {'pdf', 'docx', 'scanned_pdf', 'html', 'xlsx', 'csv'}.
9. Synthetic documents have existing provenance SQL scripts where referenced.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List, Set
import pandas as pd
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BASE_DIR.parent
DOCS_DIR = BASE_DIR / "landing" / "documents"
MANIFEST_PATH = DOCS_DIR / "DOC_MANIFEST.csv"
POLICIES_RAW_DIR = PROJECT_DIR / "knowledge" / "public_sources" / "policies" / "raw"

REQUIRED_COLUMNS = [
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

NON_EMPTY_REQUIRED_COLUMNS = [
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
]


@pytest.fixture(scope="module")
def manifest_df() -> pd.DataFrame:
    """Load and return the unified DOC_MANIFEST.csv."""
    assert MANIFEST_PATH.exists(), f"Missing unified manifest: {MANIFEST_PATH}"
    df = pd.read_csv(MANIFEST_PATH, dtype=str)
    return df


def test_manifest_columns_and_non_empty(manifest_df: pd.DataFrame):
    """Verify all 14 required columns exist and required metadata columns are non-empty."""
    for col in REQUIRED_COLUMNS:
        assert col in manifest_df.columns, f"Missing required column in manifest: {col}"

    assert len(manifest_df) == 658, f"Expected 658 total documents, got {len(manifest_df)}"

    for col in NON_EMPTY_REQUIRED_COLUMNS:
        null_count = manifest_df[col].isna().sum()
        empty_count = (manifest_df[col].astype(str).str.strip() == "").sum()
        assert null_count == 0, f"Column {col} has {null_count} nulls"
        assert empty_count == 0, f"Column {col} has {empty_count} empty strings"


def test_doc_id_unique(manifest_df: pd.DataFrame):
    """Verify doc_id is globally unique across the unified manifest."""
    assert manifest_df["doc_id"].is_unique, "Duplicate doc_id values detected in DOC_MANIFEST.csv"
    duplicates = manifest_df[manifest_df["doc_id"].duplicated(keep=False)]["doc_id"].tolist()
    assert len(duplicates) == 0, f"Duplicates: {duplicates}"


def test_all_disk_files_listed_exactly_once(manifest_df: pd.DataFrame):
    """Verify every landing doc file (excluding _provenance/manifests) and raw policy file is listed exactly once."""
    # 1. Gather all document files on disk under landing/documents
    landing_doc_files: Set[str] = set()
    for root, dirs, files in os.walk(DOCS_DIR):
        if "_provenance" in root:
            continue
        for f in files:
            if f.startswith("DOC_MANIFEST"):
                continue
            rel = os.path.relpath(os.path.join(root, f), BASE_DIR)
            landing_doc_files.add(rel)

    assert len(landing_doc_files) == 580, f"Expected 580 landing document files, found {len(landing_doc_files)}"

    # 2. Gather all raw policy files
    assert POLICIES_RAW_DIR.exists(), f"Missing {POLICIES_RAW_DIR}"
    raw_policy_files = {f"knowledge/public_sources/policies/raw/{f}" for f in os.listdir(POLICIES_RAW_DIR)}
    assert len(raw_policy_files) == 78, f"Expected 78 raw policy files, found {len(raw_policy_files)}"

    expected_files = landing_doc_files.union(raw_policy_files)
    assert len(expected_files) == 658, f"Expected 658 unique files across landing and policies, found {len(expected_files)}"

    # 3. Check manifest paths
    manifest_paths = set(manifest_df["path"])
    assert len(manifest_paths) == len(manifest_df), "Duplicate path values found in DOC_MANIFEST.csv"

    missing_in_manifest = expected_files - manifest_paths
    assert len(missing_in_manifest) == 0, f"Files missing in manifest ({len(missing_in_manifest)}): {list(missing_in_manifest)[:5]}"

    extra_in_manifest = manifest_paths - expected_files
    assert len(extra_in_manifest) == 0, f"Extra files in manifest ({len(extra_in_manifest)}): {list(extra_in_manifest)[:5]}"


def test_all_manifest_paths_exist_on_disk(manifest_df: pd.DataFrame):
    """Verify every path in DOC_MANIFEST.csv resolves to an existing file on disk."""
    for _, row in manifest_df.iterrows():
        p_str = row["path"]
        p_landing = BASE_DIR / p_str
        p_project = PROJECT_DIR / p_str
        assert p_landing.exists() or p_project.exists(), f"Path in manifest does not exist: {p_str}"


def test_confidentiality_and_audience_consistency(manifest_df: pd.DataFrame):
    """Verify RBAC audience consistency: strictly_confidential must NEVER be audience 'all'."""
    allowed_conf = {"public", "internal", "confidential", "strictly_confidential"}
    actual_conf = set(manifest_df["confidentiality"].unique())
    assert actual_conf.issubset(allowed_conf), f"Invalid confidentiality values: {actual_conf - allowed_conf}"

    # strictly_confidential check
    strict_docs = manifest_df[manifest_df["confidentiality"] == "strictly_confidential"]
    assert len(strict_docs) > 0, "Expected at least 1 strictly_confidential document"
    for _, row in strict_docs.iterrows():
        roles = str(row["audience_roles"]).lower()
        assert not re.search(r"\ball\b", roles), (
            f"Doc {row['doc_id']} is strictly_confidential but includes 'all' in audience_roles: {row['audience_roles']}"
        )

    # confidential check
    conf_docs = manifest_df[manifest_df["confidentiality"] == "confidential"]
    for _, row in conf_docs.iterrows():
        roles = str(row["audience_roles"]).lower()
        assert not re.search(r"\ball\b", roles), (
            f"Doc {row['doc_id']} is confidential but includes 'all' in audience_roles: {row['audience_roles']}"
        )


def test_enums_valid(manifest_df: pd.DataFrame):
    """Verify source and format enums match allowed values."""
    allowed_sources = {"public", "reconstruction", "synthetic"}
    actual_sources = set(manifest_df["source"].unique())
    assert actual_sources.issubset(allowed_sources), f"Invalid sources: {actual_sources - allowed_sources}"

    allowed_formats = {"pdf", "docx", "scanned_pdf", "html", "xlsx", "csv"}
    actual_formats = set(manifest_df["format"].unique())
    assert actual_formats.issubset(allowed_formats), f"Invalid formats: {actual_formats - allowed_formats}"


def test_provenance_sql_exists_for_synthetic_docs(manifest_df: pd.DataFrame):
    """Verify that synthetic documents referencing provenance SQL actually exist on disk."""
    synth_docs = manifest_df[manifest_df["source"] == "synthetic"]
    assert len(synth_docs) > 0
    for _, row in synth_docs.iterrows():
        sql_ref = str(row.get("provenance_sql", "") or "").strip()
        if sql_ref and sql_ref.lower() != "nan":
            sql_path = BASE_DIR / sql_ref
            assert sql_path.exists(), f"Referenced provenance SQL does not exist: {sql_path} (for doc {row['doc_id']})"
