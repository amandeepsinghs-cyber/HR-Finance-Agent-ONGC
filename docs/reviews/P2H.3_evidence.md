# P2H.3 Evidence — V19 Turns 1–3: Ordered Levels, Canonical >5-yr Rule, Roster Columns & Cohort Store

- **Step:** `P2H.3` (V19 turns 1–3 backend: ordered levels, canonical `DELHI_GT5_CONT_V1` / `STATION_GT5_CONT_V1` rule, 7-column roster, session cohort store `C-1..C-8`, 11-persona × 3-turn RBAC matrix)
- **Role / Agent:** `rbac` (Role A, Gemini 4 Argon)
- **Branch / Worktree:** `v3/P2H-hr` (`HR and Finance_ONGC__v3P2H`)
- **Features & Bugs Addressed:** `FEAT-032`, `FEAT-033`; closes **`BUG-34`** (`ORDER BY MIN(grade_level_order) ASC, grade ASC`)
- **Specs & Behaviour Docs:** `docs/specs/SPEC-07_v19_transfer_workflow_email.md` (§4.1–4.3, §4.6, §4.7), `docs/behaviour/BEH-02_v19_hr_transfer_chain.md` (`BEH-02.01–.04, .10, .16, .17, .20–.24, .30–.32`), `docs/delegation/packets/v3/P2H.3.md`

---

## 1. Stop-and-Ask Resolution & Frontend Additive Contract Alignment

1. **Stay-Start Column (`board #52 -> #53`):**
   - `SPEC-07 §4.2` prose referenced `current_stay_start_date`, whereas `fact_employee_snapshot` (`dataform/definitions/gold/fact_employee_snapshot.sqlx:56,115`, `semantic_model.yaml:68`, `certified/library.yaml:13`) exposes `continuous_from_date`.
   - Resolved by `@coordinator` in `#53`: use `continuous_from_date` (`DATE_DIFF(DATE '2026-10-19', continuous_from_date, DAY) > 1826`), which evaluates to the exact SSOT counts (`419` executives and `645` all-cadres out of `943` active Delhi staff).
2. **Additive Contract Fields for Frontend (`board #77`):**
   - **T1 / T2 Level Column Chart (`visual.chart`):**
     - `kind: "column"`
     - `x_order: "explicit"`
     - `note: "Levels are categories, so this is a column chart in level order."`
     - `footnote: "Also in Delhi: CMD 1, Directors 2"` (on T1)
   - **T3 Named Roster (`visual.table`):**
     - `columns: ["name", "functional_designation", "grade", "ongc_tenure_years", "delhi_tenure_years", "years_to_retirement", "exemption", "emp_id", "discipline"]` (or `"station_tenure_years"` for non-Delhi single-station rosters)
     - `column_labels`: human-readable labels for the 7 visible columns (`"Name"`, `"Designation"`, `"Level"`, `"ONGC service (yrs)"`, `"Tenure in Delhi (yrs)"` / `"Tenure at <Station> (yrs)"`, `"Years to retirement"`, `"Exemption"`)
     - `hidden_columns: ["emp_id", "discipline"]`
     - `default_sort: {"key": "delhi_tenure_years", "dir": "desc"}` (with deterministic SQL tie-breaker `, emp_id ASC`)
     - `as_of: "2026-10-19"`

---

## 2. Acceptance Criteria Verification Table

