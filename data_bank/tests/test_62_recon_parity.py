"""Parity and seeded-break tests for Employee-360 & Field-Economics-360 reconciliation (P2H.8)."""

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
        & (fld_mut["object_id"] == "FLD-MUMBAI-HIGH")
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
