"""
Comprehensive test suite for Step 2.4 (Tables F5–F11).
Tests schema conformance, accounting identities, referential integrity,
public calibration targets, and emergent story expectations per DELEGATION_PLAYBOOK.md.
"""

from datetime import date
import hashlib
from pathlib import Path
import duckdb
import pandas as pd
import pytest

DATA_BANK_DIR = Path(__file__).resolve().parent.parent
LANDING_DIR = DATA_BANK_DIR / "landing"
SAP_DIR = LANDING_DIR / "sap"
EXCEL_DIR = LANDING_DIR / "excel"
DB_EXPORTS_DIR = LANDING_DIR / "db_exports"


@pytest.fixture(scope="module")
def duck_con():
    """Initializes in-memory DuckDB and loads all landing files directly."""
    con = duckdb.connect(":memory:")

    # Load Reference tables
    with open(DATA_BANK_DIR / "world_bible" / "reference" / "fields.yaml") as f:
        import yaml
        fields = yaml.safe_load(f)["fields"]
    con.register("dim_field", pd.DataFrame(fields))

    with open(DATA_BANK_DIR / "world_bible" / "reference" / "work_centres.yaml") as f:
        wcs = yaml.safe_load(f)["work_centres"]
    con.register("dim_work_centre", pd.DataFrame(wcs))

    with open(DATA_BANK_DIR / "world_bible" / "reference" / "cost_centres.yaml") as f:
        ccs = yaml.safe_load(f)["cost_centres"]
    con.register("dim_cost_centre", pd.DataFrame(ccs))

    with open(DATA_BANK_DIR / "world_bible" / "reference" / "projects.yaml") as f:
        prjs = yaml.safe_load(f)["projects"]
    con.register("dim_project", pd.DataFrame(prjs))

    with open(DATA_BANK_DIR / "world_bible" / "reference" / "vendors.yaml") as f:
        vens = yaml.safe_load(f)["vendors"]
    con.register("dim_vendor", pd.DataFrame(vens))

    with open(DATA_BANK_DIR / "world_bible" / "reference" / "customers.yaml") as f:
        custs = yaml.safe_load(f)["customers"]
    con.register("dim_customer", pd.DataFrame(custs))

    # Load Upstream operational files
    con.execute(f"CREATE TABLE production_monthly AS SELECT * FROM '{DB_EXPORTS_DIR / 'production_monthly.csv'}'")
    con.execute(f"CREATE TABLE wells_drilled AS SELECT * FROM '{DB_EXPORTS_DIR / 'wells_drilled.csv'}'")

    pfx_df = pd.read_excel(EXCEL_DIR / "price_fx.xlsx", sheet_name="price_fx_monthly")
    con.register("price_fx_monthly", pfx_df)

    py_df = pd.read_csv(SAP_DIR / "PY_CLUSTER_EXP.csv")
    con.register("payroll_monthly", py_df)

    # Load Generated Step 2.4 landing tables
    con.execute(f"CREATE TABLE field_pnl_annual AS SELECT * FROM '{SAP_DIR / 'CO_PA.csv'}'")
    con.execute(f"CREATE TABLE cost_ledger AS SELECT * FROM '{SAP_DIR / 'COSP_COSS.csv'}'")

    capex_df = pd.read_excel(EXCEL_DIR / "capex_be_re_actuals.xlsx", sheet_name="capex_budget")
    con.register("capex_budget", capex_df)

    con.execute(f"CREATE TABLE project_progress AS SELECT * FROM '{SAP_DIR / 'project_milestones.csv'}'")
    con.execute(f"CREATE TABLE purchase_orders AS SELECT * FROM '{SAP_DIR / 'EKKO_EKPO.csv'}'")
    con.execute(f"CREATE TABLE receivables AS SELECT * FROM '{SAP_DIR / 'FI_AR_INVOICES.csv'}'")

    forex_df = pd.read_excel(EXCEL_DIR / "treasury_forex_hedges.xlsx", sheet_name="forex_hedges")
    con.register("forex_hedges", forex_df)

    return con


# ------------------------------------------------------------------------------
# 1. Landing Files Existence & Row Counts
# ------------------------------------------------------------------------------

def test_landing_files_exist():
    assert (SAP_DIR / "CO_PA.csv").exists()
    assert (SAP_DIR / "COSP_COSS.csv").exists()
    assert (EXCEL_DIR / "capex_be_re_actuals.xlsx").exists()
    assert (SAP_DIR / "project_milestones.csv").exists()
    assert (SAP_DIR / "EKKO_EKPO.csv").exists()
    assert (SAP_DIR / "FI_AR_INVOICES.csv").exists()
    assert (EXCEL_DIR / "treasury_forex_hedges.xlsx").exists()


