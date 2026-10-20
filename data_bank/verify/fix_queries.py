import json

with open('verify/stress_test_prompts.json') as f:
    prompts = json.load(f)

for p in prompts:
    # Fix group keyword in P_06_2
    if p['prompt_id'] == 'P_06_2':
        p['query'] = p['query'].replace("cadre, group,", "cadre, `group`,")
    # Fix subsidiary_pat_inr_cr in P_11_1, P_11_2, P_48_2
    if 'subsidiary_pat_inr_cr' in p['query']:
        p['query'] = p['query'].replace("subsidiary_pat_inr_cr", "pat_inr_cr")
    # Fix dividend columns if needed
    if 'dividend_declared_inr_cr' in p['query'] and 'subsidiary_financials' in p['query']:
        p['query'] = p['query'].replace("dividend_declared_inr_cr, dividend_received_by_ongc_inr_cr", "dividend_payout_ratio_pct")

with open('verify/stress_test_prompts.json', 'w') as f:
    json.dump(prompts, f, indent=2)

print("Updated queries.")
