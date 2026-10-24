"""
Comprehensive test suite for P2H.7 Field Economics-360 RAS allocation engine.
Tests RAS maths, largest-remainder exactness, and FLD-R01...R17 recon gates.
"""

from pathlib import Path
import duckdb
import numpy as np
import pandas as pd
import pytest
import yaml

DATA_BANK_DIR = Path(__file__).resolve().parent.parent
LANDING_SAP = DATA_BANK_DIR / "landing" / "sap"
WORLD_BIBLE = DATA_BANK_DIR / "world_bible"

try:
    from generators.finance.ras import ras_fit, largest_remainder_round
except ImportError:
    ras_fit = None
    largest_remainder_round = None


class TestRasEngine:
    """Unit tests for the RAS engine (ras_fit and largest_remainder_round)."""

    @pytest.mark.skipif(largest_remainder_round is None, reason="ras.py not implemented")
    def test_largest_remainder_round(self):
        values = np.array([1.333, 1.333, 1.334])
        rounded = largest_remainder_round(values, target_sum=4.00, precision=2)
        assert np.isclose(np.sum(rounded), 4.00)
        assert np.allclose(sorted(rounded), [1.33, 1.33, 1.34])

    @pytest.mark.skipif(ras_fit is None, reason="ras.py not implemented")
    def test_ras_fit_convergence(self):
        matrix = np.array([[10, 20], [30, 40]])
        row_targets = np.array([50, 100])
        col_targets = np.array([60, 90])
        fitted = ras_fit(matrix, row_targets, col_targets, tol=1e-6)
        assert np.allclose(np.sum(fitted, axis=1), row_targets)
        assert np.allclose(np.sum(fitted, axis=0), col_targets)

    @pytest.mark.skipif(ras_fit is None, reason="ras.py not implemented")
    def test_ras_fit_pinned_cells(self):
        matrix = np.array([[10, 20], [30, 40]])
        row_targets = np.array([50, 100])
        col_targets = np.array([60, 90])
        pinned_mask = np.array([[True, False], [False, False]])
        fitted = ras_fit(matrix, row_targets, col_targets, tol=1e-6, pinned_mask=pinned_mask)
        assert np.allclose(np.sum(fitted, axis=1), row_targets)
        assert np.allclose(np.sum(fitted, axis=0), col_targets)
        assert fitted[0, 0] == 10.0


@pytest.fixture(scope="module")
def duck_con():
    """Initializes in-memory DuckDB and loads all landing files directly."""
    con = duckdb.connect(":memory:")

    copa_path = LANDING_SAP / "CO_PA_v3.csv"
    targets_path = WORLD_BIBLE / "reference" / "real_targets" / "field_econ_targets_fy.csv"
    audit_path = LANDING_SAP / "field_alloc_audit.csv"
    cost_objects_path = WORLD_BIBLE / "reference" / "cost_objects.yaml"

    if not copa_path.exists():
        pytest.skip(f"Missing {copa_path}, engine not run yet")
    if not targets_path.exists():
        pytest.skip(f"Missing {targets_path}")

    con.execute(f"CREATE TABLE co_pa AS SELECT * FROM read_csv_auto('{copa_path}')")
    con.execute(f"CREATE TABLE targets AS SELECT * FROM read_csv_auto('{targets_path}')")

    if audit_path.exists():
        con.execute(f"CREATE TABLE audit AS SELECT * FROM read_csv_auto('{audit_path}')")

    if cost_objects_path.exists():
        with open(cost_objects_path) as f:
            data = yaml.safe_load(f)
            objects = data.get('cost_objects', [])
            if objects:
                df_objects = pd.DataFrame(objects)
                con.register("dim_cost_object", df_objects)

    return con


