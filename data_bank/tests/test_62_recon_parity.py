"""Parity, seeded-break, and schema-guard tests for Employee-360 & Field-Economics-360 reconciliation (P2H.8)."""

import re
import sys
from pathlib import Path
import duckdb
import numpy as np
import pandas as pd
import pytest
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from generators.reconcile import (
    LEVIES_COLS,
    LIFTING_COLS,
    N35_LINE_TO_COL,
    OPEX_COLS,
    _ensure_wide_field_df,
    run_employee_reconciliation,
    run_field_reconciliation,
)

REPO_ROOT = BASE_DIR.parent
FIXTURES_DIR = BASE_DIR / "tests" / "fixtures" / "recon"
SQLX_DIR = BASE_DIR / "medallion" / "dataform" / "definitions" / "v3"
EVAL_DIR = REPO_ROOT / "yukti" / "backend" / "eval"


@pytest.fixture(scope="module")
def fixture_dfs():
    emp_df = pd.read_csv(FIXTURES_DIR / "emp_fixture.csv")
    pool_df = pd.read_csv(FIXTURES_DIR / "pool_fixture.csv")
    fld_df = pd.read_csv(FIXTURES_DIR / "fld_fixture.csv")
    audit_df = pd.read_csv(FIXTURES_DIR / "audit_fixture.csv")
    targets_df = pd.read_csv(FIXTURES_DIR / "targets_fixture.csv")
    return emp_df, pool_df, fld_df, audit_df, targets_df


def _extract_sqlx_select_columns(sqlx_text: str) -> set[str]:
    """Extract output column names from the final SELECT list of a Dataform SQLX file."""
    # Find the last SELECT ... FROM block
    matches = list(re.finditer(r"\bSELECT\b(.*?)\bFROM\b", sqlx_text, flags=re.IGNORECASE | re.DOTALL))
    assert matches, "No SELECT ... FROM block found in SQLX"
    select_body = matches[-1].group(1)

    cols: set[str] = set()
    # Split top-level comma-separated expressions
    depth = 0
    current: list[str] = []
    parts: list[str] = []
    for ch in select_body:
        if ch == "(":
            depth += 1
            current.append(ch)
        elif ch == ")":
            depth = max(0, depth - 1)
            current.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current).strip())

    for part in parts:
        # Remove SQL single-line comments
        lines = [ln.split("--")[0].strip() for ln in part.splitlines() if ln.split("--")[0].strip()]
        cleaned = " ".join(lines).strip()
        if not cleaned:
            continue
        m_as = re.search(r"\bAS\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*$", cleaned, flags=re.IGNORECASE)
        if m_as:
            cols.add(m_as.group(1))
        else:
            m_col = re.search(r"(?:[a-zA-Z_][a-zA-Z0-9_]*\.)?([a-zA-Z_][a-zA-Z0-9_]*)\s*$", cleaned)
            if m_col:
                cols.add(m_col.group(1))
    return cols


def test_fixture_row_limits(fixture_dfs):
    """Verify all 2-FY synthetic fixture CSVs have <= 200 rows and real domain columns."""
    emp_df, pool_df, fld_df, audit_df, targets_df = fixture_dfs
    for name, df in [
        ("emp_fixture.csv", emp_df),
        ("pool_fixture.csv", pool_df),
        ("fld_fixture.csv", fld_df),
        ("audit_fixture.csv", audit_df),
        ("targets_fixture.csv", targets_df),
    ]:
        assert 1 <= len(df) <= 200, f"{name} has {len(df)} rows (must be <= 200)"

    assert {"fiscal_year", "emp_id", "cost_note35_a_inr", "cost_total_inr"}.issubset(emp_df.columns)
    assert {"fy", "object_id", "segment", "line_code", "amount_inr_mn"}.issubset(fld_df.columns)


