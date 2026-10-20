-- Provenance for Major Projects Capex Outlay
-- Note: Reads cleaned workbook from landing/excel/_clean/capex_be_re_actuals.xlsx (reconstructed from messy landing source)
SELECT prj_id, project_name, asset_wc_id, fiscal_year,
       round(sum(budget_estimate_be_inr_cr), 2) as total_be,
       round(sum(revised_estimate_re_inr_cr), 2) as total_re,
       round(sum(actual_spend_inr_cr), 2) as total_actual
FROM 'landing/excel/_clean/capex_be_re_actuals.xlsx'
WHERE fiscal_year = 'FY26'
GROUP BY prj_id, project_name, asset_wc_id, fiscal_year
ORDER BY total_actual DESC
LIMIT 10;