SELECT field_id, asset_wc_id, gross_revenue_inr_cr, total_opex_inr_cr, 
       ebitda_inr_cr, dda_depreciation_inr_cr, pbt_inr_cr, 
       allocated_manpower_cost_inr_cr, regular_employee_headcount, 
       total_production_boe, lifting_cost_per_boe_usd, 
       is_loss_making_3yr_consecutive, is_divestment_candidate, 
       pec_monetisation_potential_flag, root_cause_loss_code, 
       estimated_annual_opex_savings_inr_cr, estimated_annual_capex_savings_inr_cr, 
       projected_pec_farmout_payoff_5yr_inr_cr
FROM 'landing/sap/CO_PA.csv'
WHERE fiscal_year = 'FY26' AND line_type = 'field' 
  AND (pbt_inr_cr < 0 OR pec_monetisation_potential_flag = true)
ORDER BY pbt_inr_cr ASC;