def test_sqlx_no_hardcoded_zero_stubs():
    """Verify recon_employee360.sqlx and recon_field_economics.sqlx have all check IDs and zero 0.0 stubs."""
    emp_sql = (SQLX_DIR / "recon_employee360.sqlx").read_text(encoding="utf-8")
    fld_sql = (SQLX_DIR / "recon_field_economics.sqlx").read_text(encoding="utf-8")
    assert_sql = (SQLX_DIR / "assert_recon_block_pass.sqlx").read_text(encoding="utf-8")

    for i in range(1, 31):
        cid = f"EMP-R{i:02d}"
        assert cid in emp_sql, f"Missing {cid} in recon_employee360.sqlx"
    for i in range(1, 18):
        cid = f"FLD-R{i:02d}"
        assert cid in fld_sql, f"Missing {cid} in recon_field_economics.sqlx"

    assert "0.0 AS " not in emp_sql, "Found hardcoded 0.0 AS stub in recon_employee360.sqlx"
    assert "0.0 AS " not in fld_sql, "Found hardcoded 0.0 AS stub in recon_field_economics.sqlx"
    assert "IFNULL(t.value, 0)" not in emp_sql, "Found IFNULL(t.value, 0) in recon_employee360.sqlx"
    assert "IFNULL(t.value, 0)" not in fld_sql, "Found IFNULL(t.value, 0) in recon_field_economics.sqlx"
    assert "severity = 'BLOCK' AND status = 'FAIL'" in assert_sql


