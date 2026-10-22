"""Automated SSOT Reconciliation & Grain Verification Suite (Phase 1.5)."""

from google.cloud import bigquery

PROJECT = "ongc-hr-finance-agent"
LOCATION = "asia-south1"
LABELS = {"datacloud": "ai-agent"}


def main():
    client = bigquery.Client(project=PROJECT, location=LOCATION)

    def run_scalar(sql: str):
        cfg = bigquery.QueryJobConfig(labels=LABELS)
        rows = list(client.query(sql, job_config=cfg).result())
        return rows[0][0] if rows else None

    # 1. Active company headcount == 22,798 (as of Oct-2026; FY26 Mar-2026 is 23,117) across all SSOT and Gold tables
    hc_ssot_emp = run_scalar(f"SELECT COUNT(*) FROM `{PROJECT}.hrfin_gold.ssot_workforce_employee` WHERE active_headcount = 1")
    hc_ssot_wc = run_scalar(f"SELECT SUM(active_headcount) FROM `{PROJECT}.hrfin_gold.ssot_work_centre_360`")
    hc_mart_wf = run_scalar(f"SELECT SUM(in_position_strength) FROM `{PROJECT}.hrfin_gold.mart_workforce`")
    assert hc_ssot_emp == 22798, f"Expected 22798 in ssot_workforce_employee, got {hc_ssot_emp}"
    assert hc_ssot_wc == 22798, f"Expected 22798 in ssot_work_centre_360, got {hc_ssot_wc}"
    assert hc_mart_wf == 22798, f"Expected 22798 in mart_workforce, got {hc_mart_wf}"
    print(f"[PASS] Company active headcount = {hc_ssot_emp:,} across ssot_workforce_employee, ssot_work_centre_360, mart_workforce")

    # 2. Ahmedabad (WC-AHM) headcount == 1,199 (698 execs, 501 non-execs)
    ahm_emp = run_scalar(f"SELECT COUNT(*) FROM `{PROJECT}.hrfin_gold.ssot_workforce_employee` WHERE active_headcount = 1 AND wc_id = 'WC-AHM'")
    ahm_wc = run_scalar(f"SELECT active_headcount FROM `{PROJECT}.hrfin_gold.ssot_work_centre_360` WHERE wc_id = 'WC-AHM'")
    ahm_wf = run_scalar(f"SELECT SUM(in_position_strength) FROM `{PROJECT}.hrfin_gold.mart_workforce` WHERE wc_id = 'WC-AHM'")
    assert ahm_emp == 1199 and ahm_wc == 1199 and ahm_wf == 1199, f"Ahmedabad mismatch: {ahm_emp}, {ahm_wc}, {ahm_wf}"
    print(f"[PASS] Ahmedabad (WC-AHM) active headcount = {ahm_emp:,} across all tables (zero fan-out)")

    # 3. No duplicate emp_id in ssot_workforce_employee or mart_workforce
    dup_ssot = run_scalar(f"SELECT COUNT(*) - COUNT(DISTINCT emp_id) FROM `{PROJECT}.hrfin_gold.ssot_workforce_employee`")
    dup_wf = run_scalar(f"SELECT COUNT(*) - COUNT(DISTINCT emp_id) FROM `{PROJECT}.hrfin_gold.mart_workforce`")
    assert dup_ssot == 0 and dup_wf == 0, f"Duplicate emp_id found: ssot={dup_ssot}, wf={dup_wf}"
    print("[PASS] Zero duplicate emp_id in ssot_workforce_employee and mart_workforce")

    # 4. Field economics 360 & Corporate Annual 360 populated
    fields_fy26 = run_scalar(f"SELECT COUNT(*) FROM `{PROJECT}.hrfin_gold.ssot_field_economics_360` WHERE fiscal_year = 'FY26' AND field_id IS NOT NULL")
    corp_rev_fy26 = run_scalar(f"SELECT gross_revenue_inr_cr FROM `{PROJECT}.hrfin_gold.ssot_corporate_annual_360` WHERE fiscal_year = 'FY26'")
    assert fields_fy26 >= 45, f"Expected >=45 fields in FY26, got {fields_fy26}"
    assert corp_rev_fy26 and corp_rev_fy26 > 100000, f"Unexpected FY26 corporate revenue: {corp_rev_fy26}"
    print(f"[PASS] ssot_field_economics_360 FY26 fields = {fields_fy26}, ssot_corporate_annual_360 FY26 revenue = ₹{corp_rev_fy26:,.2f} Cr")


if __name__ == "__main__":
    main()
