# Semantic audit brief — answer key (2026-10-20)

You are auditing AND fixing one slice of the ONGC HR & Finance answer key (eval oracle for the Yukti agent + UI fixture source).
A previous audit marked 65/65 "pass" yet missed a severe grain bug (C11 summed `headcount_snapshot` over 12 FY26 months vs 1 FY21 month → Bassein "22,703" employees, company has 23,117; and added oil MMT to gas BCM). Your job is to find and fix every such semantic error in your slice.

## Paths / rules
- AK = `/usr/local/google/home/amandeepsinghs/o&g agentic transformation/Oil & Gas Agent Portfolio/cloud_run_apps/HR and Finance_ONGC/data_bank/answer_key` (always quote; contains `&` and spaces).
- Root SQL `AK/sql/<id>.sql`, expected `AK/expected/<id>.json`, answer `AK/answers/<id>.md`; follow-ups `AK/followups/<id>__<kind>.{sql,json,md}` (kinds: drill_down, why, compare_or_so_what). Questions text: `data_bank/world_bible/reference/questions.yaml`.
- Pre-change backup (for "old" values): `/usr/local/google/home/amandeepsinghs/.gemini/jetski/brain/ee3ffc4e-1366-47ae-9683-f25a82a4f930/scratch/answer_key_before/` (same layout).
- READ `AK/semantic_audit/REFERENCE_FACTS.md` first (anchors, stock-vs-flow table, coverage facts).
- GCP project `ongc-hr-finance-agent`, datasets hrfin_silver / hrfin_gold / hrfin_docs (asia-south1). **READ-ONLY** BigQuery: SELECT only, no DDL/DML. Python client must use job labels `{"datacloud":"ai-agent"}` (the provided tools do). For ad-hoc exploration use: `cd "$AK" && echo "<sql>" | uv run python /usr/local/google/home/amandeepsinghs/.gemini/jetski/brain/ee3ffc4e-1366-47ae-9683-f25a82a4f930/scratch/q.py` (default dataset hrfin_silver; prefix `hrfin_gold.` for gold).
- Do NOT read `data_bank/generators/**` or any `story_register*.yaml`. Do not edit `common.py`, `run_entry.py`, `build_answer_key.py`, tests, or other slices' files.

