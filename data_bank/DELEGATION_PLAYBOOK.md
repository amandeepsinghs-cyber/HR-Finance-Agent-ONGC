# Delegation Playbook: Flash generation, independent verification, lead adjudication

> [!IMPORTANT]
> **Separation of duties.** Three roles, never the same agent:
> 1. **Generator (Gemini Flash):** writes the seeded Python generator and the record-level data for one step, plus its own unit tests.
> 2. **Verifier (Gemini Flash, independent):** never sees the generator's code. It proves from the *output data only* that the questions and follow-ups can be answered.
> 3. **Lead (me):** writes the briefs, runs both test suites, runs an independent spot-check, and accepts or rejects. The user sees one status line per step and reviews at the gates.

---

## 1. Generator brief template (sent verbatim, with the step-specific block filled in)

```
ROLE: Generator for step <ID> of data_bank/DATA_GENERATION_CHECKLIST.md
PROJECT="<project root>"  (quote paths: spaces and &)

READ FIRST, IN ORDER (mandatory):
 1. data_bank/DATA_GENERATION_CHECKLIST.md: North Star, Global rules (esp. 5a: records not aggregates), follow-up contract, your step row
 2. data_bank/DELEGATION_PLAYBOOK.md: this file
 3. data_bank/world_bible/reference/questions.yaml: the 89 questions + 267 follow-ups
 4. data_bank/world_bible/question_coverage.yaml: filter entries whose `tables` include YOUR tables. These are your acceptance criteria.
 5. data_bank/world_bible/schema_silver.yaml: your tables' columns, PK/FK, sap_field_map, source_format
 6. data_bank/GENERATOR_PATTERN_BRIEF.md: qualitative behaviours. GENERATORS MUST NOT READ world_bible/story_register.yaml or story_register_actuals.yaml (blind generation; story numbers are for the verifier and lead only)
 7. data_bank/world_bible/calibration_targets.yaml: targets whose target_tables include yours
 8. data_bank/world_bible/reference/*.yaml: the ONLY valid IDs
 9. data_bank/reports/step_reports/LEAD_NOTES.md: lead corrections; these override the files above

PRODUCE:
 - data_bank/generators/<domain>/gen_<step>.py: seeded (SEED=20261019), deterministic, CLI `uv run python generators/<domain>/gen_<step>.py`
 - Landing files in source-native format, exactly as named in schema_silver.yaml (SAP field names for SAP sources, Excel with realistic sheet layout for Excel sources)
 - data_bank/tests/test_<step>_*.py
 - data_bank/reports/step_reports/<step>.md (template in the checklist)

HARD RULES:
 - Simulate INDIVIDUAL RECORDS (people, postings, transactions, months). Never write a summary number that can't be recomputed from records.
 - Story numbers are TARGET RANGES: ±10% around the register value unless the value is a public calibration target (then ±2%, or exact if the target says exact). Tune simulation parameters until the pattern EMERGES.
 - Derived KPIs/flags (lifting cost, BOE/employee, loss flags, tenure) must be computed from base columns in code, and tested for equality.
 - NO PLUGS: never hit a target by back-solving a balancing column ("other", "adjustment") per row, by rescaling individual records, or by setting a series value equal to an unrelated target. Every amount must be non-negative where physically required, within documented plausible bands, and driven by physical/business drivers. Calibrate through GLOBAL parameters and explicitly labelled, record-derived reconciling lines. If a story then lands outside its range, REPORT the honest value. Lead finding from 2.4: 301 negative opex rows were used as a plug.
 - FULLY EMERGENT (user decision, 2026-10-19). Story findings must come ONLY from general simulation rules:
   * FORBIDDEN: any condition, dictionary, loop count or index slice keyed on a specific entity ID (WC-/FLD-/PRJ-/CUST-/VEN-/EMP-) or story number that sets an amount, count, date, flag or selects records. Exception: the 5 demo personas (EMP-000001..3, EMP-102451, EMP-103892), whose OWN records may be specified.
   * ALLOWED: parameters keyed on GENERAL ATTRIBUTE CLASSES from reference data (work-centre type/sector/hard_station_cat/onshore_offshore, field maturity/terrain/hydrocarbon/discovery_year, discipline function, grade band, customer type, vendor category); stochastic draws (seeded); and calibration to PUBLIC targets (calibration_targets.yaml) through global scalars or attribute-level allocation weights. A public target at entity level (e.g. Assam state 3,561) may be met through allocation weights for that attribute class, not by editing records.
   * Story numbers in story_register.yaml are EXPECTATIONS, not targets. Tune only general parameters so patterns are likely. After generation, the verifier records the ACTUAL values in world_bible/story_register_actuals.yaml; those (and the answer key) are the truth.
   * tests/test_no_entity_forcing.py (static scan of generators) must pass.
   * Generator tests must NOT assert story numbers (that incentivises forcing). Story tests = pattern/sanity checks + printed emergent values. Hard asserts only for public calibration targets, identities, plausibility bounds. Exact hits on many story numbers are treated as evidence of forcing.
   * Demo-persona records may be specified only inside one function `apply_demo_personas(...)`.
   * Class parameters live in a documented PARAMS dict at the top of each generator. No string-wrapped numbers, no name-substring matching, no story numbers synthesised by arithmetic.
 - Every column in schema_silver for your tables must be populated with realistic values (nulls only where nullable and plausible).
 - No real personal names for employees or vendors (Faker en_IN, seeded). Real names only for organisation, places, fields, projects, subsidiaries, customers.
 - Write nothing outside data_bank/. No git. Don't tick checklist boxes.

YOUR TESTS MUST ASSERT: row counts; PK unique; FK valid against reference + upstream landing; calibration targets; story ranges (computed by SQL/pandas FROM the records); derived columns = recomputation; determinism (run twice → identical SHA-256).

REPLY: PASS/FAIL · files + row counts · calibration table (target / actual / delta) · stories (range / actual) · assumptions.
REPORT PROVENANCE (mandatory): start the reply with SHA-256 (16 chars) + mtime of every upstream AND output file of THIS run; every number must be computed in this run (no carried-over text). No year-specific `if fy == ...` branches that set outcomes; time variation comes from documented PARAMS series.
```

