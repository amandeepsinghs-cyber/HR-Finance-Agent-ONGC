import json
import difflib

with open('verify/stress_test_prompts.json') as f:
    prompts = json.load(f)

with open('reports/existing_prompts_dump.txt') as f:
    existing = [line.strip() for line in f if line.strip()]

print(f"Checking {len(prompts)} new prompts against {len(existing)} existing reference prompts...")

high_sim = []
for p in prompts:
    p_text = p['text'].lower()
    for e in existing:
        e_text = e.lower()
        sim = difflib.SequenceMatcher(None, p_text, e_text).ratio()
        if sim > 0.80:
            high_sim.append((p['prompt_id'], p['text'], e, sim))

if high_sim:
    print(f"WARNING: Found {len(high_sim)} prompts with >80% similarity:")
    for pid, ptxt, etxt, s in high_sim:
        print(f"- {pid} (sim={s:.2f}):\n  NEW: {ptxt}\n  OLD: {etxt}")
else:
    print("SUCCESS: Zero high-similarity collisions detected! All 150 prompts are brand new.")