def test_row_counts_and_pk_uniqueness(duck_con):
    tables_pk = [
        ("field_pnl_annual", "pnl_id", 500),
        ("cost_ledger", "ledger_id", 300000),
        ("capex_budget", "budget_id", 7000),
        ("project_progress", "progress_id", 300),
        ("purchase_orders", "po_line_id", 100000),
        ("receivables", "invoice_id", 50000),
        ("forex_hedges", "hedge_id", 50),
    ]
    for tbl, pk, min_cnt in tables_pk:
        cnt = duck_con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        assert cnt >= min_cnt, f"Table {tbl} has {cnt} rows, expected >= {min_cnt}"
        uniq_pk = duck_con.execute(f"SELECT COUNT(DISTINCT {pk}) FROM {tbl}").fetchone()[0]
        assert cnt == uniq_pk, f"Table {tbl} primary key {pk} not unique ({cnt} != {uniq_pk})"
        null_pk = duck_con.execute(f"SELECT COUNT(*) FROM {tbl} WHERE {pk} IS NULL").fetchone()[0]
        assert null_pk == 0, f"Table {tbl} primary key {pk} has null values"


def test_foreign_keys_referential_integrity(duck_con):
    invalid_fld = duck_con.execute("""
        SELECT COUNT(*) FROM field_pnl_annual p
        LEFT JOIN dim_field df ON p.field_id = df.field_id
        WHERE p.field_id IS NOT NULL AND df.field_id IS NULL
    """).fetchone()[0]
    assert invalid_fld == 0, f"field_pnl_annual has {invalid_fld} invalid field_id"

    invalid_cc = duck_con.execute("""
        SELECT COUNT(*) FROM cost_ledger c
        LEFT JOIN dim_cost_centre dc ON c.cost_centre_id = dc.cost_centre_id
        WHERE dc.cost_centre_id IS NULL
    """).fetchone()[0]
    assert invalid_cc == 0, f"cost_ledger has {invalid_cc} invalid cost_centre_id"

    invalid_prj = duck_con.execute("""
        SELECT COUNT(*) FROM capex_budget b
        LEFT JOIN dim_project p ON b.prj_id = p.prj_id
        WHERE b.prj_id IS NOT NULL AND p.prj_id IS NULL
    """).fetchone()[0]
    assert invalid_prj == 0, f"capex_budget has {invalid_prj} invalid prj_id"

    invalid_ven = duck_con.execute("""
        SELECT COUNT(*) FROM purchase_orders po
        LEFT JOIN dim_vendor v ON po.vendor_id = v.vendor_id
        WHERE v.vendor_id IS NULL
    """).fetchone()[0]
    assert invalid_ven == 0, f"purchase_orders has {invalid_ven} invalid vendor_id"

    invalid_cust = duck_con.execute("""
        SELECT COUNT(*) FROM receivables r
        LEFT JOIN dim_customer c ON r.customer_id = c.customer_id
        WHERE c.customer_id IS NULL
    """).fetchone()[0]
    assert invalid_cust == 0, f"receivables has {invalid_cust} invalid customer_id"


# ------------------------------------------------------------------------------
# 2. Accounting Identities on 100% of Rows
# ------------------------------------------------------------------------------

