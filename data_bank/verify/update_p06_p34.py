import json

with open('verify/stress_test_prompts_remedied.json') as f:
    prompts = json.load(f)

for p in prompts:
    if p['prompt_id'] == 'P_06_3':
        p['query_type'] = 'SEARCH'
        p['query'] = 'recruitment cadre restructuring vacancy norms executive induction'
        p['status'] = 'PARTIAL'
    if p['prompt_id'] == 'P_34_1':
        p['query_type'] = 'SEARCH'
        p['query'] = 'special casual leave sports welfare amendment circular'
        p['status'] = 'PARTIAL'

with open('verify/stress_test_prompts_remedied.json', 'w') as f:
    json.dump(prompts, f, indent=2)

print("Updated P_06_3 and P_34_1.")
