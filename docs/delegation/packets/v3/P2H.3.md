# Task Packet: `P2H.3` V19 turns 1–3: ordered levels, canonical >5-yr rule, roster columns, cohort store

**Executor:** O→F (O: definition registry + cohort store + planner patch; F: chart ordering, roster columns, tests) · **Author:** O · **Date:** 2026-10-23
**Branch:** `v3/P2H-hr` · **Base SHA:** `<after P2H.1>` · **Max files changed:** 10 · **Budget:** ~70 tool calls · **Features:** FEAT-023 · **Bug:** BUG-34 · **Spec:** [SPEC-07 §4.1–4.3, §4.6, §4.7](../../../specs/SPEC-07_v19_transfer_workflow_email.md) · **Behaviour:** [BEH-02.01–.04, .10, .16, .17, .20–.24, .30–.32](../../../behaviour/BEH-02_v19_hr_transfer_chain.md)
**App root (quote it):** `/usr/local/google/home/amandeepsinghs/o&g agentic transformation/Oil & Gas Agent Portfolio/cloud_run_apps/HR and Finance_ONGC`

## 1. Goal
V19 turns 1–3 return an E1→E9 column chart, one canonical ">5 years" count (executives default + all-cadres toggle, with Illustrative + real citations), and a 7-column roster, with a session cohort carried across turns.

## 2. Context you need
- Compiler grade ordering (`ORDER BY headcount DESC`), planner follow-up patch (`continuous_stay_years > 5.0`), certified C1 (`>= 60 months`), `presenter.py:128` (roster cap), `drilldowns.py:128-129`, `turn_runner.py:945-1075` (legacy age-histogram default), `dataform/definitions/gold/v_continuous_stay.sqlx`, `semantic_model.yaml`.
- diag_B §3 (trace), §5 (thresholds).

## 3. Files you may change
1. `yukti/backend/app/semantic/definitions.yaml` (new: `DELHI_GT5_CONT_V1`, `STATION_GT5_CONT_V1`)
2. `yukti/backend/app/semantic/semantic_model.yaml` (`grade_level_order`, `delhi_tenure_years` alias)
3. `yukti/backend/app/brain/compiler.py` (order by `grade_level_order`; definition expansion)
4. `yukti/backend/app/brain/planner.py` (follow-up patch → definition id)
5. `yukti/backend/app/brain/certified/library.yaml` (C1 → definition)
6. `yukti/backend/app/brain/presenter.py` (T1 chart kind/note/footnote; T2 KPI + citations + chips; T3 columns/labels)
7. `yukti/backend/app/session_memory.py` (cohort store per SPEC-07 §4.6)
8. `yukti/backend/app/turn_runner.py` (delete legacy age-histogram default for level questions)
9. `yukti/backend/tests/test_v19_definition.py`, `tests/test_v19_chain.py` (new; turns 1–3 part)
10. `dataform/definitions/gold/dim_grade.sqlx` (add `grade_level_order`; no bq run)

## 4. Do NOT touch
- Export/email (P2H.4), RBAC policy (P2H.1), SPEC-04 data regeneration. No git/deploy/bq DDL/DML/destructive commands.

## 5. Exact requirements
1. Reference SQL exactly as SPEC-07 §4.2; strictly `> 1826` days; executives E1–E9 default; `all_cadres` adds GRP-B/C/D.
2. T2 answer shows both counts, rule sentence, "Illustrative" JRTP 3.2 line and the Delhi HC 2018 (J-03) line; chips per SPEC-07 §4.2.
3. T1: `chart.kind="column"`, explicit x order, one-time note, board-level footnote.
4. T3: 7 visible columns per SPEC-07 §4.3, sort by Delhi tenure desc, label switches for other stations.
5. Cohort store: C0/C1 parent-child, anaphora binding, `go back` re-activation; written by planner and voice paths.
6. RBAC per SPEC-07 §4.7 columns T1–T3 (uses P2H.1 policy).

## 6. Examples
```
"how many employees in Delhi across levels, histogram" → x = [E1..E9, GRP-B, GRP-C, GRP-D]
"how many of these > 5 years" → KPI "{n_gt5_exec} executives ({n_gt5_all} including non-executive staff)"
```

## 7. Acceptance criteria
- [ ] SPEC-07 AC 1–3 (order, counts = reference SQL on fixture data, roster columns).
- [ ] Threshold edge test: 1826 days excluded, 1827 included.
- [ ] 0 code paths still using `>= 60` months or `minus 3-yr retirees` for this definition (grep).
- [ ] RBAC T1–T3 for 11 personas (33 cases) green.

## 8. Self-check commands
```bash
cd "<app root>/yukti/backend" && .venv/bin/python -m pytest -q tests/test_v19_definition.py tests/test_v19_chain.py tests/test_planner_golden.py -k "v19 or delhi"
grep -rnE "60 ?months|>= ?60" "<app root>/yukti/backend/app/brain/certified/library.yaml" | head
```

## 9. Stop-and-ask triggers
- `v_continuous_stay` lacks `stay_start_date` (report actual columns).
- Planner golden tests change outside V19.

## 10. Report format
- **Files changed** · **Self-check output** · **Acceptance criteria** ✅/❌ · **Open questions**