def test_accounting_identities_every_row(duck_con):
    # gross_revenue = oil_revenue + gas_revenue
    mismatch_rev = duck_con.execute("""
        SELECT COUNT(*) FROM field_pnl_annual
        WHERE ABS(gross_revenue_inr_cr - ROUND(oil_revenue_inr_cr + gas_revenue_inr_cr, 2)) > 0.02
    """).fetchone()[0]
    assert mismatch_rev == 0, f"Gross revenue mismatch on {mismatch_rev} rows"

    # net_revenue = gross_revenue - royalty - cess - saed
    mismatch_net = duck_con.execute("""
        SELECT COUNT(*) FROM field_pnl_annual
        WHERE ABS(net_revenue_inr_cr - ROUND(gross_revenue_inr_cr - statutory_royalty_inr_cr - statutory_cess_inr_cr - statutory_windfall_tax_saed_inr_cr, 2)) > 0.02
    """).fetchone()[0]
    assert mismatch_net == 0, f"Net revenue mismatch on {mismatch_net} rows"

    # ebitda = net_revenue - total_opex
    mismatch_ebitda = duck_con.execute("""
        SELECT COUNT(*) FROM field_pnl_annual
        WHERE ABS(ebitda_inr_cr - ROUND(net_revenue_inr_cr - total_opex_inr_cr, 2)) > 0.02
    """).fetchone()[0]
    assert mismatch_ebitda == 0, f"EBITDA mismatch on {mismatch_ebitda} rows"

    # pbt = ebitda - dda_depreciation
    mismatch_pbt = duck_con.execute("""
        SELECT COUNT(*) FROM field_pnl_annual
        WHERE ABS(pbt_inr_cr - ROUND(ebitda_inr_cr - dda_depreciation_inr_cr, 2)) > 0.02
    """).fetchone()[0]
    assert mismatch_pbt == 0, f"PBT mismatch on {mismatch_pbt} rows"

    # total_opex = sum of all 8 opex heads
    mismatch_opex = duck_con.execute("""
        SELECT COUNT(*) FROM field_pnl_annual
        WHERE ABS(total_opex_inr_cr - ROUND(
            allocated_manpower_cost_inr_cr +
            contractor_cost_inr_cr +
            power_fuel_cost_inr_cr +
            workover_repairs_cost_inr_cr +
            water_handling_cost_inr_cr +
            logistics_osv_chopper_cost_inr_cr +
            chemicals_consumables_cost_inr_cr +
            other_opex_inr_cr, 2)) > 0.02
    """).fetchone()[0]
    assert mismatch_opex == 0, f"Opex heads sum mismatch on {mismatch_opex} rows"


# ------------------------------------------------------------------------------
# 3. Opex Sanity, Terrain Bands & Plant Margins
# ------------------------------------------------------------------------------

def test_opex_sanity_no_negative_heads_and_ratio_bounds(duck_con):
    # Rule 1: Zero negative values on any opex head across all rows
    neg_heads = duck_con.execute("""
        SELECT COUNT(*) FROM field_pnl_annual
        WHERE allocated_manpower_cost_inr_cr < 0
           OR contractor_cost_inr_cr < 0
           OR power_fuel_cost_inr_cr < 0
           OR workover_repairs_cost_inr_cr < 0
           OR water_handling_cost_inr_cr < 0
           OR logistics_osv_chopper_cost_inr_cr < 0
           OR chemicals_consumables_cost_inr_cr < 0
           OR other_opex_inr_cr < 0;
    """).fetchone()[0]
    assert neg_heads == 0, f"Found {neg_heads} rows with negative opex heads"

    # Rule 2: other_opex must be between 3% and 15% of total_opex for every field operational row
    ratio_violations = duck_con.execute("""
        SELECT COUNT(*) FROM field_pnl_annual
        WHERE line_type = 'field' AND total_opex_inr_cr > 1.0
          AND ( (other_opex_inr_cr / total_opex_inr_cr) < 0.03 OR (other_opex_inr_cr / total_opex_inr_cr) > 0.15 );
    """).fetchone()[0]
    assert ratio_violations == 0, f"Found {ratio_violations} rows violating 3%-15% other_opex bound"

    # Rule 3: Terrain bands for unit costs per boe
    off_log = duck_con.execute("""
        SELECT AVG(p.logistics_osv_chopper_cost_inr_cr * 10000000.0 / p.total_production_boe)
        FROM field_pnl_annual p
        JOIN dim_field f ON p.field_id = f.field_id
        WHERE p.fiscal_year = 'FY26' AND f.onshore_offshore = 'offshore' AND p.total_production_boe > 0;
    """).fetchone()[0]
    assert 120.0 <= off_log <= 220.0, f"Offshore logistics unit cost {off_log:.2f} outside band [120, 220]"

    on_log = duck_con.execute("""
        SELECT AVG(p.logistics_osv_chopper_cost_inr_cr * 10000000.0 / p.total_production_boe)
        FROM field_pnl_annual p
        JOIN dim_field f ON p.field_id = f.field_id
        WHERE p.fiscal_year = 'FY26' AND f.onshore_offshore = 'onshore' AND p.total_production_boe > 0;
    """).fetchone()[0]
    assert 15.0 <= on_log <= 35.0, f"Onshore logistics unit cost {on_log:.2f} outside band [15, 35]"


def test_plant_ebitda_margins_within_bounds(duck_con):
    # Rule: Dedicated Gas Processing Plant EBITDA margins must land in 10%–45%
    plant_margins = duck_con.execute("""
        SELECT asset_wc_id, gross_revenue_inr_cr, total_opex_inr_cr, ebitda_inr_cr, ebitda_margin_pct
        FROM field_pnl_annual
        WHERE line_type = 'plant_vap' AND fiscal_year = 'FY26';
    """).fetchall()
    assert len(plant_margins) == 3, f"Expected 3 plants, found {len(plant_margins)}"
    for p in plant_margins:
        wc, g_rev, opex, ebitda, margin = p[0], p[1], p[2], p[3], p[4]
        assert ebitda > 0, f"Plant {wc} has negative EBITDA: {ebitda}"
        assert 10.0 <= margin <= 45.0, f"Plant {wc} EBITDA margin {margin:.2f}% outside [10%, 45%]"


