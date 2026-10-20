-- Answer Key Follow-up SQL: X6__drill_down
-- Question: What is the cumulative capital invested in solar, wind, and green hydrogen projects under ONGC Green Limited (OGL)?
-- Type: data
-- Semantic audit 2026-10-20: Cumulative capital per project = SUM of annual_capex FY22-FY26 (the stored cumulative_capex_inr_cr is
-- 1.8x the FY26 annual value and does not reconcile with the annual series), by solar / wind / green hydrogen.
SELECT
    project_name,
    technology_type,
    MAX(IF(fiscal_year = 'FY26', installed_capacity_mw, NULL)) AS installed_mw_fy26,
    ROUND(SUM(annual_capex_inr_cr), 1) AS cumulative_capex_fy22_fy26_cr,
    MAX(IF(fiscal_year = 'FY26', cumulative_capex_inr_cr, NULL)) AS stored_cumulative_capex_fy26_cr
FROM energy_transition
WHERE fiscal_year IN ('FY22', 'FY23', 'FY24', 'FY25', 'FY26')
GROUP BY project_name, technology_type
ORDER BY cumulative_capex_fy22_fy26_cr DESC;
