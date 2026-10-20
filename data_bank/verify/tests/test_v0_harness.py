"""
test_v0_harness.py — Unit tests for Independent Verification Harness V0
Testing loader, probes runner, consistency engine, and verify_step orchestrator
strictly against tiny synthetic fixtures under verify/fixtures/.
"""

import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import duckdb
import pytest

from verify.consistency import (
    audit_fk_validity,
    audit_pk_uniqueness,
    audit_temporal_sanity,
    run_consistency_audits,
)
from verify.loader import generate_dim_calendar, load_data
from verify.run_probes import execute_probes, run_single_probe
from verify.verify_step import verify_step

FIXTURES_LANDING = Path(__file__).resolve().parent.parent / "fixtures" / "landing"
SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / "world_bible" / "schema_silver.yaml"
REF_DIR = Path(__file__).resolve().parent.parent.parent / "world_bible" / "reference"


@pytest.fixture
def mem_conn():
    """Isolated in-memory DuckDB connection loaded with synthetic fixtures."""
    conn = duckdb.connect(":memory:")
    conn, report = load_data(
        conn=conn,
        schema_path=SCHEMA_PATH,
        ref_dir=REF_DIR,
        landing_dir=FIXTURES_LANDING,
    )
    return conn, report


def test_loader_loads_reference_dimensions(mem_conn):
    """Verify that world_bible reference dimensions load with exact silver view schemas."""
    conn, report = mem_conn
    assert "dim_work_centre" in report.available_tables
    assert "dim_grade" in report.available_tables
    assert "dim_discipline" in report.available_tables
    assert "dim_calendar" in report.available_tables

    wc_count = conn.execute("SELECT COUNT(*) FROM dim_work_centre").fetchone()[0]
    assert wc_count > 0

    # Check that silver views exist under default, silver_, and hrfin_silver namespaces
    assert conn.execute("SELECT COUNT(*) FROM silver_dim_work_centre").fetchone()[0] == wc_count
    assert conn.execute("SELECT COUNT(*) FROM hrfin_silver.dim_work_centre").fetchone()[0] == wc_count


def test_loader_synthetic_csv_and_sap_mapping(mem_conn):
    """Verify CSV ingestion and SAP field mapping on synthetic HR tables."""
    conn, report = mem_conn
    assert "employee_master" in report.available_tables
    assert "posting_history" in report.available_tables

    # Check employee_master mapped SAP fields to Silver columns
    cols = [r[0] for r in conn.execute("DESCRIBE employee_master").fetchall()]
    assert "emp_id" in cols
    assert "doj" in cols
    assert "dob" in cols
    assert "gender" in cols
    assert "current_wc_id" in cols
    assert "current_grade_id" in cols

    emp_rows = conn.execute("SELECT emp_id, doj, current_wc_id, current_grade_id FROM employee_master").fetchall()
    assert len(emp_rows) == 3
    assert emp_rows[0][0] == "100001"
    assert emp_rows[0][2] == "WC-DEL"


def test_loader_synthetic_excel_ingestion(mem_conn):
    """Verify Excel .xlsx ingestion into silver views."""
    conn, report = mem_conn
    assert "dpc_cases" in report.available_tables

    dpc_rows = conn.execute("SELECT dpc_id, emp_id, status FROM dpc_cases").fetchall()
    assert len(dpc_rows) == 1
    assert dpc_rows[0][0] == "DPC-FY26-01"
    assert dpc_rows[0][1] == "100001"


def test_consistency_pk_uniqueness(mem_conn):
    """Verify PK uniqueness passes on clean synthetic data and catches injected duplicate."""
    conn, _ = mem_conn
    report = run_consistency_audits(conn)

    # In clean state, all PK audits must pass
    pk_audits = [a for a in report.audit_results if a.audit_category == "PK"]
    assert len(pk_audits) > 0
    assert all(a.status == "PASS" for a in pk_audits)

    # Inject duplicate PK into employee_master raw table and re-run
    conn.execute("""
        INSERT INTO main.raw_employee_master (PERNR, BEGDA, GBDAT, GESCH, VDSK1, WERKS, PERSK, STAT2)
        VALUES ('100001', '2015-06-01', '1985-04-12', 'M', 'General', 'WC-DEL', 'E4', 'Active');
    """)
    dirty_report = run_consistency_audits(conn)
    emp_pk_audit = next(a for a in dirty_report.audit_results if a.target_entity == "employee_master")
    assert emp_pk_audit.status == "FAIL"
    assert emp_pk_audit.violations_count >= 1


def test_consistency_fk_validity(mem_conn):
    """Verify FK validity passes on clean synthetic data and catches injected orphan."""
    conn, _ = mem_conn
    report = run_consistency_audits(conn)

    fk_audits = [a for a in report.audit_results if a.audit_category == "FK"]
    assert len(fk_audits) > 0
    assert all(a.status == "PASS" for a in fk_audits)

    # Inject orphan FK in posting_history (nonexistent emp_id)
    conn.execute("""
        INSERT INTO main.raw_posting_history (PERNR, BEGDA, ENDDA, WERKS, PERSK, MASSN, MASSG)
        VALUES ('999999', '2022-01-01', NULL, 'WC-DEL', 'E1', 'ROT', 'REG');
    """)
    dirty_report = run_consistency_audits(conn)
    orphan_audit = next(a for a in dirty_report.audit_results if "posting_history.emp_id" in a.target_entity)
    assert orphan_audit.status == "FAIL"
    assert orphan_audit.violations_count >= 1


def test_consistency_temporal_sanity(mem_conn):
    """Verify temporal sanity audits on synthetic data."""
    conn, _ = mem_conn
    report = run_consistency_audits(conn)
    temporal_audits = [a for a in report.audit_results if a.audit_category == "TEMPORAL"]
    assert len(temporal_audits) > 0
    assert all(a.status == "PASS" for a in temporal_audits)


def test_run_probes_against_synthetic_data(mem_conn):
    """Test probe runner against synthetic fixture."""
    conn, report = mem_conn
    summary = execute_probes(conn)
    assert summary.total_probes == 356
    assert summary.stubs == 102
    assert summary.executed > 0


def test_verify_step_orchestrator(tmp_path):
    """Verify end-to-end orchestration and report generation."""
    json_res = verify_step(
        step_id="test_synthetic",
        db_path=tmp_path / "test.duckdb",
        landing_dir=FIXTURES_LANDING,
        output_dir=tmp_path,
    )
    assert json_res["step_id"] == "test_synthetic"
    assert "verdict" in json_res
    assert (tmp_path / "test_synthetic_verification.md").exists()
    assert (tmp_path / "test_synthetic_verification.json").exists()

    md_text = (tmp_path / "test_synthetic_verification.md").read_text(encoding="utf-8")
    assert "# Step test_synthetic Verification Report" in md_text
    assert "## 1. Landing Data Provenance Manifest" in md_text
    assert "## 2. Executive Summary" in md_text