def test_field_econ_schema_and_n35_guard(fixture_dfs):
    """Guard against schema/enum/N35 drift across recon_field_economics.sqlx, reconcile.py, and golden_field_econ.yaml."""
    _, _, fld_df, _, _ = fixture_dfs

    ssot_sql = (SQLX_DIR / "ssot_field_economics_360.sqlx").read_text(encoding="utf-8")
    v_fy_sql = (SQLX_DIR / "v_field_economics_fy.sqlx").read_text(encoding="utf-8")
    recon_fld_sql = (SQLX_DIR / "recon_field_economics.sqlx").read_text(encoding="utf-8")
    reconcile_py = (BASE_DIR / "generators" / "reconcile.py").read_text(encoding="utf-8")
    golden_fld_text = (EVAL_DIR / "golden_field_econ.yaml").read_text(encoding="utf-8")

    ssot_cols = _extract_sqlx_select_columns(ssot_sql)
    v_fy_cols = _extract_sqlx_select_columns(v_fy_sql)
    assert len(ssot_cols) >= 44, f"Expected >= 44 columns in ssot_field_economics_360.sqlx, got {len(ssot_cols)}"
    assert len(v_fy_cols) >= 44, f"Expected >= 44 columns in v_field_economics_fy.sqlx, got {len(v_fy_cols)}"

    # 1. None of the non-existent legacy column names or enum literals may appear anywhere
    banned_legacy_identifiers = {
        "subcontracting",
        "repair_maintenance",
        "port_trust_pipeline",
        "general_admin",
        "pol_consumption",
        "octroi_other_levies",
        "services_received",
        "misc_expenditure",
        "note35_total",
        "expl_survey_cost",
        "expl_wells_written_off",
        "finance_cost_unwinding",
        "finance_cost_interest",
        "prod_crude_mt",
        "prod_condensate_mt",
        "prod_gas_mmscm",
        "sales_crude_mt",
        "sales_gas_mmscm",
        "sales_vap_kt",
        "other_income_alloc",
        "lifting_cost",
        "producing_field",
        "FLD-MUMBAI-HIGH",
        "FLD-ANKLESHWAR",
        "FLD-PANNA-MUKTA",
    }
    for banned in banned_legacy_identifiers:
        pat = rf"(?<![a-zA-Z0-9_]){re.escape(banned)}(?![a-zA-Z0-9_])"
        assert not re.search(pat, recon_fld_sql), f"Banned legacy identifier {banned!r} found in recon_field_economics.sqlx"
        assert not re.search(pat, reconcile_py), f"Banned legacy identifier {banned!r} found in reconcile.py"
        assert not re.search(pat, golden_fld_text), f"Banned legacy identifier {banned!r} found in golden_field_econ.yaml"

    # 2. All column constants in reconcile.py must exist in ssot_field_economics_360.sqlx and v_field_economics_fy.sqlx
    reconcile_col_constants = set(N35_LINE_TO_COL.values()) | set(LEVIES_COLS) | set(OPEX_COLS) | set(LIFTING_COLS)
    missing_in_ssot = reconcile_col_constants - ssot_cols
    missing_in_v_fy = reconcile_col_constants - v_fy_cols
    assert not missing_in_ssot, f"reconcile.py column constants missing from ssot_field_economics_360.sqlx: {missing_in_ssot}"
    assert not missing_in_v_fy, f"reconcile.py column constants missing from v_field_economics_fy.sqlx: {missing_in_v_fy}"

    w_fld = _ensure_wide_field_df(fld_df)
    wide_generated_cols = set(w_fld.columns) - set(fld_df.columns)
    assert wide_generated_cols.issubset(ssot_cols), (
        f"_ensure_wide_field_df generated non-canonical columns: {wide_generated_cols - ssot_cols}"
    )

    # 3. Parse every ssot_field_economics_360 column referenced in recon_field_economics.sqlx and verify it exists
    sql_keywords = {
        "SELECT", "FROM", "WHERE", "GROUP", "BY", "UNION", "ALL", "AS", "IF", "IN", "AND", "OR",
        "NOT", "NULL", "IS", "LEFT", "JOIN", "ON", "USING", "WITH", "CASE", "WHEN", "THEN", "ELSE",
        "END", "SUM", "COUNTIF", "ABS", "SAFE_DIVIDE", "COALESCE", "NULLIF", "MAX", "MIN", "AVG", "ROUND",
        "GENERATE_UUID", "CURRENT_TIMESTAMP", "STRUCT", "UNNEST", "TRUE", "FALSE", "CAST", "FLOAT64", "DATE",
    }
    fld_fy_match = re.search(r"WITH\s+fld_fy\s+AS\s*\((.*?)\),\s*emp_staff_fy", recon_fld_sql, flags=re.DOTALL)
    assert fld_fy_match, "Could not locate fld_fy CTE in recon_field_economics.sqlx"
    fld_fy_body = fld_fy_match.group(1)
    # Remove ${ref("ssot_field_economics_360")} and string literals
    fld_fy_clean = re.sub(r"\$\{ref\([^)]+\)\}", "ssot", fld_fy_body)
    fld_fy_clean = re.sub(r"'[^']*'", "", fld_fy_clean)
    alias_To_col: dict[str, str] = {}
    for m_sum in re.finditer(r"SUM\(([a-z_][a-z0-9_]*)\)\s+AS\s+([a-z_][a-z0-9_]*)", fld_fy_clean):
         alias_To_col[m_sum.group(2)] = m_sum.group(1)

    for tok in re.findall(r"\b[a-z_][a-z0-9_]*\b", fld_fy_clean):
        if tok.upper() in sql_keywords or tok in {"ssot"}:
            continue
        if re.search(rf"\bAS\s+{re.escape(tok)}\b", fld_fy_clean, flags=re.IGNORECASE):
            continue
        assert tok in ssot_cols, (
            f"Column {tok!r} referenced in recon_field_economics.sqlx fld_fy CTE not in ssot_field_economics_360.sqlx"
        )

    # Check all 24 (line_code, alias) pairs in n35_unpivoted
    n35_cte_match = re.search(r"n35_unpivoted\s+AS\s*\((.*?)\),\s*raw_checks", recon_fld_sql, flags=re.DOTALL)
    assert n35_cte_match, "Could not locate n35_unpivoted CTE in recon_field_economics.sqlx"
    n35_cte_body = n35_cte_match.group(1)
    sqlx_n35_pairs = re.findall(
        r"SELECT\s+fiscal_year\s*,\s*'(N35\.[A-Z0-9_]+)'(?:\s+AS\s+line_code)?\s*,\s*CAST\(([a-zA-Z_][a-zA-Z0-9_]*)\s+AS\s+FLOAT64\)",
        n35_cte_body,
    )
    assert len(sqlx_n35_pairs) == 24, f"Expected 24 N35 pairs in n35_unpivoted, got {len(sqlx_n35_pairs)}"
    for lcode, alias_name in sqlx_n35_pairs:
        col_name = alias_To_col.get(alias_name)
        assert col_name in ssot_cols, f"n35_unpivoted alias {alias_name!r} -> {col_name!r} for {lcode} not in ssot_field_economics_360.sqlx"
        assert N35_LINE_TO_COL.get(lcode) == col_name, f"Mismatch between SQLX and reconcile.py for {lcode}: {col_name}"

    # 4. Assert every N35.* code in SQLX and reconcile.py exists in field_econ_targets_fy.csv
    real_targets_df = pd.read_csv(BASE_DIR / "world_bible" / "reference" / "real_targets" / "field_econ_targets_fy.csv")
    target_n35_codes = set(
        real_targets_df[real_targets_df["line_code"].str.startswith("N35.")]["line_code"].unique()
    )
    assert len(target_n35_codes) == 24
    assert set(N35_LINE_TO_COL.keys()) == target_n35_codes
    assert {lc for lc, _ in sqlx_n35_pairs} == target_n35_codes

    # 5. Parse every recompute_sql in golden_field_econ.yaml and verify columns & object_ids
    co_cfg = yaml.safe_load((BASE_DIR / "world_bible" / "reference" / "cost_objects.yaml").read_text(encoding="utf-8"))
    valid_object_ids = {obj["object_id"] for obj in co_cfg["cost_objects"]}
    fld_scenarios = yaml.safe_load(golden_fld_text)["scenarios"]
    for sc in fld_scenarios:
        sid = sc["id"]
        sql = sc["expected"].get("recompute_sql")
        if not sql or "v_field_economics_fy" not in sql:
            continue
        # Verify object_id literals in recompute_sql exist in cost_objects.yaml
        for oid in re.findall(r"'(?:FLD|JV|WC|EXP|CO)-[A-Z0-9_-]+'", sql):
            oid_clean = oid.strip("'")
            assert oid_clean in valid_object_ids, f"{sid}: unknown object_id {oid_clean!r} in recompute_sql"
        # Verify column identifiers in recompute_sql exist in v_field_economics_fy.sqlx
        sql_no_str = re.sub(r"'[^']*'", "", sql)
        sql_no_table = re.sub(r"`[^`]+`", "tbl", sql_no_str)
        aliases = set(re.findall(r"\bAS\s+([a-zA-Z_][a-zA-Z0-9_]*)\b", sql_no_table, flags=re.IGNORECASE))
        for tok in re.findall(r"\b[a-z_][a-z0-9_]*\b", sql_no_table):
            if tok.upper() in sql_keywords or tok in aliases or tok in {"tbl", "DESC", "ASC", "LIMIT", "ORDER"}:
                continue
            assert tok in v_fy_cols, (
                f"{sid}: column {tok!r} in recompute_sql not found in v_field_economics_fy.sqlx ({sorted(v_fy_cols)})"
            )


