SELECT fiscal_year, field_id, asset_wc_id, gross_revenue_inr_cr, 
       total_opex_inr_cr, ebitda_inr_cr, pbt_inr_cr, lifting_cost_per_boe_usd
FROM 'landing/sap/CO_PA.csv'
WHERE field_id IN ('FLD-CHP', 'FLD-BOR')
ORDER BY field_id, fiscal_year DESC;