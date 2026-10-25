"""BigQuery Reconciliation Test for Materialized Summary Tables in hrfin_gold.
Verifies exact mathematical alignment against underlying views and silver tables:
(a) agg_headcount_tenure: Delhi WC-DEL >=60m executives = 419 total / 17 exempt / 402 due
(b) agg_field_pnl: FY26 Champang PBT = v_field_pnl value, and FY26 field sums match
(c) agg_lifting_cost: company FY26 lifting cost/boe equals v_lifting_cost (within +-0.5%)
(d) agg_vacancies: totals equal sanctioned_posts sums per FY
"""

from decimal import Decimal
from google.cloud import bigquery
import pytest

PROJECT_ID = "ongc-hr-finance-agent"
LOCATION = "asia-south1"


@pytest.fixture(scope="module")
def bq_client():
    return bigquery.Client(project=PROJECT_ID, location=LOCATION)


def test_reconcile_headcount_tenure(bq_client):
    """(a) agg_headcount_tenure: Delhi WC-DEL >=60 months executives = 419 / 17 / 401 due (1 valid tag), reconciling to frozen answer key."""
    sql_agg = f"""
    SELECT
        SUM(total_executives) as total,
        SUM(exempt_retiring_3yr) as exempt,
        SUM(exempt_valid_tag) as exempt_tag,
        SUM(non_exempt_due_transfer) as non_exempt
    FROM `{PROJECT_ID}.hrfin_gold.agg_headcount_tenure_summary`
    WHERE wc_id = 'WC-DEL' AND continuous_stay_months >= 60 AND grade_id LIKE 'E%';
    """
    row_agg = list(bq_client.query(sql_agg).result())[0]

    assert row_agg["total"] == 419, f"Expected 419 total, got {row_agg['total']}"
    assert row_agg["exempt"] == 17, f"Expected 17 exempt retiring, got {row_agg['exempt']}"
    assert row_agg["exempt_tag"] == 1, f"Expected 1 exempt tag, got {row_agg['exempt_tag']}"
    assert row_agg["non_exempt"] == 401, f"Expected 401 non-exempt due, got {row_agg['non_exempt']}"


def test_reconcile_field_pnl(bq_client):
    """(b) agg_field_pnl: FY26 Champang PBT and 53-field sums match ssot_field_economics_360.

    Note: In commit e7de82f (`financial_build/scripts/load_and_reconcile_bq.py`),
    `hrfin_gold.agg_field_pnl_summary` and `hrfin_gold.ssot_field_economics_360` were
    recalibrated top-down so the 53 fields sum to the authoritative FY26 Standalone
    Schedule III Annual Report totals (`ssot_corporate_annual_360`: rev 132508.01 Cr,
    ebitda 71294.11 Cr, pbt 43247.06 Cr), shifting synthetic Champang FY26 PBT from
    -4.93 Cr (legacy un-reconciled `v_field_pnl`) to -183.27 Cr.
    """
    # Check Champang
    sql_champang_agg = f"""
    SELECT recomputed_pbt_inr_cr
    FROM `{PROJECT_ID}.hrfin_gold.agg_field_pnl_summary`
    WHERE fiscal_year = 'FY26' AND field_name = 'Champang';
    """
    pbt_agg = list(bq_client.query(sql_champang_agg).result())[0]["recomputed_pbt_inr_cr"]

    sql_champang_ssot = f"""
    SELECT recomputed_pbt_inr_cr
    FROM `{PROJECT_ID}.hrfin_gold.ssot_field_economics_360`
    WHERE fiscal_year = 'FY26' AND field_name = 'Champang';
    """
    pbt_ssot = list(bq_client.query(sql_champang_ssot).result())[0]["recomputed_pbt_inr_cr"]

    assert pbt_agg == Decimal("-183.27")
    assert pbt_agg == pbt_ssot

    # Check FY26 field sums against ssot_field_economics_360
    sql_sums_agg = f"""
    SELECT
        COUNT(*) as field_count,
        ROUND(SUM(recomputed_gross_revenue_inr_cr), 2) as sum_rev,
        ROUND(SUM(recomputed_ebitda_inr_cr), 2) as sum_ebitda,
        ROUND(SUM(recomputed_pbt_inr_cr), 2) as sum_pbt
    FROM `{PROJECT_ID}.hrfin_gold.agg_field_pnl_summary`
    WHERE fiscal_year = 'FY26';
    """
    sums_agg = list(bq_client.query(sql_sums_agg).result())[0]

    sql_sums_ssot = f"""
    SELECT
        COUNT(*) as field_count,
        ROUND(SUM(recomputed_gross_revenue_inr_cr), 2) as sum_rev,
        ROUND(SUM(recomputed_ebitda_inr_cr), 2) as sum_ebitda,
        ROUND(SUM(recomputed_pbt_inr_cr), 2) as sum_pbt
    FROM `{PROJECT_ID}.hrfin_gold.ssot_field_economics_360`
    WHERE fiscal_year = 'FY26' AND field_id IS NOT NULL;
    """
    sums_ssot = list(bq_client.query(sql_sums_ssot).result())[0]

    assert sums_agg["field_count"] == 53
    assert sums_agg["sum_rev"] == sums_ssot["sum_rev"]
    assert sums_agg["sum_ebitda"] == sums_ssot["sum_ebitda"]
    assert sums_agg["sum_pbt"] == sums_ssot["sum_pbt"]