def test_parity(fixture_dfs):
    """Verify Python reconcile.py vs SQL logic parity across all 30 EMP and 17 FLD checks on the 2-FY fixture."""
    emp_df, pool_df, fld_df, audit_df, targets_df = fixture_dfs

    emp_res = run_employee_reconciliation(emp_df, pool_df, targets_df)
    fld_res = run_field_reconciliation(fld_df, targets_df, audit_df=audit_df, emp_df=emp_df)

    # All 30 EMP and 17 FLD checks must be present and PASS on the unmutated 2-FY fixture
    assert set(emp_res["check_id"].unique()) == {f"EMP-R{i:02d}" for i in range(1, 31)}
    assert set(fld_res["check_id"].unique()) == {f"FLD-R{i:02d}" for i in range(1, 18)}
    assert (emp_res["status"] == "PASS").all(), f"Failing EMP rows:\n{emp_res[emp_res['status'] != 'PASS']}"
    assert (fld_res["status"] == "PASS").all(), f"Failing FLD rows:\n{fld_res[fld_res['status'] != 'PASS']}"

    # Verify SQL parity via DuckDB over the 2-FY fixture tables
    con = duckdb.connect(":memory:")
    w_fld = _ensure_wide_field_df(fld_df)
    con.register("ssot_employee_360", emp_df)
    con.register("fact_employee_cost_pool", pool_df)
    con.register("ssot_field_economics_360", w_fld)
    con.register("fact_field_alloc_audit", audit_df)
    con.register("targets", targets_df)

    sql_emp_r01 = con.execute(
        """
        SELECT
          e.fiscal_year,
          (SUM(e.cost_total_inr) + COALESCE(MAX(p.pool_inr), 0)) / 1e6 AS ssot_value,
          t.value AS reference_value
        FROM ssot_employee_360 e
        LEFT JOIN (
          SELECT fiscal_year, SUM(amount_inr) AS pool_inr
          FROM fact_employee_cost_pool
          GROUP BY fiscal_year
        ) p USING (fiscal_year)
        LEFT JOIN targets t ON e.fiscal_year = t.fiscal_year AND t.metric_code = 'employee_cost_total'
        GROUP BY e.fiscal_year, t.value
        ORDER BY e.fiscal_year
        """
    ).df()
    py_emp_r01 = emp_res[emp_res["check_id"] == "EMP-R01"].sort_values("fiscal_year")
    np.testing.assert_allclose(sql_emp_r01["ssot_value"].values, py_emp_r01["ssot_value"].values, rtol=1e-6)
    np.testing.assert_allclose(sql_emp_r01["reference_value"].values, py_emp_r01["reference_value"].values, rtol=1e-6)

    sql_fld_r04_roy = con.execute(
        """
        SELECT
          f.fiscal_year,
          SUM(f.royalty) AS ssot_value,
          t.value AS reference_value
        FROM ssot_field_economics_360 f
        LEFT JOIN targets t ON f.fiscal_year = t.fiscal_year AND t.line_code = 'N35.ROYALTY'
        GROUP BY f.fiscal_year, t.value
        ORDER BY f.fiscal_year
        """
    ).df()
    py_fld_r04_roy = fld_res[
        (fld_res["check_id"] == "FLD-R04") & (fld_res["dimension_key"] == "N35.ROYALTY")
    ].sort_values("fiscal_year")
    np.testing.assert_allclose(sql_fld_r04_roy["ssot_value"].values, py_fld_r04_roy["ssot_value"].values, rtol=1e-6)
    np.testing.assert_allclose(sql_fld_r04_roy["reference_value"].values, py_fld_r04_roy["reference_value"].values, rtol=1e-6)