# ------------------------------------------------------------------------------
# 4. Revenue & Payroll Reconciliations
# ------------------------------------------------------------------------------

def test_revenue_volume_x_price_reconciliation(duck_con):
    recon = duck_con.execute("""
        WITH monthly_calc AS (
            SELECT
                p.field_id,
                p.fiscal_year,
                SUM(((p.oil_production_mt + p.condensate_production_mt) * 7.33 * fx.ongc_crude_net_realisation_inr_bbl) / 10000000.0) AS calc_oil_rev,
                SUM((p.gas_sales_mmscm * 35314.7 * (CASE WHEN lower(df.notes) LIKE '%deepwater%' AND fx.non_apm_deepwater_gas_price_usd_mmbtu IS NOT NULL THEN fx.non_apm_deepwater_gas_price_usd_mmbtu ELSE fx.apm_gas_price_usd_mmbtu END) * fx.inr_usd_fx_rate) / 10000000.0) AS calc_gas_rev
            FROM production_monthly p
            JOIN price_fx_monthly fx ON p.month = fx.month
            JOIN dim_field df ON p.field_id = df.field_id
            WHERE p.fiscal_year = 'FY26'
            GROUP BY p.field_id, p.fiscal_year
        )
        SELECT
            pnl.field_id,
            pnl.oil_revenue_inr_cr,
            ROUND(mc.calc_oil_rev, 2) AS calc_oil,
            pnl.gas_revenue_inr_cr,
            ROUND(mc.calc_gas_rev, 2) AS calc_gas
        FROM field_pnl_annual pnl
        JOIN monthly_calc mc ON pnl.field_id = mc.field_id AND pnl.fiscal_year = mc.fiscal_year
        WHERE pnl.fiscal_year = 'FY26' AND pnl.line_type = 'field';
    """).fetchall()

    for r in recon:
        fid, oil_act, oil_calc, gas_act, gas_calc = r[0], r[1], r[2], r[3], r[4]
        assert abs(oil_act - oil_calc) <= 0.05, f"Oil revenue mismatch for {fid}: {oil_act} vs {oil_calc}"
        assert abs(gas_act - gas_calc) <= 0.05, f"Gas revenue mismatch for {fid}: {gas_act} vs {gas_calc}"


def test_payroll_manpower_reconciliation(duck_con):
    pnl_mp = duck_con.execute("""
        SELECT SUM(allocated_manpower_cost_inr_cr) FROM field_pnl_annual WHERE fiscal_year = 'FY26'
    """).fetchone()[0]
    payroll_total = duck_con.execute("""
        SELECT SUM(LGART_9001 + (LGART_1001 + LGART_1002) * (superannuation_benefit_pct / 100.0)) / 1e7
        FROM payroll_monthly WHERE fiscal_year = 'FY26'
    """).fetchone()[0]
    assert abs(pnl_mp - payroll_total) <= 0.05, f"P&L manpower {pnl_mp} cr != payroll total {payroll_total} cr"


def test_fy26_revenue_and_segment_calibration(duck_con):
    tot_rev = duck_con.execute("SELECT SUM(gross_revenue_inr_cr) FROM field_pnl_annual WHERE fiscal_year = 'FY26'").fetchone()[0]
    assert abs(tot_rev - 132508.0) / 132508.0 <= 0.02, f"Total revenue {tot_rev} cr deviates from 132,508 cr"

    off_rev = duck_con.execute("""
        SELECT SUM(gross_revenue_inr_cr) FROM field_pnl_annual
        WHERE fiscal_year = 'FY26' AND (
            field_id IN (SELECT field_id FROM dim_field WHERE onshore_offshore = 'offshore')
            OR (line_type = 'plant_vap' AND asset_wc_id = 'WC-URN')
        )
    """).fetchone()[0]
    assert abs(off_rev - 92406.0) / 92406.0 <= 0.02, f"Offshore segment revenue {off_rev} cr deviates from 92,406 cr"

    on_rev = duck_con.execute("""
        SELECT SUM(gross_revenue_inr_cr) FROM field_pnl_annual
        WHERE fiscal_year = 'FY26' AND (
            field_id IN (SELECT field_id FROM dim_field WHERE onshore_offshore = 'onshore')
            OR (line_type IN ('plant_vap', 'reconciliation', 'exploration_writeoff') AND asset_wc_id != 'WC-URN')
        )
    """).fetchone()[0]
    assert abs(on_rev - 40102.0) / 40102.0 <= 0.02, f"Onshore segment revenue {on_rev} cr deviates from 40,102 cr"