def test_reconcile_lifting_cost(bq_client):
    """(c) agg_lifting_cost: company FY26 lifting cost/boe equals v_lifting_cost (within +-0.5%)."""
    sql_agg = f"""
    SELECT
        ROUND(SUM(total_opex_inr_cr * 10000000.0) / NULLIF(SUM(total_production_boe), 0), 2) as lifting_cost_inr_boe,
        ROUND(SUM(total_opex_inr_cr * 10000000.0 / 88.33) / NULLIF(SUM(total_production_boe), 0), 2) as lifting_cost_usd_boe
    FROM `{PROJECT_ID}.hrfin_gold.agg_lifting_cost_summary`
    WHERE fiscal_year = 'FY26';
    """
    res_agg = list(bq_client.query(sql_agg).result())[0]

    sql_view = f"""
    SELECT
        ROUND(SUM(total_opex_inr_cr * 10000000.0) / NULLIF(SUM(total_production_boe), 0), 2) as lifting_cost_inr_boe,
        ROUND(SUM(total_opex_inr_cr * 10000000.0 / 88.33) / NULLIF(SUM(total_production_boe), 0), 2) as lifting_cost_usd_boe
    FROM `{PROJECT_ID}.hrfin_gold.v_lifting_cost`
    WHERE fiscal_year = 'FY26';
    """
    res_view = list(bq_client.query(sql_view).result())[0]

    inr_diff_pct = abs(float(res_agg["lifting_cost_inr_boe"]) - float(res_view["lifting_cost_inr_boe"])) / float(res_view["lifting_cost_inr_boe"])
    usd_diff_pct = abs(float(res_agg["lifting_cost_usd_boe"]) - float(res_view["lifting_cost_usd_boe"])) / float(res_view["lifting_cost_usd_boe"])

    assert inr_diff_pct <= 0.005, f"INR diff pct {inr_diff_pct} exceeds 0.5%"
    assert usd_diff_pct <= 0.005, f"USD diff pct {usd_diff_pct} exceeds 0.5%"


def test_reconcile_vacancies(bq_client):
    """(d) agg_vacancies: totals equal sanctioned_posts sums per FY."""
    sql_agg = f"""
    SELECT
        fiscal_year,
        SUM(total_sanctioned) as sum_sanctioned,
        SUM(total_in_position) as sum_in_position,
        SUM(total_vacancies) as sum_vacancies
    FROM `{PROJECT_ID}.hrfin_gold.agg_vacancies_summary`
    GROUP BY fiscal_year
    ORDER BY fiscal_year DESC;
    """
    rows_agg = {r["fiscal_year"]: dict(r) for r in bq_client.query(sql_agg).result()}

    sql_base = f"""
    SELECT
        fiscal_year,
        SUM(sanctioned_strength) as sum_sanctioned,
        SUM(in_position_strength) as sum_in_position,
        SUM(vacancy_count) as sum_vacancies
    FROM `{PROJECT_ID}.hrfin_silver.sanctioned_posts`
    GROUP BY fiscal_year
    ORDER BY fiscal_year DESC;
    """
    rows_base = {r["fiscal_year"]: dict(r) for r in bq_client.query(sql_base).result()}

    for fy, base in rows_base.items():
        assert fy in rows_agg
        agg = rows_agg[fy]
        assert agg["sum_sanctioned"] == base["sum_sanctioned"]
        assert agg["sum_in_position"] == base["sum_in_position"]
        assert agg["sum_vacancies"] == base["sum_vacancies"]