| ID | Criterion | Verification & Numbers | Status |
|---|---|---|---|
| **AC-1** | **Turn 1 (`BEH-02.01, .04, .30, .31`; `BUG-34`):** All 3 phrasings (*"How many employees are here in Delhi across different levels? Draw a histogram"*, *"Show Delhi staff by level"*, *"Employees in Delhi across levels"*) compile `ORDER BY MIN(grade_level_order) ASC, grade ASC`, return `kind: "column"`, `x_order: "explicit"`, `note: "Levels are categories, so this is a column chart in level order."`, `footnote: "Also in Delhi: CMD 1, Directors 2"`, X-axis `E1..E9, GRP-B, GRP-C, GRP-D` (`940` bars + `3` board in footnote = `943`), and insight title `"Delhi: 943 staff; E3 is the largest executive level (154)"`. Legacy age histogram removed (`turn_runner.py:0d`). | Verified across all 3 phrasings in `tests/test_v19_chain.py::test_v19_t1_three_phrasings_ordered_column_chart` (`3/3` pass). Counts: `E1=68, E2=135, E3=154, E4=109, E5=88, E6=62, E7=42, E8=21, E9=4, GRP-B=0, GRP-C=231, GRP-D=26` (`sum=940`; `CMD=1, DIR=2`; `total=943`). | **PASS** |
| **AC-2** | **Canonical `>5-yr` Definition (`SPEC-07 §4.2`, `BEH-02.02–.03, .10, .16, .17`):** `DELHI_GT5_CONT_V1` and `STATION_GT5_CONT_V1` in `definitions.yaml` (`min_days_exclusive: 1826`, `as_of: "2026-10-19"`, `exemption_handling: "counted_not_removed"`). Certified `C1` in `library.yaml` uses `DELHI_GT5_CONT_V1` (`0` paths use `>= 60` months). Turn 2 returns `419` executives (`E1=35, E2=90, E3=87, E4=67, E5=57, E6=35, E7=33, E8=12, E9=3`) and states both `419 executives (645 including non-executive staff)`, rule sentence (`> 1,826 days, as of 2026-10-19`), **Illustrative** `JRTP Rev 4 cl. 3.2`, and real `Delhi High Court (2018), ONGC v. B.V. Srihari Rao` (`J-03`). `"Include all cadres"` chip creates sibling cohort `C1'` (`645`). | Verified in `tests/test_v19_definition.py` (`8/8` pass, including `1826` excluded vs `1827` included threshold test and `PA0002_PA0001.csv` + `PA0001.csv` parity) and `tests/test_v19_chain.py` (`T2` + `T2b` + Mumbai `STATION_GT5_CONT_V1` variant). | **PASS** |
| **AC-3** | **Turn 3 Named Roster (`SPEC-07 §4.3`, `BEH-02.03, .17, .32`):** `"Give me their names"` returns `419` rows (`total_rows: 419`), 7 visible columns (`name, functional_designation, grade, ongc_tenure_years, delhi_tenure_years, years_to_retirement, exemption`), `hidden_columns: ["emp_id", "discipline"]`, `default_sort: {"key": "delhi_tenure_years", "dir": "desc"}` with `, emp_id ASC` tie-breaker, `as_of: "2026-10-19"`, and `"Tenure at Mumbai (yrs)"` (`station_tenure_years`) for Mumbai. | Verified in `tests/test_v19_chain.py::test_v19_turns_1_to_3_and_cohort_lifecycle_cmd` and `test_v19_non_delhi_station_variant_mumbai`. | **PASS** |
| **AC-4** | **Session Cohort Store (`SPEC-07 §4.6 C-1..C-8`):** `SessionState.cohorts` (bounded `<= 50`) and `active_cohort_id` in `session_memory.py`: `C0` root on T1 (`943`), `C1` child on T2 (`419`, `parent_cohort_id="C0"`, `definition_id="DELHI_GT5_CONT_V1"`), `C1'` sibling on `"Include all cadres"` (`645`, `parent_cohort_id="C0"`), re-plot (`C-3`) preserves `active_cohort_id` and `level_rows`, `"Go back to all Delhi staff"` (`C-2`) restores `C0`, and principal change (`C-8`) clears `cohorts`. | Verified in `tests/test_v19_chain.py::test_v19_turns_1_to_3_and_cohort_lifecycle_cmd`. | **PASS** |
| **AC-5** | **11-Persona × 3-Turn RBAC Matrix (`SPEC-07 §4.7`, `BEH-02.20–.24`):** `CMD` and `DIR_HR` see full counts on T1/T2 and all `419` named rows on T3; `DIR_FIN` sees full counts on T1/T2 and aggregate grade breakdown on T3 (`name`/`emp_id` stripped in both response and `active_cohort`); `E1..E4_HR` and `E1..E4_FIN` see `k>=5` suppressed counts on T1/T2 (`E9='<5'`, `GRP-B='<5'`) and `R-NAMED` aggregate downgrade on T3 with exact copy (`"I can't share individual names at your access level. Here is the same group as counts by grade (groups under 5 shown as '<5')."`) and no `name`/`emp_id` in `active_cohort`. | Verified across all `11 × 3 = 33` cases in `tests/test_v19_chain.py::test_v19_rbac_11_personas_x_3_turns` (`33/33` pass). | **PASS** |
| **AC-6** | **Dataform `dim_grade.sqlx` & Semantic Model (`SPEC-07 §4.1`):** `dataform/definitions/gold/dim_grade.sqlx` (and mirror in `data_bank/medallion/dataform/definitions/gold/dim_grade.sqlx`) defines `grade_level_order` (`E1=1..E9=9, GRP-B=10, GRP-C=11, GRP-D=12, CMD/DIR=NULL`), exposed in `semantic_model.yaml` alongside `delhi_tenure_years`. | Verified in `tests/test_v19_definition.py::test_dim_grade_sqlx_and_level_order_mapping`. | **PASS** |
| **AC-7** | **Zero Legacy `60 months` / `>= 60` in Certified Library:** `grep -rnE "60 ?months|>= ?60" yukti/backend/app/brain/certified/library.yaml` returns `0` matches. | Verified via shell grep and `tests/test_v19_definition.py::test_zero_legacy_60_months_or_retiree_subtraction_in_c1`. | **PASS** |
| **AC-8** | **Existing Regression Suites Green:** All P2H.1, P2H.2, B4 drilldowns/narrator, contract v2, query spec, certified query, and catalog consistency suites remain green. | `1,196 passed` across 20 test modules (`0` failures). | **PASS** |