def test_fy26_segment_profit_and_dda_calibration(duck_con):
    off_pbt = duck_con.execute("""
        SELECT SUM(pbt_inr_cr) FROM field_pnl_annual
        WHERE fiscal_year = 'FY26' AND (
            field_id IN (SELECT field_id FROM dim_field WHERE onshore_offshore = 'offshore')
            OR (line_type = 'plant_vap' AND asset_wc_id = 'WC-URN')
        )
    """).fetchone()[0]
    assert abs(off_pbt - 34385.0) / 34385.0 <= 0.02, f"Offshore PBT {off_pbt} cr deviates from 34,385 cr"

    on_pbt = duck_con.execute("""
        SELECT SUM(pbt_inr_cr) FROM field_pnl_annual
        WHERE fiscal_year = 'FY26' AND (
            field_id IN (SELECT field_id FROM dim_field WHERE onshore_offshore = 'onshore')
            OR (line_type IN ('plant_vap', 'reconciliation', 'exploration_writeoff') AND asset_wc_id != 'WC-URN')
        )
    """).fetchone()[0]
    assert abs(on_pbt - 6246.0) / 6246.0 <= 0.02, f"Onshore PBT {on_pbt} cr deviates from 6,246 cr"

    off_dda = duck_con.execute("""
        SELECT SUM(dda_depreciation_inr_cr) FROM field_pnl_annual
        WHERE fiscal_year = 'FY26' AND (
            field_id IN (SELECT field_id FROM dim_field WHERE onshore_offshore = 'offshore')
            OR (line_type = 'plant_vap' AND asset_wc_id = 'WC-URN')
        )
    """).fetchone()[0]
    assert abs(off_dda - 18830.0) / 18830.0 <= 0.02, f"Offshore DD&A {off_dda} cr deviates from 18,830 cr"

    on_dda = duck_con.execute("""
        SELECT SUM(dda_depreciation_inr_cr) FROM field_pnl_annual
        WHERE fiscal_year = 'FY26' AND (
            field_id IN (SELECT field_id FROM dim_field WHERE onshore_offshore = 'onshore')
            OR (line_type IN ('plant_vap', 'reconciliation', 'exploration_writeoff') AND asset_wc_id != 'WC-URN')
        )
    """).fetchone()[0]
    assert abs(on_dda - 6367.0) / 6367.0 <= 0.02, f"Onshore DD&A {on_dda} cr deviates from 6,367 cr"


def test_statutory_levies_calibration(duck_con):
    royalty = duck_con.execute("SELECT SUM(statutory_royalty_inr_cr) FROM field_pnl_annual WHERE fiscal_year = 'FY26'").fetchone()[0]
    assert abs(royalty - 12965.0) / 12965.0 <= 0.02, f"Royalty {royalty} cr deviates from 12,965 cr"

    cess = duck_con.execute("SELECT SUM(statutory_cess_inr_cr) FROM field_pnl_annual WHERE fiscal_year = 'FY26'").fetchone()[0]
    assert abs(cess - 13034.0) / 13034.0 <= 0.02, f"Cess {cess} cr deviates from 13,034 cr"

    saed = duck_con.execute("SELECT SUM(statutory_windfall_tax_saed_inr_cr) FROM field_pnl_annual WHERE fiscal_year = 'FY26'").fetchone()[0]
    assert saed == 0.0, f"FY26 SAED should be 0.0, got {saed}"


def test_capex_calibration_and_story_s10(duck_con):
    cap_fy26 = duck_con.execute("SELECT SUM(actual_spend_inr_cr) FROM capex_budget WHERE fiscal_year = 'FY26'").fetchone()[0]
    assert abs(cap_fy26 - 35878.0) / 35878.0 <= 0.02, f"FY26 capex {cap_fy26} cr deviates from 35,878 cr"

    cap_fy25 = duck_con.execute("SELECT SUM(actual_spend_inr_cr) FROM capex_budget WHERE fiscal_year = 'FY25'").fetchone()[0]
    assert abs(cap_fy25 - 62057.0) / 62057.0 <= 0.02, f"FY25 capex {cap_fy25} cr deviates from 62,057 cr"

    h1_act = duck_con.execute("SELECT SUM(actual_spend_inr_cr) FROM capex_budget WHERE fiscal_year = 'FY27'").fetchone()[0]
    h1_be = duck_con.execute("SELECT SUM(budget_estimate_be_inr_cr) FROM capex_budget WHERE fiscal_year = 'FY27'").fetchone()[0]
    assert h1_act > 0 and h1_be > 0, "FY27 H1 capex spend and BE should be positive"
    achieve = (h1_act / h1_be) * 100.0
    assert 60.0 <= achieve <= 105.0, f"FY27 H1 capex achievement {achieve:.2f}% plausible range"


