-- Provenance for Corporate Capex Plan
-- Note: Reads cleaned workbook from landing/excel/_clean/capex_be_re_actuals.xlsx (reconstructed from messy landing source)
SELECT fiscal_year, capex_head, 
       round(sum(budget_estimate_be_inr_cr), 2) as total_be,
       round(sum(revised_estimate_re_inr_cr), 2) as total_re,
       round(sum(actual_spend_inr_cr), 2) as total_actual
FROM 'landing/excel/_clean/capex_be_re_actuals.xlsx'
GROUP BY fiscal_year, capex_head
ORDER BY fiscal_year DESC, total_actual DESC
LIMIT 12;