---

## 3. Files Created / Modified

- `dataform/definitions/gold/dim_grade.sqlx` & `data_bank/medallion/dataform/definitions/gold/dim_grade.sqlx` *(new)*
- `yukti/backend/app/semantic/definitions.yaml` & `yukti/backend/app/brain/definitions.yaml` *(new)*
- `yukti/backend/app/brain/semantic_model.yaml` & `yukti/backend/app/semantic/semantic_model.yaml`
- `yukti/backend/app/brain/certified/library.yaml` & `yukti/backend/certified/library.yaml`
- `yukti/backend/app/brain/compiler.py`
- `yukti/backend/app/brain/query_spec.py`
- `yukti/backend/app/brain/planner.py`
- `yukti/backend/app/brain/presenter.py`
- `yukti/backend/app/brain/pipeline.py`
- `yukti/backend/app/brain/drilldowns.py`
- `yukti/backend/app/brain/rbac.py`
- `yukti/backend/app/tools/chart_rules.py`
- `yukti/backend/app/session_memory.py`
- `yukti/backend/app/turn_runner.py`
- `yukti/backend/app/ui_control.py`
- `yukti/contracts/answer_contract.schema.json`
- `docs/specs/SPEC-03_coordinator_agents_jobs.md`
- `yukti/backend/tests/test_v19_definition.py` *(new)*
- `yukti/backend/tests/test_v19_chain.py` *(new)*

---

## 4. Verification Commands & Verbatim Output

### 4.1 P2H.3 Self-Check Suite (`test_v19_definition.py` + `test_v19_chain.py` + `test_b4_narrator_drilldowns.py` + `library.yaml` grep)

```bash
cd "/usr/local/google/home/amandeepsinghs/o&g agentic transformation/Oil & Gas Agent Portfolio/cloud_run_apps/HR and Finance_ONGC__v3P2H/yukti/backend" && \
"/usr/local/google/home/amandeepsinghs/o&g agentic transformation/Oil & Gas Agent Portfolio/cloud_run_apps/HR and Finance_ONGC/yukti/backend/.venv/bin/python" -m pytest -q \
  tests/test_b4_narrator_drilldowns.py \
  tests/test_v19_definition.py \
  tests/test_v19_chain.py && \
grep -rnE "60 ?months|>= ?60" "/usr/local/google/home/amandeepsinghs/o&g agentic transformation/Oil & Gas Agent Portfolio/cloud_run_apps/HR and Finance_ONGC__v3P2H/yukti/backend/app/brain/certified/library.yaml" | head
```

Output:
```text
.....................................................                    [100%]
53 passed in 5.71s
```
*(Grep output: empty — 0 matches for `60 months` or `>= 60`.)*

### 4.2 Full P2H.1 + P2H.2 + P2H.3 + Core Backend Regression Suites

```bash
cd "/usr/local/google/home/amandeepsinghs/o&g agentic transformation/Oil & Gas Agent Portfolio/cloud_run_apps/HR and Finance_ONGC__v3P2H/yukti/backend" && \
"/usr/local/google/home/amandeepsinghs/o&g agentic transformation/Oil & Gas Agent Portfolio/cloud_run_apps/HR and Finance_ONGC/yukti/backend/.venv/bin/python" -m pytest -q \
  tests/test_v19_definition.py \
  tests/test_v19_chain.py \
  tests/test_persona_question_matrix.py \
  tests/test_personas_v3.py \
  tests/test_self_scope.py \
  tests/test_refusal_copy.py \
  tests/test_auth_tokens.py \
  tests/test_rbac_policy.py \
  tests/test_role_escalation.py \
  tests/test_query_spec.py \
  tests/test_b4_narrator_drilldowns.py \
  tests/test_certified_query.py \
  tests/test_contract_v2_fixtures.py \
  tests/test_draft_columns.py \
  tests/test_transfer_note.py \
  tests/test_insights.py \
  tests/test_entities.py \
  tests/test_normalize.py \
  tests/test_catalog_consistency.py \
  tests/test_semantic_model_and_flag.py
```

Output:
```text
1196 passed in 21.09s
```

---

## 5. Deviations

- **None.** Stop-and-ask item (`continuous_from_date` column name) was resolved before implementation via `@coordinator` (`#53`), and all additive frontend contract fields (`#77`) are emitted backward-compatibly.