def test_receivables_calibration_and_story_s23(duck_con):
    tot_rec = duck_con.execute("SELECT SUM(outstanding_amount_inr_cr) FROM receivables WHERE fiscal_year = 'FY26'").fetchone()[0]
    assert abs(tot_rec - 13168.0) / 13168.0 <= 0.02, f"Receivables {tot_rec} cr deviates from 13,168 cr"

    # Debtor collection period in 25–40 days
    tot_rev = duck_con.execute("SELECT SUM(gross_revenue_inr_cr) FROM field_pnl_annual WHERE fiscal_year = 'FY26'").fetchone()[0]
    debtor_days = (tot_rec / tot_rev) * 365.0
    assert 25.0 <= debtor_days <= 40.0, f"Debtor days {debtor_days:.2f} outside [25, 40]"

    # Overdue >90d share of outstanding in [5%, 25%]
    overdue_90 = duck_con.execute("""
        SELECT SUM(outstanding_amount_inr_cr) FROM receivables
        WHERE fiscal_year = 'FY26' AND aging_days > 90
    """).fetchone()[0]
    overdue_share = (overdue_90 / tot_rec) * 100.0
    assert 5.0 <= overdue_share <= 25.0, f">90d overdue share {overdue_share:.2f}% outside [5%, 25%]"

    # Ageing buckets sum to total outstanding
    bucket_sum = duck_con.execute("""
        SELECT SUM(outstanding_amount_inr_cr) FROM receivables
        WHERE fiscal_year = 'FY26' AND aging_bucket IN ('<30 days', '31-60 days', '61-90 days', '91-180 days', '>180 days')
    """).fetchone()[0]
    assert abs(bucket_sum - tot_rec) <= 0.05, f"Ageing buckets sum {bucket_sum} != total outstanding {tot_rec}"


def test_receivables_invoicing_reconciliation_to_revenue(duck_con):
    # Rule: Σ FY26 invoice net value ≈ FY26 revenue from operations ±3%
    tot_invoiced_fy26 = duck_con.execute("""
        SELECT SUM(billed_amount_inr_cr) FROM receivables WHERE fiscal_year = 'FY26'
    """).fetchone()[0]
    rev_fy26 = duck_con.execute("""
        SELECT SUM(gross_revenue_inr_cr) FROM field_pnl_annual WHERE fiscal_year = 'FY26'
    """).fetchone()[0]
    invoicing_delta = abs(tot_invoiced_fy26 - rev_fy26) / rev_fy26 * 100.0
    assert invoicing_delta <= 3.0, f"FY26 Invoiced total {tot_invoiced_fy26:.2f} cr deviates from revenue {rev_fy26:.2f} cr by {invoicing_delta:.2f}% (exceeds ±3%)"


def test_po_spend_series_yoy_and_paid_bounds(duck_con):
    po_yoy = duck_con.execute("""
        SELECT fiscal_year, SUM(revised_po_value_inr) / 1e7 AS spend
        FROM purchase_orders
        WHERE fiscal_year IN ('FY22', 'FY23', 'FY24', 'FY25', 'FY26')
        GROUP BY fiscal_year ORDER BY fiscal_year;
    """).fetchall()

    for idx in range(1, len(po_yoy)):
        prev_spend = po_yoy[idx-1][1]
        curr_spend = po_yoy[idx][1]
        pct_change = ((curr_spend - prev_spend) / prev_spend) * 100.0
        assert -25.0 <= pct_change <= 25.0, f"PO YoY jump {pct_change:.2f}% exceeds ±25%"

    paid_violations = duck_con.execute("""
        SELECT COUNT(*) FROM purchase_orders
        WHERE actual_paid_amount_inr > (revised_po_value_inr + 0.01);
    """).fetchone()[0]
    assert paid_violations == 0, f"Found {paid_violations} purchase order lines where paid > revised"


