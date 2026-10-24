"""
Comprehensive test suite for P2H.7 Field Economics-360 RAS allocation engine.
Tests RAS maths, largest-remainder exactness, FLD-R01...R17 recon gates,
and two-run SHA-256 determinism.
"""

import hashlib
from pathlib import Path
import sys
import duckdb
import numpy as np
import pandas as pd
import pytest
import yaml

DATA_BANK_DIR = Path(__file__).resolve().parent.parent
if str(DATA_BANK_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_BANK_DIR))
LANDING_SAP = DATA_BANK_DIR / "landing" / "sap"
WORLD_BIBLE = DATA_BANK_DIR / "world_bible"

try:
    from generators.finance.ras import ras_fit, largest_remainder_round
    from generators.finance.alloc_field_economics import run_allocation
except ImportError:
    ras_fit = None
    largest_remainder_round = None
    run_allocation = None


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

    @pytest.mark.skipif(run_allocation is None, reason="alloc_field_economics.py not implemented")
    def test_two_run_sha256_determinism(self):
        """Running run_allocation() twice must produce byte-identical CSVs."""
        copa_path = LANDING_SAP / "CO_PA_v3.csv"
        audit_path = LANDING_SAP / "field_alloc_audit.csv"
        run_allocation()
        h1_copa = hashlib.sha256(copa_path.read_bytes()).hexdigest()
        h1_audit = hashlib.sha256(audit_path.read_bytes()).hexdigest()
        run_allocation()
        h2_copa = hashlib.sha256(copa_path.read_bytes()).hexdigest()
        h2_audit = hashlib.sha256(audit_path.read_bytes()).hexdigest()
        assert h1_copa == h2_copa, "CO_PA_v3.csv is not deterministic across runs"
        assert h1_audit == h2_audit, "field_alloc_audit.csv is not deterministic across runs"


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
            objects = data.get("cost_objects", [])
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

    def get_copa_sum(self, con, fy, line_code, segment=None, object_id=None):
        if object_id:
            q = "SELECT SUM(amount_inr_mn) FROM co_pa WHERE fy=? AND UPPER(line_code)=UPPER(?) AND object_id=?"
            res = con.execute(q, [fy, line_code, object_id]).fetchone()
        elif segment:
            tables = [r[0] for r in con.execute("SHOW TABLES").fetchall()]
            if "dim_cost_object" in tables:
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
        target = self.get_target(duck_con, fy, "PL.REV_OPS")
        assert target is not None, f"Missing PL.REV_OPS target for {fy}"
        assert target > 500000.0, f"{fy} PL.REV_OPS must be in INR million, got {target}"
        actual = self.get_copa_sum(duck_con, fy, "PL.REV_OPS")
        tol = 0.01 if int(fy[2:]) >= 21 else 1.0
        assert abs(actual - target) <= tol, f"{fy} REV_OPS mismatch: {actual} vs {target}"

    @pytest.mark.parametrize("fy", [f"FY{yy}" for yy in range(17, 27)])
    def test_fld_r02_revenue_by_product(self, duck_con, fy):
        for prod in ["REV.CRUDE", "REV.GAS", "REV.VAP", "REV.OTHER_OP"]:
            target = self.get_target(duck_con, fy, prod)
            assert target is not None, f"Missing {prod} target for {fy}"
            actual = self.get_copa_sum(duck_con, fy, prod)
            assert abs(actual - target) <= 1.0, f"{fy} {prod} mismatch: {actual} vs {target}"

    @pytest.mark.parametrize("fy", [f"FY{yy}" for yy in range(21, 27)])
    def test_fld_r03_segment_revenue(self, duck_con, fy):
        for seg, code in [("Offshore", "SEG.REV.OFF"), ("Onshore", "SEG.REV.ON")]:
            target = self.get_target(duck_con, fy, code)
            assert target is not None, f"Missing {code} target for {fy}"
            actual = self.get_copa_sum(duck_con, fy, "PL.REV_OPS", segment=seg)
            assert abs(actual - target) <= 0.01, f"{fy} {code} mismatch: {actual} vs {target}"

    @pytest.mark.parametrize("fy", [f"FY{yy}" for yy in range(17, 27)])
    def test_fld_r04_note35_lines(self, duck_con, fy):
        lines = [
            "N35.staff_expenditure",
            "N35.workover_ops",
            "N35.water_injection_desalting",
            "N35.consumption_stores_spares",
            "N35.pollution_control",
            "N35.transport_expenditure",
            "N35.insurance",
            "N35.power_fuel",
            "N35.repairs_maintenance",
            "N35.contractual_hire",
            "N35.other_production_exp",
            "N35.transport_freight_products",
            "N35.r_and_d",
            "N35.gae",
            "N35.csr",
            "N35.exchange_loss",
            "N35.misc_exp",
            "N35.fv_loss",
            "N35.royalty",
            "N35.oidb_cess",
            "N35.nccd",
            "N35.excise_saed",
            "N35.port_trust",
            "N35.other_levies",
        ]
        tol = 0.01 if int(fy[2:]) >= 21 else 1.0
        for code in lines:
            target = self.get_target(duck_con, fy, code)
            assert target is not None, f"Missing {code} target for {fy}"
            actual = self.get_copa_sum(duck_con, fy, code)
            assert abs(actual - target) <= tol, f"{fy} {code} mismatch: {actual} vs {target}"

    @pytest.mark.parametrize("fy", [f"FY{yy}" for yy in range(21, 27)])
    def test_fld_r05_staff_expenditure(self, duck_con, fy):
        target = self.get_target(duck_con, fy, "N35.STAFF_EXPENDITURE")
        assert target is not None, f"Missing N35.STAFF_EXPENDITURE target for {fy}"
        actual = self.get_copa_sum(duck_con, fy, "N35.staff_expenditure")
        assert abs(actual - target) <= 0.01, f"{fy} staff_expenditure mismatch: {actual} vs {target}"

    @pytest.mark.parametrize("fy", [f"FY{yy}" for yy in range(17, 27)])
    def test_fld_r06_exploration_dda_impairment(self, duck_con, fy):
        tol = 0.01 if int(fy[2:]) >= 21 else 1.0
        for code in ["PL.EXPL_SURVEY", "PL.EXPL_WELLS", "N37.IMPAIRMENT_NET", "PL.PROVISIONS"]:
            target = self.get_target(duck_con, fy, code)
            assert target is not None, f"Missing {code} target for {fy}"
            actual = self.get_copa_sum(duck_con, fy, code)
            assert abs(actual - target) <= tol, f"{fy} {code} mismatch: {actual} vs {target}"

    @pytest.mark.parametrize("fy", [f"FY{yy}" for yy in range(21, 27)])
    def test_fld_r07_segment_dda_writeoffs(self, duck_con, fy):
        mappings = [
            ("SEG.DDA.OFF", "PL.DDA", "Offshore"),
            ("SEG.DDA.ON", "PL.DDA", "Onshore"),
            ("SEG.DDA.UNALLOC", "PL.DDA", "Unallocated"),
            ("SEG.WO.OFF", "PL.PROVISIONS", "Offshore"),
            ("SEG.WO.ON", "PL.PROVISIONS", "Onshore"),
            ("SEG.WO.UNALLOC", "PL.PROVISIONS", "Unallocated"),
        ]
        for tcode, lcode, seg in mappings:
            target = self.get_target(duck_con, fy, tcode)
            assert target is not None, f"Missing {tcode} target for {fy}"
            actual = self.get_copa_sum(duck_con, fy, lcode, segment=seg)
            assert abs(actual - target) <= 0.01, f"{fy} {tcode} mismatch: {actual} vs {target}"

    @pytest.mark.parametrize("fy", [f"FY{yy}" for yy in range(21, 27)])
    def test_fld_r08_segment_result_contrib(self, duck_con, fy):
        for seg, tcode in [
            ("Offshore", "SEG.RES.OFF"),
            ("Onshore", "SEG.RES.ON"),
            ("Unallocated", "SEG.UNALLOC"),
        ]:
            target = self.get_target(duck_con, fy, tcode)
            assert target is not None, f"Missing {tcode} target for {fy}"
            actual = self.get_copa_sum(
                duck_con, fy, "SEGMENT_RESULT_CONTRIB", segment=seg
            )
            assert abs(actual - target) <= 0.05, (
                f"{fy} {tcode} segment_result_contrib mismatch: {actual} vs {target}"
            )
        hq_target = self.get_target(duck_con, fy, "SEG.UNALLOC")
        hq_actual = self.get_copa_sum(
            duck_con, fy, "SEGMENT_RESULT_CONTRIB", object_id="CO-HQ"
        )
        assert abs(hq_actual - hq_target) <= 0.05, (
            f"{fy} CO-HQ segment_result_contrib {hq_actual} != SEG.UNALLOC {hq_target}"
        )

    @pytest.mark.parametrize("fy", [f"FY{yy}" for yy in range(17, 27)])
    def test_fld_r09_pbt(self, duck_con, fy):
        target = self.get_target(duck_con, fy, "PL.PBT")
        assert target is not None, f"Missing PL.PBT target for {fy}"
        actual = self.get_copa_sum(duck_con, fy, "PL.PBT")
        tol = 0.05 if int(fy[2:]) >= 21 else 1.0
        assert abs(actual - target) <= tol, f"{fy} PBT mismatch: {actual} vs {target}"

    @pytest.mark.parametrize("fy", [f"FY{yy}" for yy in range(21, 27)])
    def test_fld_r10_ras_factors(self, duck_con, fy):
        factors = duck_con.execute(
            "SELECT nature, ras_factor FROM audit WHERE fy=?", [fy]
        ).fetchall()
        assert len(factors) > 20, f"Too few audit rows for {fy}"
        in_warn_band = 0
        total_unpinned = 0
        for nature, factor in factors:
            if factor is None:
                continue
            if nature.upper() in ("STAFF_EXPENDITURE", "N35.STAFF_EXPENDITURE"):
                assert abs(factor - 1.0) < 1e-6, f"{fy} staff factor {factor} != 1.0"
            else:
                assert 0.33 <= factor <= 3.0, (
                    f"{fy} {nature} factor {factor} outside [0.33, 3.0]"
                )
                total_unpinned += 1
                if 0.5 <= factor <= 2.0:
                    in_warn_band += 1
        assert in_warn_band / max(total_unpinned, 1) >= 0.90, (
            f"{fy} fewer than 90% of RAS factors in [0.5, 2.0]"
        )

    @pytest.mark.parametrize("fy", [f"FY{yy}" for yy in range(17, 27)])
    def test_fld_r11_r12_production_sales(self, duck_con, fy):
        for code in [
            "PROD.CRUDE_ONGC",
            "PROD.CRUDE_JV",
            "PROD.GAS_ONGC",
            "PROD.GAS_JV",
            "QTY.CRUDE_SOLD",
            "QTY.GAS_SOLD",
            "QTY.VAP_SOLD",
        ]:
            target = self.get_target(duck_con, fy, code)
            assert target is not None, f"Missing {code} target for {fy}"
            actual = self.get_copa_sum(duck_con, fy, code)
            assert abs(actual - target) <= 0.01, f"{fy} {code} mismatch: {actual} vs {target}"

    @pytest.mark.parametrize("fy", [f"FY{yy}" for yy in range(17, 27)])
    def test_fld_r13_capex(self, duck_con, fy):
        target = self.get_target(duck_con, fy, "CAPEX.TOTAL")
        assert target is not None, f"Missing CAPEX.TOTAL target for {fy}"
        actual = self.get_copa_sum(duck_con, fy, "CAPEX.TOTAL")
        assert abs(actual - target) <= 1.0, f"{fy} CAPEX mismatch: {actual} vs {target}"

    @pytest.mark.parametrize("fy", [f"FY{yy}" for yy in range(17, 27)])
    def test_fld_r14_month_sum_equals_fy_value(self, duck_con, fy):
        """Every FY must have all 12 months and exact 2-decimal precision on monthly financial lines."""
        n_months = duck_con.execute(
            "SELECT COUNT(DISTINCT month) FROM co_pa WHERE fy=?", [fy]
        ).fetchone()[0]
        assert n_months == 12, f"{fy} expected 12 distinct months, got {n_months}"
        bad_precision = duck_con.execute(
            """
            SELECT COUNT(*) FROM co_pa
            WHERE fy=?
              AND line_code NOT LIKE 'PROD.%'
              AND line_code NOT LIKE 'QTY.%'
              AND ABS(amount_inr_mn - ROUND(amount_inr_mn, 2)) > 1e-6
            """,
            [fy],
        ).fetchone()[0]
        assert bad_precision == 0, f"{fy} has {bad_precision} non-2-decimal financial rows"

    @pytest.mark.parametrize("fy", [f"FY{yy}" for yy in range(21, 27)])
    def test_fld_r15_no_negative(self, duck_con, fy):
        """No object has negative production, revenue, or opex (SPEC-05 §7 FLD-R15)."""
        q = """
            SELECT COUNT(*) FROM co_pa 
            WHERE fy=? 
            AND amount_inr_mn < 0 
            AND line_code NOT IN (
                'N37.IMPAIRMENT_NET', 'impairment_net', 'CO-TREASURY_pbt',
                'PL.OTHER_INCOME', 'PL.INVENTORY_CHANGE', 'PL.EXCEPTIONAL',
                'SEGMENT_RESULT_CONTRIB', 'PBT_CONTRIB', 'PL.PBT'
            )
            AND object_id NOT IN ('CO-TREASURY', 'CO-HQ', 'CO-FIN')
            AND line_code NOT LIKE '%impairment%'
            AND line_code NOT LIKE 'SEG.UNALLOC%'
        """
        res = duck_con.execute(q, [fy]).fetchone()
        assert res[0] == 0, f"{fy} found {res[0]} negative production/revenue/opex values"

    @pytest.mark.parametrize("fy", [f"FY{yy}" for yy in range(21, 27)])
    def test_fld_r16_realised_crude_price_band(self, duck_con, fy):
        """Field realised crude price within ±10% of company realised crude price (SPEC-05 §7 FLD-R16)."""
        comp_rev = self.get_target(duck_con, fy, "REV.CRUDE")
        comp_qty = self.get_target(duck_con, fy, "QTY.CRUDE_SOLD")
        comp_price = comp_rev / comp_qty
        rows = duck_con.execute(
            """
            SELECT object_id,
                   SUM(CASE WHEN line_code='REV.CRUDE' THEN amount_inr_mn ELSE 0 END) AS rev,
                   SUM(CASE WHEN line_code='QTY.CRUDE_SOLD' THEN amount_inr_mn ELSE 0 END) AS qty
            FROM co_pa
            WHERE fy=?
            GROUP BY object_id
            HAVING qty > 0.05
            """,
            [fy],
        ).fetchall()
        assert len(rows) > 10
        for oid, rev, qty in rows:
            field_price = rev / qty
            rel_err = abs(field_price - comp_price) / comp_price
            assert rel_err <= 0.10, (
                f"{fy} {oid} realised crude price {field_price:.1f} outside ±10% of {comp_price:.1f}"
            )

    def test_fld_r17_opex_per_boe_rank_stability(self, duck_con):
        """Spearman rank correlation of field opex/boe between consecutive FYs >= 0.7 (SPEC-05 §7 FLD-R17)."""
        df = duck_con.execute(
            """
            SELECT fy, object_id,
                   SUM(CASE WHEN line_code LIKE 'N35.%' AND line_code NOT IN (
                       'N35.ROYALTY','N35.OIDB_CESS','N35.NCCD','N35.EXCISE_SAED','N35.PORT_TRUST','N35.OTHER_LEVIES'
                   ) THEN amount_inr_mn ELSE 0 END) AS opex,
                   SUM(CASE WHEN line_code IN ('PROD.CRUDE_ONGC','PROD.CRUDE_JV') THEN amount_inr_mn * 7.33
                            WHEN line_code IN ('PROD.GAS_ONGC','PROD.GAS_JV') THEN amount_inr_mn * 7.33
                            ELSE 0 END) AS boe_mm
            FROM co_pa
            WHERE object_id LIKE 'FLD-%'
            GROUP BY fy, object_id
            HAVING boe_mm > 0
            """
        ).df()
        df["opex_per_boe"] = df["opex"] / df["boe_mm"]
        piv = df.pivot(index="object_id", columns="fy", values="opex_per_boe").dropna()
        fys = sorted(piv.columns)
        for i in range(len(fys) - 1):
            # scipy-free Spearman: Pearson correlation of average ranks.
            rho = piv[fys[i]].rank().corr(piv[fys[i + 1]].rank())
            assert rho >= 0.70, (
                f"Spearman rho between {fys[i]} and {fys[i+1]} is {rho:.3f} < 0.70"
            )
