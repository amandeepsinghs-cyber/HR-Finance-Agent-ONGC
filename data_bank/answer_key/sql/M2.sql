-- Answer Key SQL: M2
-- Question: "What is the capex utilisation by asset this year?" (aggregate)
-- Type: data
-- Semantic audit 2026-10-20: Old SQL answered a different question (project cost overruns) and fanned out over project_progress milestones (360 duplicated rows).
-- Semantic audit 2026-10-20: Now: FY27 year-to-date (Apr-Sep 2026) capex utilisation (actual vs BE and RE) by asset work centre from capex_budget.

SELECT
    wc.wc_id,
    wc.short_name AS asset,
    wc.type AS wc_type,
    COUNT(DISTINCT cb.month) AS months_covered,
    ROUND(SUM(cb.budget_estimate_be_inr_cr), 2) AS ytd_be_inr_cr,
    ROUND(SUM(cb.revised_estimate_re_inr_cr), 2) AS ytd_re_inr_cr,
    ROUND(SUM(cb.actual_spend_inr_cr), 2) AS ytd_actual_inr_cr,
    ROUND(SUM(cb.actual_spend_inr_cr) * 100.0 / NULLIF(SUM(cb.budget_estimate_be_inr_cr), 0), 1) AS utilisation_vs_be_pct,
    ROUND(SUM(cb.actual_spend_inr_cr) * 100.0 / NULLIF(SUM(cb.revised_estimate_re_inr_cr), 0), 1) AS utilisation_vs_re_pct
FROM capex_budget cb
JOIN dim_work_centre wc ON wc.wc_id = cb.asset_wc_id
WHERE cb.fiscal_year = 'FY27'
GROUP BY wc.wc_id, wc.short_name, wc.type
ORDER BY ytd_actual_inr_cr DESC;
