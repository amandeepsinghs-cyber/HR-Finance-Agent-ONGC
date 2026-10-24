import pytest
import subprocess
import sys
import json
from pathlib import Path
import os
import yaml

DATA_BANK_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = DATA_BANK_ROOT / "tests" / "fixtures" / "recon"

def test_parity():
    # Write synthetic fixtures
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    (FIXTURES_DIR / "emp_fixture.csv").write_text("fiscal_year,seeded_break_emp,seeded_break_fld,cost_note35_a_inr,cost_note35_b_inr,cost_note35_c_inr,cost_note35_d_inr,cost_note35_e_inr,cost_note35_f_inr,gross_earnings_inr,total_deductions_inr,net_pay_inr,cost_total_inr\nFY26,0,0,0,0,0,0,0,0,0,0,0,0\n")
    (FIXTURES_DIR / "fld_fixture.csv").write_text("fiscal_year,seeded_break_emp,seeded_break_fld\nFY26,0,0\n")
    (FIXTURES_DIR / "targets_fixture.csv").write_text("fiscal_year,metric,value\nFY26,employee_cost_total,0\n")

    res = subprocess.run([
        sys.executable, str(DATA_BANK_ROOT / "generators" / "reconcile.py"),
        "--json-out",
        "--emp-csv", str(FIXTURES_DIR / "emp_fixture.csv"),
        "--fld-csv", str(FIXTURES_DIR / "fld_fixture.csv"),
        "--targets-csv", str(FIXTURES_DIR / "targets_fixture.csv")
    ], capture_output=True, text=True)
    assert res.returncode == 0
    data = json.loads(res.stdout)
    assert len(data) >= 40

def test_fld_r04_seeded_break():
    (FIXTURES_DIR / "fld_fixture_break.csv").write_text("fiscal_year,seeded_break_emp,seeded_break_fld\nFY26,0,1\n")
    res = subprocess.run([
        sys.executable, str(DATA_BANK_ROOT / "generators" / "reconcile.py"),
        "--json-out",
        "--emp-csv", str(FIXTURES_DIR / "emp_fixture.csv"),
        "--fld-csv", str(FIXTURES_DIR / "fld_fixture_break.csv"),
        "--targets-csv", str(FIXTURES_DIR / "targets_fixture.csv")
    ], capture_output=True, text=True)
    assert res.returncode == 2
    data = json.loads(res.stdout)
    fld_r04 = next(d for d in data if d['check_id'] == 'FLD-R04')
    assert fld_r04['status'] == 'FAIL'

def test_emp_r01_seeded_break():
    (FIXTURES_DIR / "emp_fixture_break.csv").write_text("fiscal_year,seeded_break_emp,seeded_break_fld,cost_note35_a_inr,cost_note35_b_inr,cost_note35_c_inr,cost_note35_d_inr,cost_note35_e_inr,cost_note35_f_inr,gross_earnings_inr,total_deductions_inr,net_pay_inr,cost_total_inr\nFY26,1,0,0,0,0,0,0,0,0,0,0,0\n")
    res = subprocess.run([
        sys.executable, str(DATA_BANK_ROOT / "generators" / "reconcile.py"),
        "--json-out",
        "--emp-csv", str(FIXTURES_DIR / "emp_fixture_break.csv"),
        "--fld-csv", str(FIXTURES_DIR / "fld_fixture.csv"),
        "--targets-csv", str(FIXTURES_DIR / "targets_fixture.csv")
    ], capture_output=True, text=True)
    assert res.returncode == 2
    data = json.loads(res.stdout)
    emp_r01 = next(d for d in data if d['check_id'] == 'EMP-R01')
    assert emp_r01['status'] == 'FAIL'

def test_golden_yaml_schema():
    golden_emp = DATA_BANK_ROOT.parent / "yukti" / "backend" / "eval" / "golden_employee360.yaml"
    golden_fld = DATA_BANK_ROOT.parent / "yukti" / "backend" / "eval" / "golden_field_econ.yaml"
    with open(golden_emp) as f:
        emp_data = yaml.safe_load(f)
    with open(golden_fld) as f:
        fld_data = yaml.safe_load(f)
    
    all_data = emp_data + fld_data
    assert len(all_data) == 40
    ids = [d['id'] for d in all_data]
    for i in range(1, 41):
        assert f"BEH-06.{i:02d}" in ids
    
    for item in all_data:
        assert 'id' in item
        assert 'persona' in item
        assert 'utterance' in item
        assert 'expect' in item
        expect = item['expect']
        assert 'tolerance' in expect
        assert 'label' in expect
        assert 'visual_type' in expect
        assert 'rbac' in expect
        assert 'values' in expect or 'recompute_sql' in expect
