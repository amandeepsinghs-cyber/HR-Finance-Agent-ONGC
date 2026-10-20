import json

with open('verify/stress_test_executed_results.json') as f:
    data = json.load(f)

ans_prompts = [r for r in data['results'] if r['status'] == 'ANSWERABLE' and '0 rows' not in r.get('result_summary', '') and 'Error' not in r.get('result_summary', '')]

# Check 15 specific prompts across various categories
sample_ids = [
    'P_01_2', 'P_02_1', 'P_03_1', 'P_04_1', 'P_05_1',
    'P_08_1', 'P_09_1', 'P_13_1', 'P_14_1', 'P_16_1',
    'P_18_1', 'P_20_1', 'P_21_1', 'P_26_1', 'P_27_1'
]

print(f"Auditing 15 ANSWERABLE prompts for direct relevance...")
for p in ans_prompts:
    if p['prompt_id'] in sample_ids:
        print(f"\n--- {p['prompt_id']} ({p['persona']}) ---")
        print(f"Question: {p['text']}")
        print(f"Kind: {p['kind']}")
        print(f"Query: {p['query'][:90]}...")
        print(f"Summary: {p['result_summary'][:150]}...")