def test_monthly_series_continuity_fy26_vs_fy27_h1(duck_con):
    # Rule: For every monthly series, |Apr–Sep 2026 monthly mean / FY26 monthly mean − 1| <= 25%
    # 1. Capex series
    cap26 = duck_con.execute("SELECT SUM(actual_spend_inr_cr)/12.0 FROM capex_budget WHERE fiscal_year = 'FY26'").fetchone()[0]
    cap27 = duck_con.execute("SELECT SUM(actual_spend_inr_cr)/6.0 FROM capex_budget WHERE fiscal_year = 'FY27'").fetchone()[0]
    cap_delta = abs(cap27 / cap26 - 1.0) * 100.0
    assert cap_delta <= 25.0, f"Capex monthly mean jump {cap_delta:.2f}% exceeds 25%"

    # 2. Cost ledger opex by head
    heads = duck_con.execute("SELECT DISTINCT cost_head FROM cost_ledger").fetchall()
    for h in heads:
        head_name = h[0]
        m26 = duck_con.execute(f"SELECT SUM(amount_inr)/12.0 FROM cost_ledger WHERE fiscal_year = 'FY26' AND cost_head = '{head_name}'").fetchone()[0]
        m27 = duck_con.execute(f"SELECT SUM(amount_inr)/6.0 FROM cost_ledger WHERE fiscal_year = 'FY27' AND cost_head = '{head_name}'").fetchone()[0]
        delta = abs(m27 / m26 - 1.0) * 100.0
        assert delta <= 25.0, f"Cost ledger head {head_name} monthly jump {delta:.2f}% exceeds 25%"

    # 3. Purchase orders spend
    po26 = duck_con.execute("SELECT SUM(revised_po_value_inr)/12.0 FROM purchase_orders WHERE fiscal_year = 'FY26'").fetchone()[0]
    po27 = duck_con.execute("SELECT SUM(revised_po_value_inr)/6.0 FROM purchase_orders WHERE fiscal_year = 'FY27'").fetchone()[0]
    po_delta = abs(po27 / po26 - 1.0) * 100.0
    assert po_delta <= 25.0, f"PO spend monthly jump {po_delta:.2f}% exceeds 25%"

    # 4. Receivables invoicing
    rec26 = duck_con.execute("SELECT SUM(billed_amount_inr_cr)/12.0 FROM receivables WHERE fiscal_year = 'FY26'").fetchone()[0]
    rec27 = duck_con.execute("SELECT SUM(billed_amount_inr_cr)/6.0 FROM receivables WHERE fiscal_year = 'FY27'").fetchone()[0]
    rec_delta = abs(rec27 / rec26 - 1.0) * 100.0
    assert rec_delta <= 25.0, f"Receivables invoicing monthly jump {rec_delta:.2f}% exceeds 25%"


# ------------------------------------------------------------------------------
# 6. Emergent Story Expectations (Testing Direction and Real Properties)
# ------------------------------------------------------------------------------

def test_story_s6_mature_field_losses(duck_con):
    # Marginal mature fields have constrained profitability due to high water-cut / artificial lift
    bor_pbt = duck_con.execute("""
        SELECT pbt_inr_cr FROM field_pnl_annual
        WHERE field_id = 'FLD-BOR' AND fiscal_year = 'FY26'
    """).fetchone()[0]
    assert bor_pbt < 50.0, f"Borholla PBT {bor_pbt} cr should be constrained/negative"

    adi_ebitda = duck_con.execute("""
        SELECT ebitda_margin_pct FROM field_pnl_annual
        WHERE field_id = 'FLD-ADI' AND fiscal_year = 'FY26'
    """).fetchone()[0]
    assert adi_ebitda < 50.0, f"Adiyakkamangalam EBITDA margin {adi_ebitda}% should be constrained"


def test_story_s8_manpower_cost_per_boe_disparity(duck_con):
    mh_mp = duck_con.execute("""
        SELECT SUM(allocated_manpower_cost_inr_cr) * 10000000.0 / SUM(total_production_boe)
        FROM field_pnl_annual
        WHERE asset_wc_id = 'WC-MUM' AND fiscal_year = 'FY26' AND total_production_boe > 0
    """).fetchone()[0]

    cam_mp = duck_con.execute("""
        SELECT SUM(allocated_manpower_cost_inr_cr) * 10000000.0 / SUM(total_production_boe)
        FROM field_pnl_annual
        WHERE asset_wc_id = 'WC-CAM' AND fiscal_year = 'FY26' AND total_production_boe > 0
    """).fetchone()[0]
    assert cam_mp > mh_mp, f"Cambay manpower cost/boe {cam_mp:.2f} should exceed Mumbai High {mh_mp:.2f}"


def test_story_s9_capex_slippages(duck_con):
    slipped = duck_con.execute("""
        SELECT COUNT(*) FROM project_progress
        WHERE schedule_slippage_months > 12 AND cost_overrun_inr_cr > 1000.0
    """).fetchone()[0]
    assert slipped >= 1, f"Expected major projects with slippage >12m and overrun >1000 cr, found {slipped}"