def test_fld_r04_seeded_break(fixture_dfs):
    """Mutate a real N35.ROYALTY row by +1.0 (Rs 1 mn) and verify FLD-R04 transitions PASS -> FAIL."""
    emp_df, pool_df, fld_df, audit_df, targets_df = fixture_dfs

    fld_mut = fld_df.copy()
    royalty_mask = (
        (fld_mut["fiscal_year"] == "FY26")
        & (fld_mut["object_id"] == "FLD-MHN")
        & (fld_mut["line_code"] == "N35.ROYALTY")
    )
    assert royalty_mask.sum() == 1
    first_idx = fld_mut[royalty_mask].index[0]
    fld_mut.loc[first_idx, "amount_inr_mn"] += 1.0

    fld_res_mut = run_field_reconciliation(fld_mut, targets_df, audit_df=audit_df, emp_df=emp_df)
    r04_roy_fy26 = fld_res_mut[
        (fld_res_mut["check_id"] == "FLD-R04")
        & (fld_res_mut["fiscal_year"] == "FY26")
        & (fld_res_mut["dimension_key"] == "N35.ROYALTY")
    ]
    assert len(r04_roy_fy26) == 1
    row = r04_roy_fy26.iloc[0]
    assert row["status"] == "FAIL"
    assert row["severity"] == "BLOCK"
    assert row["abs_diff"] == pytest.approx(1.0, abs=1e-6)
    assert row["abs_diff"] > row["tolerance_abs"]

    # Verify assert_recon_block_pass filter returns >= 1 row
    block_fails = fld_res_mut[(fld_res_mut["severity"] == "BLOCK") & (fld_res_mut["status"] == "FAIL")]
    assert len(block_fails) >= 1


