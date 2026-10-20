-- Answer Key SQL: F2
-- Question: What is capex utilisation (budget vs. revised estimate vs. actual) by asset for the current year?
-- Type: data
-- Semantic audit 2026-10-20: was a list of project_progress milestone rows with RCE > sanctioned cost (6 duplicate
-- Semantic audit 2026-10-20: milestone rows per project, no BE/RE/actual, no current-year filter). Now capex_budget for
-- Semantic audit 2026-10-20: the current FY27 year-to-date (Apr-Sep 2026, 6 months; BE/RE are phased monthly) by asset:
-- Semantic audit 2026-10-20: BE, RE, actual, utilisation vs BE and vs RE.

SELECT
    cb.asset_wc_id,
    wc.short_name AS asset_name,
    wc.onshore_offshore,
    COUNT(DISTINCT cb.prj_id) AS projects,
    COUNT(DISTINCT cb.month) AS months_covered,
    ROUND(SUM(cb.budget_estimate_be_inr_cr), 1) AS be_ytd_cr,
    ROUND(SUM(cb.revised_estimate_re_inr_cr), 1) AS re_ytd_cr,
    ROUND(SUM(cb.actual_spend_inr_cr), 1) AS actual_ytd_cr,
    ROUND(SUM(cb.actual_spend_inr_cr) * 100 / NULLIF(SUM(cb.budget_estimate_be_inr_cr), 0), 1) AS utilisation_vs_be_pct,
    ROUND(SUM(cb.actual_spend_inr_cr) * 100 / NULLIF(SUM(cb.revised_estimate_re_inr_cr), 0), 1) AS utilisation_vs_re_pct,
    ROUND(SUM(cb.actual_spend_inr_cr) - SUM(cb.budget_estimate_be_inr_cr), 1) AS variance_vs_be_cr
FROM capex_budget cb
LEFT JOIN dim_work_centre wc ON wc.wc_id = cb.asset_wc_id
WHERE cb.fiscal_year = 'FY27'
GROUP BY cb.asset_wc_id, wc.short_name, wc.onshore_offshore
ORDER BY actual_ytd_cr DESC;
