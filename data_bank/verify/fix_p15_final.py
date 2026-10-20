import json

with open('verify/stress_test_prompts.json') as f:
    prompts = json.load(f)

for p in prompts:
    if p['prompt_id'] == 'P_15_1':
        p['query'] = "SELECT to_city, COUNT(DISTINCT travel_claim_id) as claims_count, ROUND(SUM(approved_amount_inr)/10000000, 2) as total_approved_cr FROM hrfin_silver.travel_claims WHERE fiscal_year = 'FY26' GROUP BY 1 ORDER BY total_approved_cr DESC LIMIT 5"
    if p['prompt_id'] == 'P_15_2':
        p['query'] = "SELECT grade_id, COUNT(*) as trips, ROUND(SUM(approved_amount_inr)/10000000, 2) as approved_cr, ROUND(SUM(fare_amount_inr)/10000000, 2) as fare_cr, ROUND(SUM(lodging_hotel_amount_inr)/10000000, 2) as hotel_cr, ROUND(SUM(daily_allowance_da_inr)/10000000, 2) as da_cr FROM hrfin_silver.travel_claims WHERE fiscal_year = 'FY26' AND grade_id IN ('E4', 'E5', 'E6', 'E7', 'E8') GROUP BY 1 ORDER BY 1"
    if p['prompt_id'] == 'P_15_3':
        p['query'] = "SELECT ROUND(SUM(approved_amount_inr)/10000000, 2) as total_travel_cr, ROUND(SUM(approved_amount_inr)*0.30/10000000, 2) as savings_30pct_cr FROM hrfin_silver.travel_claims WHERE fiscal_year = 'FY26'"

with open('verify/stress_test_prompts.json', 'w') as f:
    json.dump(prompts, f, indent=2)

print("Updated P_15 final.")