## What to audit (every root SQL and every follow-up SQL in your slice)
Defect classes (use these exact codes in the log):
- `STOCK_SUMMED` — summing stock/snapshot measures (headcount, contractor headcount, wells, balances, receivables outstanding, liabilities, reserves) across periods instead of period-end (e.g. `month='2026-03'` for FY26, `'2026-09'` for latest) or average.
- `UNEQUAL_PERIODS` — compared periods with different month coverage (e.g. FY27 = 6 months vs FY26 = 12; headcount_snapshot FY21 = 1 month).
- `UNIT_MIXING` — MT + MMSCM/BCM, BOE vs MMTOE, ₹ / lakh / crore mixed. Production → BOE (`total_production_boe`) or MMTOE (BOE/7.33e6) or separate oil/gas columns.
- `JOIN_FANOUT` — multi-grain marts or duplicate dim rows multiplying measures.
- `FY_MAPPING` — wrong fiscal year (Indian FY Apr–Mar; "current FY" = FY27 partial; "last full FY" = FY26; "5 years" = FY21→FY26), calendar-year logic for FY, date windows not anchored at 2026-10-19.
- `CATEGORICAL_CASE` — string filter on categorical (status, gender, category, cadre, type, severity, mode…) without `LOWER()` that **changed results** (missed rows). Where you touch a query, add `LOWER(col) = 'value'` as hygiene anyway (codes like wc_id, grade_id, fiscal_year, field_id stay exact). Log hygiene-only additions with class `CASE_HYGIENE` (not counted as a defect).
- `THRESHOLD_VS_RANK` — question asks "above X"/"breaching norm" but SQL uses LIMIT/top-N (or vice versa).
- `SCD2_NOT_ASOF` — posting/history tables not restricted to current (`is_current_posting`) or an as-of window.
- `PCT_DENOM` — percentages >100% where impossible, or numerator/denominator from different populations/grains.
- `SANITY_BOUND` — result violates anchors (asset headcount > company; company headcount ≠ 23,117 at 31-Mar-2026 / 22,798 today; FY26 revenue ≠ ₹1,32,508 cr; per-employee/per-BOE values off by orders of magnitude).
- `WRONG_QUESTION` — SQL does not answer the question asked (wrong entity hard-coded, wrong metric, ignores the parent's finding).
- `GENERIC_TEXT` — answers MD is the generic template ("Analysis of enterprise data across N records indicates operational patterns. Leading record reflects…"). EVERY such MD in your slice must get a real narrative even if the SQL is fine.
- `GAP` — the data genuinely cannot answer correctly (explain; still return the closest honest result if possible).

## How to fix (tooling is ready)
1. Edit the SQL file in place. Keep the 3 header comment lines (`-- Answer Key SQL: <id>` / `-- Question:` / `-- Type:`) and add `-- Semantic audit 2026-10-20: <what changed and why>` comment lines. Comment lines must start with `--` at line start (the test strips them). Use unqualified silver table names (default dataset hrfin_silver) or fully-qualified `ongc-hr-finance-agent.hrfin_gold.x`.
2. Add a narrative function for the entry in `AK/semantic_audit/narratives_<SLICE>.py` (create it; copy the import line / pattern from `narratives_C.py`, which has the worked C11 example). `NARRATIVES = {"<id>": fn}`; `fn(rows) -> str`: a CMD-style 2–4 sentence answer: sentence 1 = the direct answer to the question (the headline, used in INDEX.md), then the "so what", then one supporting fact/caveat. **Every number must come from `rows`** (use helpers `num`, `inr_cr`, `pct`, `signed_pct`, `f`, `names`, `total` from `semantic_audit.common`; Indian grouping is automatic). Only definitional constants from the question (dates, "5 years", policy thresholds) may be literal. Must be robust (no crash on None).
3. Run: `cd "$AK" && uv run python -m semantic_audit.run_entry <id> [<id> ...]` (writes JSON + MD; `--dry` to preview; `--render-only` to re-render MD from existing JSON when only the narrative changed). It refuses to write if 0 rows, identical to parent, or generic text. Re-run follow-ups AFTER their parent if the parent changed, and ensure each follow-up still differs from its parent and is consistent with the parent's corrected finding.
4. Entries with special non-generic MD (refusals D*, policy/rag citations, C1, P11, W1–W4, C13, C14/H10/F10/X7 document outputs) are rendered by the legacy renderer automatically if you don't register a narrative; if the SQL changes, verify their hard-coded prose in `build_answer_key.py` is still true — if not, register a narrative instead and report it.
5. Log every change in `AK/semantic_audit/changes_<SLICE>.yaml` as a YAML list:
   ```yaml
   - id: C11
     defect_class: [STOCK_SUMMED, UNEQUAL_PERIODS, UNIT_MIXING, GENERIC_TEXT]
     old_headline: "Bassein hc 1,928→22,703 (+1,077%); 14 assets 'added headcount' while prod (MMT+BCM) fell"
     new_headline: "No asset added headcount while losing production; headcount 20,871→16,327 across 15 assets"
     why: "Summed 12 monthly snapshots (FY26) vs 1 (FY21); added MMT to BCM. Now Mar-21 vs Mar-26 snapshot, BOE."
     severity: blocking | important | cosmetic
   ```
   Entries with only GENERIC_TEXT also get a log line (old_headline = "generic template", new_headline = your first sentence). Numbers in the log are fine (it is an audit record).
6. Data problems in silver/gold (coverage holes, implausible values, contradictions between tables) → `AK/semantic_audit/data_defects_<SLICE>.yaml` (`- table:`, `issue:`, `evidence:`, `impact_on_ids:`). Report, do NOT fix data.

## Done =
All roots + follow-ups in your slice audited; every defective one fixed, re-executed and written; zero generic MDs left in the slice (`grep -l "indicates operational patterns"`); changes/data-defect YAMLs written; `uv run python -m semantic_audit.run_entry --dry <all ids>` passes for your slice. Then send the coordinator ONE message: counts by defect class, list of changed ids, top 3 most consequential corrections (old vs new numbers), gaps, data defects. Keep it under 400 words.
