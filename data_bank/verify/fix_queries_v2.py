import json

with open('verify/stress_test_prompts.json') as f:
    prompts = json.load(f)

for p in prompts:
    if p['prompt_id'] == 'P_11_1':
        p['query'] = "SELECT fiscal_year, entity_name, pat_inr_cr, dividend_declared_inr_cr, dividend_received_by_ongc_inr_cr FROM hrfin_silver.subsidiary_financials WHERE entity_name IN ('Hindustan Petroleum Corporation Limited (HPCL)', 'Mangalore Refinery and Petrochemicals Limited (MRPL)', 'ONGC Petro additions Limited (OPaL)') ORDER BY entity_name, fiscal_year"
    if p['prompt_id'] == 'P_11_2':
        p['query'] = "SELECT fiscal_year, entity_name, pat_inr_cr, gross_refining_margin_usd_bbl FROM hrfin_silver.subsidiary_financials WHERE entity_name LIKE '%OPaL%' ORDER BY fiscal_year"
    if p['prompt_id'] == 'P_48_2':
        p['query'] = "SELECT entity_name, pat_inr_cr, dividend_received_by_ongc_inr_cr FROM hrfin_silver.subsidiary_financials WHERE entity_name LIKE '%Videsh%' AND fiscal_year = 'FY26'"

with open('verify/stress_test_prompts.json', 'w') as f:
    json.dump(prompts, f, indent=2)

print("Queries cleanly updated.")