## 2. Verifier brief template (independent agent; runs after each generator step)

```
ROLE: Independent Verifier for step <ID>. You must NOT read data_bank/generators/. Judge only the data.
READ: questions.yaml, question_coverage.yaml, schema_silver.yaml, story_register.yaml, calibration_targets.yaml, LEAD_NOTES.md
DO:
 1. Load all landing files produced so far into DuckDB (data_bank/verify/local.duckdb), applying schema_silver sap_field_map/sheet maps to create silver-named views. (This also pre-tests the Silver mapping.)
 2. For every coverage entry (question AND follow-up) whose tables are ALL available now: write a probe SQL in data_bank/verify/probes/<entry_id>.sql that answers it from the records. Run it. Record: non-empty? sensible? drill dimensions present? matches the story range?
 3. Consistency audit: cross-table FKs, temporal sanity (no posting after separation, no promotion before joining, age 18–60 at events, no overlapping postings), totals vs calibration, story emergence.
 4. Follow-up drill test: for each probed question, run its 3 follow-ups and confirm each returns a DIFFERENT, non-empty, coherent result (not the same table re-sliced to nothing).
 5. Write data_bank/verify/reports/<step>_verification.md: entries probed / answered / failed (with SQL + reason), consistency findings, story emergence table.
REPLY: PASS/FAIL, counts, and the top failures with a concrete fix request for the generator.
```

## 3. Lead acceptance protocol (per step)
| # | Check | How |
|---|---|---|
| 1 | Generator tests green | `uv run pytest tests/test_<step>*` re-run by the lead |
| 2 | Verifier report PASS | `verify/reports/<step>_verification.md`: 100% of available root questions answered; ≥95% of follow-ups |
| 3 | Lead spot-check | Lead runs 5 probes of its own choice (incl. 2 follow-ups) in DuckDB and reads the rows |
| 4 | Determinism | Re-run the generator → identical hashes |
| 5 | Decision | Accept → tick `[x]` · Reject → failing evidence goes back to the **same generator**, and the verifier re-runs |

## 4. Escalation
- Calibration impossible (targets conflict) → lead decides and logs it in LEAD_NOTES; the user is told at the next gate.
- A question/follow-up proves unanswerable → add a column to schema_silver (lead approval), regenerate, re-verify.

## 5. Step dependency order (Phase 2)
```
2.1 HR core ──► 2.2 HR satellites ──► 2.4 Field economics (needs payroll + production) ──► 2.5 Corporate & governance
2.3 Production ─────────────────────────┘
Verifier V0 (harness) builds in parallel with 2.1 / 2.3
```