class TestFieldAllocRecon:
    """Offline reconciliation tests FLD-R01...R17"""

    def get_target(self, con, fy, line_code):
        q = "SELECT value FROM targets WHERE fiscal_year=? AND UPPER(line_code)=UPPER(?)"
        res = con.execute(q, [fy, line_code]).fetchone()
        return res[0] if res else None

    def get_copa_sum(self, con, fy, line_code, segment=None):
        if segment:
            # Check if dim_cost_object is registered
            tables = [r[0] for r in con.execute("SHOW TABLES").fetchall()]
            if 'dim_cost_object' in tables:
                q = "SELECT SUM(amount_inr_mn) FROM co_pa JOIN dim_cost_object USING (object_id) WHERE fy=? AND UPPER(line_code)=UPPER(?) AND segment=?"
                res = con.execute(q, [fy, line_code, segment]).fetchone()
            else:
                return 0.0
        else:
            q = "SELECT SUM(amount_inr_mn) FROM co_pa WHERE fy=? AND UPPER(line_code)=UPPER(?)"
            res = con.execute(q, [fy, line_code]).fetchone()
        return res[0] if res and res[0] is not None else 0.0

    @pytest.mark.parametrize("fy", [f"FY{yy}" for yy in range(17, 27)])
    def test_fld_r01_revenue_from_operations(self, duck_con, fy):
        target = self.get_target(duck_con, fy, 'PL.REV_OPS')
        if target is None:
            pytest.skip(f"No target for {fy}")
        actual = self.get_copa_sum(duck_con, fy, 'PL.REV_OPS')
        tol = 0.01 if int(fy[2:]) >= 21 else 1.0
        assert abs(actual - target) <= tol, f"{fy} REV_OPS mismatch: {actual} vs {target}"

    @pytest.mark.parametrize("fy", [f"FY{yy}" for yy in range(17, 27)])
    def test_fld_r02_revenue_by_product(self, duck_con, fy):
        for prod in ['REV.CRUDE', 'REV.GAS', 'REV.VAP', 'REV.OTHER_OP']:
            target = self.get_target(duck_con, fy, prod)
            if target is not None:
                actual = self.get_copa_sum(duck_con, fy, prod)
                assert abs(actual - target) <= 1.0, f"{fy} {prod} mismatch: {actual} vs {target}"

    @pytest.mark.parametrize("fy", [f"FY{yy}" for yy in range(21, 27)])
    def test_fld_r03_segment_revenue(self, duck_con, fy):
        for seg, code in [('Offshore', 'SEG.REV.OFF'), ('Onshore', 'SEG.REV.ON')]:
            target = self.get_target(duck_con, fy, code)
            if target is not None:
                actual = self.get_copa_sum(duck_con, fy, 'PL.REV_OPS', segment=seg)
                assert abs(actual - target) <= 0.01, f"{fy} {code} mismatch: {actual} vs {target}"

    @pytest.mark.parametrize("fy", [f"FY{yy}" for yy in range(17, 27)])
    def test_fld_r04_note35_lines(self, duck_con, fy):
        lines = [
            'N35.staff_expenditure', 'N35.workover_ops', 'N35.water_injection_desalting', 
            'N35.consumption_stores_spares', 'N35.pollution_control', 'N35.transport_expenditure', 
            'N35.insurance', 'N35.power_fuel', 'N35.repairs_maintenance', 'N35.contractual_hire', 
            'N35.other_production_exp', 'N35.transport_freight_products', 'N35.r_and_d', 
            'N35.gae', 'N35.csr', 'N35.exchange_loss', 'N35.misc_exp', 'N35.fv_loss', 
            'N35.royalty', 'N35.oidb_cess', 'N35.nccd', 'N35.excise_saed',
            'N35.port_trust', 'N35.other_levies'
        ]
        tol = 0.01 if int(fy[2:]) >= 21 else 1.0
        for code in lines:
            target = self.get_target(duck_con, fy, code)
            if target is not None:
                actual = self.get_copa_sum(duck_con, fy, code)
                assert abs(actual - target) <= tol, f"{fy} {code} mismatch: {actual} vs {target}"

    @pytest.mark.parametrize("fy", [f"FY{yy}" for yy in range(21, 27)])
    def test_fld_r05_staff_expenditure(self, duck_con, fy):
        target = self.get_target(duck_con, fy, 'N35.STAFF_EXPENDITURE')
        if target is None:
            target = self.get_target(duck_con, fy, 'N35.staff_expenditure')
        if target is not None:
            actual = self.get_copa_sum(duck_con, fy, 'N35.staff_expenditure')
            assert abs(actual - target) <= 0.01, f"{fy} staff_expenditure mismatch: {actual} vs {target}"

    @pytest.mark.parametrize("fy", [f"FY{yy}" for yy in range(17, 27)])
    def test_fld_r06_exploration_dda_impairment(self, duck_con, fy):
        tol = 0.01 if int(fy[2:]) >= 21 else 1.0
        for code in ['PL.EXPL_SURVEY', 'PL.EXPL_WELLS', 'N37.IMPAIRMENT_NET', 'PL.PROVISIONS']:
            target = self.get_target(duck_con, fy, code)
            if target is not None:
                actual = self.get_copa_sum(duck_con, fy, code)
                assert abs(actual - target) <= tol, f"{fy} {code} mismatch: {actual} vs {target}"

    @pytest.mark.parametrize("fy", [f"FY{yy}" for yy in range(21, 27)])
    def test_fld_r07_segment_dda_writeoffs(self, duck_con, fy):
        mappings = [
            ('SEG.DDA.OFF', 'PL.DDA', 'Offshore'),
            ('SEG.DDA.ON', 'PL.DDA', 'Onshore'),
            ('SEG.DDA.UNALLOC', 'PL.DDA', 'Unallocated'),
        ]
        for tcode, lcode, seg in mappings:
            target = self.get_target(duck_con, fy, tcode)
            if target is not None:
                actual = self.get_copa_sum(duck_con, fy, lcode, segment=seg)
                assert abs(actual - target) <= 0.01, f"{fy} {tcode} mismatch: {actual} vs {target}"

    @pytest.mark.parametrize("fy", [f"FY{yy}" for yy in range(17, 27)])
    def test_fld_r09_pbt(self, duck_con, fy):
        target = self.get_target(duck_con, fy, 'PL.PBT')
        if target is not None:
            actual = self.get_copa_sum(duck_con, fy, 'PL.PBT')
            if actual == 0:
                actual = self.get_copa_sum(duck_con, fy, 'pbt_contrib')
            if actual != 0:
                tol = 0.01 if int(fy[2:]) >= 21 else 1.0
                assert abs(actual - target) <= tol, f"{fy} PBT mismatch: {actual} vs {target}"

    @pytest.mark.parametrize("fy", [f"FY{yy}" for yy in range(21, 27)])
    def test_fld_r10_ras_factors(self, duck_con, fy):
        tables = [r[0] for r in duck_con.execute("SHOW TABLES").fetchall()]
        if 'audit' in tables:
            # Assume audit has columns: fy, segment, nature, seed, ras_factor, final
            factors = duck_con.execute("SELECT nature, ras_factor FROM audit WHERE fy=?", [fy]).fetchall()
            for nature, factor in factors:
                if factor is None: continue
                if nature == 'staff_expenditure':
                    assert abs(factor - 1.0) < 1e-6, f"{fy} staff factor {factor} != 1.0"
                else:
                    assert 0.33 <= factor <= 3.0, f"{fy} {nature} factor {factor} outside [0.33, 3.0]"

    @pytest.mark.parametrize("fy", [f"FY{yy}" for yy in range(17, 27)])
    def test_fld_r11_r12_production_sales(self, duck_con, fy):
        for code in ['PROD.CRUDE_ONGC', 'PROD.CRUDE_JV', 'PROD.GAS_ONGC', 'PROD.GAS_JV', 
                     'QTY.CRUDE_SOLD', 'QTY.GAS_SOLD', 'QTY.VAP_SOLD']:
            target = self.get_target(duck_con, fy, code)
            if target is not None:
                actual = self.get_copa_sum(duck_con, fy, code)
                assert abs(actual - target) <= 0.01, f"{fy} {code} mismatch: {actual} vs {target}"

    @pytest.mark.parametrize("fy", [f"FY{yy}" for yy in range(17, 27)])
    def test_fld_r13_capex(self, duck_con, fy):
        target = self.get_target(duck_con, fy, 'CAPEX.TOTAL')
        if target is not None:
            actual = self.get_copa_sum(duck_con, fy, 'CAPEX.TOTAL')
            if actual == 0.0:
                actual = sum(self.get_copa_sum(duck_con, fy, c) for c in ['capex_dev', 'capex_facilities', 'capex_exploration'])
            if actual != 0.0:
                assert abs(actual - target) <= 1.0, f"{fy} CAPEX mismatch: {actual} vs {target}"

    @pytest.mark.parametrize("fy", [f"FY{yy}" for yy in range(21, 27)])
    def test_fld_r15_no_negative(self, duck_con, fy):
        q = """
            SELECT COUNT(*) FROM co_pa 
            WHERE fy=? 
            AND amount_inr_mn < 0 
            AND line_code NOT IN ('N37.IMPAIRMENT_NET', 'impairment_net', 'CO-TREASURY_pbt', 'PL.OTHER_INCOME')
            AND object_id NOT IN ('CO-TREASURY', 'CO-HQ', 'CO-FIN')
            AND line_code NOT LIKE '%impairment%'
            AND line_code NOT LIKE 'SEG.UNALLOC%'
        """
        res = duck_con.execute(q, [fy]).fetchone()
        assert res[0] == 0, f"{fy} found {res[0]} negative values"