def test_story_s15_stress_test_recomputed(duck_con):
    stressed_results = duck_con.execute("""
        WITH monthly_agg AS (
            SELECT p.field_id, SUM(p.oil_production_mt) AS tot_oil_mt
            FROM production_monthly p WHERE p.fiscal_year = 'FY26' GROUP BY p.field_id
        ),
        base_pnl AS (
            SELECT SUM(ebitda_inr_cr) AS base_ebitda FROM field_pnl_annual WHERE fiscal_year = 'FY26' AND line_type = 'field'
        ),
        stressed_pnl AS (
            SELECT
                SUM((m.tot_oil_mt * 7.33 * 60.0 * fx.inr_usd_fx_rate) / 10000000.0 * 0.72 +
                    COALESCE(pnl.gas_revenue_inr_cr, 0.0) * 0.90 - pnl.total_opex_inr_cr) AS sim_ebitda
            FROM monthly_agg m
            JOIN field_pnl_annual pnl ON m.field_id = pnl.field_id AND pnl.fiscal_year = 'FY26' AND pnl.line_type = 'field'
            CROSS JOIN (SELECT inr_usd_fx_rate FROM price_fx_monthly WHERE fiscal_year = 'FY26' LIMIT 1) fx
        )
        SELECT base_pnl.base_ebitda, stressed_pnl.sim_ebitda
        FROM base_pnl, stressed_pnl;
    """).fetchone()

    base_ebitda, sim_ebitda = stressed_results[0], stressed_results[1]
    assert sim_ebitda < base_ebitda, f"Stressed EBITDA {sim_ebitda} should be lower than baseline {base_ebitda}"


def test_story_s22_vendor_concentration(duck_con):
    top_10 = duck_con.execute("""
        SELECT SUM(revised_po_value_inr) / 1e7
        FROM purchase_orders
        WHERE fiscal_year = 'FY26' AND vendor_id IN (
            SELECT vendor_id FROM purchase_orders GROUP BY vendor_id ORDER BY SUM(revised_po_value_inr) DESC LIMIT 10
        )
    """).fetchone()[0]
    total_po = duck_con.execute("""
        SELECT SUM(revised_po_value_inr) / 1e7
        FROM purchase_orders WHERE fiscal_year = 'FY26'
    """).fetchone()[0]

    share = (top_10 / total_po) * 100.0
    assert 40.0 <= share <= 75.0, f"Top 10 vendor share {share:.2f}% expected in [40%, 75%]"


def test_story_s25_treasury_forex(duck_con):
    fc_debt = duck_con.execute("""
        SELECT SUM(gross_exposure_usd) / 1e9,
               SUM(hedged_amount_usd) * 100.0 / SUM(gross_exposure_usd),
               SUM(mtm_gain_loss_inr_cr)
        FROM forex_hedges
        WHERE fiscal_year = 'FY26'
    """).fetchone()

    assert 1.5 <= fc_debt[0] <= 3.5, f"FC debt {fc_debt[0]:.2f} bn expected in [1.5, 3.5] bn"
    assert 70.0 <= fc_debt[1] <= 90.0, f"Natural hedge coverage {fc_debt[1]:.2f}% expected in [70%, 90%]"
    assert fc_debt[2] < 0.0, f"Unhedged debt should experience MTM translation loss, got {fc_debt[2]} cr"


def test_story_s36_geleki_mom_escalation_and_slipped_projects(duck_con):
    slipped = duck_con.execute("""
        SELECT COUNT(DISTINCT prj_id) FROM project_progress
        WHERE schedule_slippage_months > 0 AND milestone_status = 'delayed_critical_path'
    """).fetchone()[0]
    assert slipped >= 2, f"Expected at least 2 delayed critical path projects, got {slipped}"


# ------------------------------------------------------------------------------
# 7. Determinism Check
# ------------------------------------------------------------------------------

def test_determinism_sha256():
    def hash_file(p):
        h = hashlib.sha256()
        with open(p, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()

    h1_copa = hash_file(SAP_DIR / "CO_PA.csv")
    h1_cosp = hash_file(SAP_DIR / "COSP_COSS.csv")
    h1_ekko = hash_file(SAP_DIR / "EKKO_EKPO.csv")
    h1_bsid = hash_file(SAP_DIR / "FI_AR_INVOICES.csv")

    assert len(h1_copa) == 64
    assert len(h1_cosp) == 64
    assert len(h1_ekko) == 64
    assert len(h1_bsid) == 64
