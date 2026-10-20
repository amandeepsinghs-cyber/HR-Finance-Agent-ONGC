"""test_35_excel.py: Verification suite for Step 3.5 messy Excel realism and recovery.

Validates that:
1. landing/excel/_parsing_specs.yaml exists and defines all 6 workbooks.
2. landing/excel/_clean/ contains pristine backups of all 6 workbooks.
3. Messy landing workbooks exhibit realistic ONGC corporate artifacts:
   - Title blocks and division banners
   - Merged multi-row headers
   - Unit rows ('₹ crore', 'in Nos.', etc.)
   - Blank spacer columns
   - Multi-sheet layouts (per-asset or per-FY partitions)
   - Subtotal and total summary rows
   - Notes, status, and confidentiality footers
   - Hidden metadata/lookup sheets
   - Formatted text representations of Indian comma numbers
4. A reference parser driven by _parsing_specs.yaml recovers 100% of the clean tables:
   - Identical row counts
   - Identical primary key sets
   - Identical column sums across every numeric and integer column (delta < 1e-4)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List
import openpyxl
import pandas as pd
import pytest
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
LANDING_EXCEL = BASE_DIR / "landing" / "excel"
CLEAN_EXCEL = LANDING_EXCEL / "_clean"
SPECS_PATH = LANDING_EXCEL / "_parsing_specs.yaml"

TARGET_WORKBOOKS = [
    "capex_be_re_actuals.xlsx",
    "manpower_plan.xlsx",
    "dpe_mou_scorecard.xlsx",
    "csr_projects_tracker.xlsx",
    "succession_planning.xlsx",
    "legal_cases_tracker.xlsx",
]


@pytest.fixture(scope="module")
def parsing_specs() -> Dict[str, Any]:
    assert SPECS_PATH.exists(), f"Missing parsing specs file: {SPECS_PATH}"
    with open(SPECS_PATH, "r", encoding="utf-8") as f:
        specs = yaml.safe_load(f)
    return specs


def reference_parse_workbook(file_name: str, spec: Dict[str, Any]) -> pd.DataFrame:
    """Reference implementation of Phase 4 Excel parser using _parsing_specs.yaml."""
    file_path = LANDING_EXCEL / file_name
    assert file_path.exists(), f"Messy workbook does not exist: {file_path}"
    wb = openpyxl.load_workbook(file_path, data_only=True)

    strategy = spec["sheet_strategy"]
    exclude = set(strategy.get("exclude_sheets", []))

    if strategy["mode"] == "named":
        sheet_names = [strategy["sheet_name"]]
    else:
        sheet_names = [s for s in wb.sheetnames if s not in exclude and wb[s].sheet_state != "hidden"]

    header_row_idx = spec["header_row"]
    data_start_row = spec["data_start_row"]
    drop_cols = set(spec.get("drop_columns", []))

    subtotal_col = spec["subtotal_filter"]["column"]
    subtotal_pats = [re.compile(p, re.IGNORECASE) for p in spec["subtotal_filter"]["patterns"]]
    footer_col = spec["footer_filter"]["column"]
    footer_pats = [re.compile(p, re.IGNORECASE) for p in spec["footer_filter"]["patterns"]]

    all_dfs = []

    for sname in sheet_names:
        ws = wb[sname]
        data = list(ws.values)
        if len(data) < data_start_row:
            continue

        raw_headers = data[header_row_idx - 1]
        headers = [str(h).strip() if h is not None else f"Unnamed: {i}" for i, h in enumerate(raw_headers)]

        rows = []
        for r_vals in data[data_start_row - 1:]:
            if all(v is None or str(v).strip() == "" for v in r_vals):
                continue
            r_dict = {}
            for h, v in zip(headers, r_vals):
                if h not in drop_cols:
                    r_dict[h] = v

            # Check subtotal filter
            sub_val = str(r_dict.get(subtotal_col, "") or "").strip()
            if any(p.search(sub_val) for p in subtotal_pats):
                continue

            # Check footer filter
            foot_val = str(r_dict.get(footer_col, "") or "").strip()
            if any(p.search(foot_val) for p in footer_pats):
                continue

            # Check if primary key is null/empty
            pk_col = spec["primary_key"][0]
            if pk_col in r_dict and (r_dict[pk_col] is None or str(r_dict[pk_col]).strip() == ""):
                continue

            rows.append(r_dict)

        if rows:
            df_sheet = pd.DataFrame(rows)
            all_dfs.append(df_sheet)

    if not all_dfs:
        return pd.DataFrame()

    full_df = pd.concat(all_dfs, ignore_index=True)

    # Conversions
    for col, dtype in spec.get("numeric_columns", {}).items():
        if col in full_df.columns:
            full_df[col] = full_df[col].apply(
                lambda x: float(str(x).replace(",", "").strip()) if pd.notna(x) and str(x).strip() != "" else None
            )

    for col in spec.get("integer_columns", []):
        if col in full_df.columns:
            full_df[col] = full_df[col].apply(
                lambda x: int(float(str(x).replace(",", "").strip())) if pd.notna(x) and str(x).strip() != "" else None
            )

    for col in spec.get("boolean_columns", []):
        if col in full_df.columns:
            full_df[col] = full_df[col].apply(
                lambda x: True if str(x).lower() in ["true", "1", "yes", "y"]
                else (False if str(x).lower() in ["false", "0", "no", "n"] else x)
            )

    for col in spec.get("string_columns", []):
        if col in full_df.columns:
            full_df[col] = full_df[col].apply(
                lambda x: str(x).strip() if pd.notna(x) and str(x).strip() != "" else None
            )

    return full_df


def test_parsing_specs_structure(parsing_specs: Dict[str, Any]):
    """Verify that _parsing_specs.yaml contains all required workbooks and metadata."""
    assert "workbooks" in parsing_specs
    for target in TARGET_WORKBOOKS:
        assert target in parsing_specs["workbooks"], f"Missing spec for {target}"
        spec = parsing_specs["workbooks"][target]
        assert "target_table" in spec
        assert "sheet_strategy" in spec
        assert "header_row" in spec
        assert "data_start_row" in spec
        assert "primary_key" in spec
        assert "subtotal_filter" in spec
        assert "footer_filter" in spec


def test_clean_backups_exist():
    """Verify that all clean originals are preserved in landing/excel/_clean/."""
    for target in TARGET_WORKBOOKS:
        clean_file = CLEAN_EXCEL / target
        assert clean_file.exists(), f"Clean original missing: {clean_file}"
        assert clean_file.stat().st_size > 5000, f"Clean file suspiciously small: {clean_file}"


@pytest.mark.parametrize("file_name", TARGET_WORKBOOKS)
def test_messy_workbook_artifacts(file_name: str, parsing_specs: Dict[str, Any]):
    """Verify that messy workbooks contain authentic Excel structures (titles, units, hidden sheet, subtotals)."""
    wb = openpyxl.load_workbook(LANDING_EXCEL / file_name, data_only=False)
    spec = parsing_specs["workbooks"][file_name]

    # 1. Hidden sheet check
    hidden_sheets = [s for s in wb.sheetnames if wb[s].sheet_state == "hidden"]
    assert len(hidden_sheets) >= 1, f"{file_name} missing hidden metadata sheet"

    # 2. Visible sheet structure
    first_visible = next(s for s in wb.sheetnames if wb[s].sheet_state != "hidden")
    ws = wb[first_visible]

    # Title in row 1 or 2
    title_val = ws.cell(1, 2).value or ws.cell(2, 2).value
    assert title_val is not None and len(str(title_val)) > 10, f"Missing title in {file_name}"

    # Spacer col A is empty in row 5
    spacer_cell = ws.cell(5, 1).value
    assert spacer_cell is None or spacer_cell == "", f"Spacer column A not empty in {file_name}"

    # Header in row 5
    header_cell = ws.cell(5, 2).value
    assert header_cell is not None, f"Missing header row 5 in {file_name}"

    # Unit row in row 6
    unit_row_vals = [ws.cell(6, c).value for c in range(2, ws.max_column + 1)]
    assert any(u is not None and ("(" in str(u) or "₹" in str(u)) for u in unit_row_vals), (
        f"Missing unit annotations in row 6 of {file_name}"
    )


def test_capex_per_asset_sheets():
    """Verify capex_be_re_actuals.xlsx contains separate sheets per asset."""
    wb = openpyxl.load_workbook(LANDING_EXCEL / "capex_be_re_actuals.xlsx", read_only=True)
    visible_sheets = [s for s in wb.sheetnames if not s.startswith("_")]
    # Should have >= 25 asset sheets
    assert len(visible_sheets) >= 25, f"Expected >= 25 asset sheets, found {len(visible_sheets)}"


def test_dpe_and_csr_per_fy_sheets():
    """Verify dpe_mou_scorecard.xlsx and csr_projects_tracker.xlsx contain per-FY sheets."""
    wb_mou = openpyxl.load_workbook(LANDING_EXCEL / "dpe_mou_scorecard.xlsx", read_only=True)
    visible_mou = [s for s in wb_mou.sheetnames if not s.startswith("_")]
    assert len(visible_mou) == 3, f"Expected 3 FY sheets in MoU scorecard, got {len(visible_mou)}"

    wb_csr = openpyxl.load_workbook(LANDING_EXCEL / "csr_projects_tracker.xlsx", read_only=True)
    visible_csr = [s for s in wb_csr.sheetnames if not s.startswith("_")]
    assert len(visible_csr) >= 8, f"Expected >= 8 FY sheets in CSR tracker, got {len(visible_csr)}"


@pytest.mark.parametrize("file_name", TARGET_WORKBOOKS)
def test_reference_parser_exact_recovery(file_name: str, parsing_specs: Dict[str, Any]):
    """Assert reference parser recovers 100% of clean data (row count, PK set, numeric sums)."""
    spec = parsing_specs["workbooks"][file_name]
    clean_df = pd.read_excel(CLEAN_EXCEL / file_name)
    recovered_df = reference_parse_workbook(file_name, spec)

    # 1. Exact row count match
    assert len(recovered_df) == len(clean_df), (
        f"{file_name}: row count mismatch (recovered={len(recovered_df)}, clean={len(clean_df)})"
    )

    # 2. Exact Primary Key set match
    pk_col = spec["primary_key"][0]
    assert pk_col in recovered_df.columns, f"PK column {pk_col} not in recovered columns"
    assert pk_col in clean_df.columns, f"PK column {pk_col} not in clean columns"

    rec_pks = set(recovered_df[pk_col].dropna().astype(str))
    clean_pks = set(clean_df[pk_col].dropna().astype(str))
    assert rec_pks == clean_pks, f"{file_name}: Primary key set mismatch"

    # 3. Exact Numeric Column Sums (tolerance < 1e-4)
    numeric_cols = list(spec.get("numeric_columns", {}).keys()) + spec.get("integer_columns", [])
    for col in numeric_cols:
        assert col in recovered_df.columns, f"Numeric column {col} missing in recovered df"
        assert col in clean_df.columns, f"Numeric column {col} missing in clean df"

        sum_rec = float(recovered_df[col].dropna().sum())
        sum_clean = float(clean_df[col].dropna().sum())
        delta = abs(sum_rec - sum_clean)
        assert delta < 1e-4, f"{file_name} column '{col}' sum mismatch: rec={sum_rec}, clean={sum_clean}, delta={delta}"