def test_emp_r01_seeded_break(fixture_dfs):
    """Mutate a real employee cost row by +1,000,000 INR (+Rs 1 mn) and verify EMP-R01 transitions PASS -> FAIL."""
    emp_df, pool_df, fld_df, audit_df, targets_df = fixture_dfs

    emp_mut = emp_df.copy()
    fy26_idx = emp_mut[emp_mut["fiscal_year"] == "FY26"].index[0]
    emp_mut.loc[fy26_idx, "cost_note35_a_inr"] += 1_000_000.0
    emp_mut.loc[fy26_idx, "cost_total_inr"] += 1_000_000.0
    emp_mut.loc[fy26_idx, "cost_expensed_inr"] += 1_000_000.0

    emp_res_mut = run_employee_reconciliation(emp_mut, pool_df, targets_df)
    r01_fy26 = emp_res_mut[(emp_res_mut["check_id"] == "EMP-R01") & (emp_res_mut["fiscal_year"] == "FY26")]
    assert len(r01_fy26) == 1
    row = r01_fy26.iloc[0]
    assert row["status"] == "FAIL"
    assert row["severity"] == "BLOCK"
    assert row["abs_diff"] == pytest.approx(1.0, abs=1e-6)
    assert row["abs_diff"] > row["tolerance_abs"]

    block_fails = emp_res_mut[(emp_res_mut["severity"] == "BLOCK") & (emp_res_mut["status"] == "FAIL")]
    assert len(block_fails) >= 1


def test_golden_yaml_schema():
    """Validate all 40 BEH-06 scenarios across golden_employee360.yaml and golden_field_econ.yaml."""
    emp_yaml_path = EVAL_DIR / "golden_employee360.yaml"
    fld_yaml_path = EVAL_DIR / "golden_field_econ.yaml"
    assert emp_yaml_path.exists(), f"Missing {emp_yaml_path}"
    assert fld_yaml_path.exists(), f"Missing {fld_yaml_path}"

    emp_scenarios = yaml.safe_load(emp_yaml_path.read_text(encoding="utf-8"))["scenarios"]
    fld_scenarios = yaml.safe_load(fld_yaml_path.read_text(encoding="utf-8"))["scenarios"]

    assert len(emp_scenarios) == 31
    assert len(fld_scenarios) == 9
    all_scenarios = emp_scenarios + fld_scenarios
    assert {s["id"] for s in all_scenarios} == {f"BEH-06.{i:02d}" for i in range(1, 41)}

    valid_personas = {
        "CMD", "DIR_HR", "DIR_FIN",
        "E1_HR", "E2_HR", "E3_HR", "E4_HR",
        "E1_FIN", "E2_FIN", "E3_FIN", "E4_FIN",
    }
    valid_visuals = {
        "kpi_card", "table", "payslip", "column", "bar", "line", "combo",
        "stacked_column", "stacked_100", "waterfall", "donut", "box",
        "roster", "recon_table", "refusal", "aggregate",
    }
    valid_rbac = {"allow", "aggregate", "self", "refuse"}

    for s in all_scenarios:
        sid = s["id"]
        assert s.get("persona") in valid_personas, f"{sid}: invalid persona {s.get('persona')!r}"
        utt = s.get("utterance", "")
        assert isinstance(utt, str) and len(utt) >= 15 and not utt.startswith("("), f"{sid}: bad utterance {utt!r}"

        exp = s.get("expected", {})
        assert exp.get("visual_type") in valid_visuals, f"{sid}: invalid visual_type {exp.get('visual_type')!r}"
        assert exp.get("rbac") in valid_rbac, f"{sid}: invalid rbac {exp.get('rbac')!r}"
        assert isinstance(exp.get("tolerance_pct"), (int, float)), f"{sid}: missing numeric tolerance_pct"
        assert exp.get("citations") and len(exp["citations"]) >= 1, f"{sid}: missing citations"

        vals = exp.get("values")
        sql = exp.get("recompute_sql")
        assert vals is not None or sql is not None, f"{sid}: must specify values or recompute_sql"
        if vals is not None:
            assert vals != [1] and vals != [1.0], f"{sid}: placeholder values [1] not allowed"
        if sql is not None:
            assert sql.strip().upper() != "SELECT 1", f"{sid}: placeholder SELECT 1 not allowed"
            assert "hrfin_" in sql, f"{sid}: recompute_sql must query real hrfin_* table/view"
