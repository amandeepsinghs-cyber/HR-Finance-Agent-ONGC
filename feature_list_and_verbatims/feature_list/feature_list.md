# Yukti AI — Feature List & Requirements Specification

**Location**: `feature_list_and_verbatims/feature_list/`  
**Linked Verbatims**: [`feature_list_and_verbatims/verbatims/`](../verbatims/)  
**Status**: Active / Refinement · **Process**: every feature is delivered through the five-gate process in [`BUILD.md`](../../BUILD.md) §4; steps live in [`UPGRADE_CHECKLIST.md`](../../UPGRADE_CHECKLIST.md)

---

## Feature Index

| Feature ID | Feature Name | Source Verbatim | Priority | Category | Phase | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **FEAT-001** | **Scrollable Conversational Feed (History Preservation)** | V8 §3, V11 | **P0** | Frontend / UX | U2 | Specified |
| **FEAT-002** | **Multi-Turn Context & Entity Carryover** | V11 | **P0** | Backend / Agent | B2 (via FEAT-009) | Specified |
| **FEAT-003** | **Visual Presentation & Charting Audit** | V7, V11 | **P1** | Visualization / UX | U5 | Specified |
| **FEAT-004** | **Luminous Siri / Infinity Loop Voice Orb** | V12 | **P1** | UI / Animation | U3 | Specified |
| **FEAT-005** | **Executive UI Modernization & Material Polish** | V12 | **P1** | UI / Design System | U1 + U4 | Specified |
| **FEAT-006** | **CMD Actionable Employee-Level Roster (Drilldown)** | V13 | **P0** | Data / HR Actions | U5 (UI) + B3 (data) | Specified |
| **FEAT-007** | **Answer Contract v2 (forward-compatible UI ↔ brain)** | V14 (D-4) | **P0** | Contract / Frontend | U2 | Specified |
| **FEAT-008** | **Generated Semantic Layer (catalog = data truth)** | Audit 2026-10-22 | **P0** | Backend / Data | B1 | Specified |
| **FEAT-009** | **QuerySpec Planner & Compiler (replaces keyword fast-paths)** | V11, V13, V14 (D-1) | **P0** | Backend / Agent | B2 | Specified |
| **FEAT-010** | **Granular-Data RBAC Policy (row/column masking)** | V3, V13, V14 (D-5) | **P0** | Governance | B3 (+ U5 UI states) | Specified (D-10, D-11) |
| **FEAT-011** | **Insight Engine & Drill-down Chips ("granular insights")** | V13, V14 | **P0** | Backend / UX | B4 (+ U5 UI) | Specified |
| **FEAT-012** | **Reliability, Safety & Performance Hardening** | Audit 2026-10-22 (P2/P3) | **P1** | Backend / Ops | H1 | Specified |
| **FEAT-013** | **Voice Pipeline Quality (barge-in, mic lifecycle, no duplicate turns)** | V6, V8, audit | **P1** | Frontend / Voice | U3 | Specified |
| **FEAT-014** | **Eval-Gated Release & Cloud Run Redeploy** | V14 (D-3) | **P1** | Quality / Ops | U0 + H1 | Specified |
| **FEAT-015** | **Any-Chart Re-presentation & Chart Excellence** | V7, V15 | **P0** | Visualization / UX | U1.5 + U5.7–U5.9 | U1.5 done; U5 pending |
| **FEAT-016** | **AI Aura visual language** (feathery Google-hue light for AI presence) | V16 | **P1** | UI / Brand | U1.6 (done), U4, U3 | Prototype approved (D-16) |

> **Design Specifications Reference**: See [`design_recommendations_ui_and_orb.md`](./design_recommendations_ui_and_orb.md) for detailed UI glassmorphism and voice orb wave formulas.

---

## FEAT-001: Scrollable Conversational Feed (History Preservation)

### 1. User Problem Statement
Currently, asking a new question clears or completely replaces the screen. The user cannot see previous questions, tables, or charts, making comparison across queries impossible and feeling disconnected from standard conversational AI experiences (Gemini, Claude, ChatGPT).

### 2. Required Behavior
* **Non-Destructive Append**: When a new question is submitted (by voice or text), the previous turn (question + narrative + visual canvas cards) remains intact and scrolls up.
* **Stream/Feed Layout**: The main viewport functions as an interactive vertical feed:
  * Turn $N-1$: User prompt $\rightarrow$ Yukti verbal summary $\rightarrow$ Generated ECharts/DataTable/Doc card.
  * Turn $N$: User prompt $\rightarrow$ Yukti verbal summary $\rightarrow$ Generated ECharts/DataTable/Doc card.
* **Auto-Scroll with User Control**: The viewport smoothly auto-scrolls down to reveal the latest streaming response, but pauses auto-scrolling if the user scrolls up manually to inspect earlier data.
* **Card Interactivity in History**: Historic charts, tables, and document previews remain fully interactive (hover tooltips, tab switching, export triggers).

### 3. Acceptance Criteria
- [ ] Asking Question B after Question A does not erase Question A's card.
- [ ] The user can scroll up to view Question A's exact visual and tabular outputs.
- [ ] Responsive across full-screen canvas and floating chat modes.

---

## FEAT-002: Multi-Turn Context & Entity Carryover

### 1. User Problem Statement
Every question is currently evaluated in isolation. If a user asks *"How many employees are in New Delhi?"* and follows up with *"Break them down by discipline"*, the system does not remember that "them" refers to Delhi employees, causing failures or irrelevant answers.

### 2. Required Behavior
* **Contextual Entity Resolution**: The agent backend retains the active entity context (e.g. `location: "Delhi"`, `cadre: "Executive"`, `fiscal_year: "FY26"`, `field: "Mumbai High"`) across turns within the same session.
* **Multi-Turn Chat History in Prompts**: The backend passes conversation turn history (user questions, tool outputs, agent summaries) to Gemini so follow-up queries naturally inherit antecedents and filters.
* **Session Reset Option**: A clear "New Session / Clear Context" action allowing the user to start a fresh topic when desired.

### 3. Acceptance Criteria
- [ ] Follow-up questions referencing pronouns or implicit filters ("break them down", "compare this with last year", "show only loss-making ones") correctly resolve context from the immediate prior turn.
- [ ] Session memory persists across voice and text turns within the current browser session.

---

## FEAT-003: Visual Presentation & Charting Audit

### 1. Objective
Conduct an exhaustive audit of all visual representations (charts, KPI metrics, geospatial maps, data tables, and document drafts) across the entire question bank to identify presentation gaps and elevate visual polish.

### 2. Scope of Upcoming Audit
* Map every data question type (categorical, time-series, geospatial, tabular, hierarchical) to its optimal visual format (ECharts, Survey of India map, structured card, rich document).
* Identify gaps where plain text is returned instead of an actionable visual.
* Ensure visual hierarchy, color palette, and responsiveness match ONGC leadership expectations.

### 3. Acceptance Criteria
- [ ] `docs/visual_audit.md` maps all 107 question-bank items to a visual type, with gaps listed.
- [ ] Every mapped item renders its visual from a fixture (U5.6 sweep: 0 failures).
- [ ] No data answer renders as plain text only when a visual type is mapped.

---

## FEAT-004: Luminous Siri / Infinity Loop Voice Orb

### 1. User Problem Statement
The existing 3D Fibonacci particle orb feels chaotic, jittery, and overly technical. Leadership expects a serene, organic, and executive voice presence—analogous to Apple's Siri multi-ribbon wave / infinity loop or DeepMind AlphaFold's continuous harmonic ribbons.

### 2. Required Behavior
* **Organic Infinity Ribbon Geometry**: Replace point particles with 3–4 overlapping, luminous cubic Bézier / harmonic sine curves that morph continuously in an infinity / mobius loop configuration.
* **State-Aware Dynamics**:
  * **Idle**: Gentle, slow breathing cycle with soft ambient glow.
  * **Listening**: Responsive audio amplitude modulation where user speech drives ribbon amplitude and thickness organically.
  * **Thinking**: Luminous wave pulse revolving around the loop perimeter at a steady cadence.
  * **Speaking**: Warm vocal resonance frequency pulses matching the agent's synthesized speech playback.
* **Visual Polish**: Smooth gradient blending (ONGC deep saffron `#E85D04` / petroleum blue `#0077B6` / clean gold) with subtle background radial blur, ensuring zero visual noise or harsh edges.

### 3. Acceptance Criteria
- [ ] No scattered or vibrating dots.
- [ ] Smooth 60fps canvas or SVG rendering without CPU spikes.
- [ ] Clear visual distinction between Idle, Listening, Thinking, and Speaking states.

---

## FEAT-005: Executive UI Modernization & Enterprise Material Polish

### 1. User Problem Statement
The current interface is functional but feels somewhat "basic" and flat. It needs an executive-grade aesthetic tailored for ONGC leadership (CMD, Directors) that conveys authority and polish without becoming complex, cluttered, or difficult to use.

### 2. Required Behavior
* **Executive Frame & Card Elevation**:
  * Replace flat borders with subtle frosted glass surfaces (`backdrop-blur-md`, soft layered shadows `shadow-sm` to `shadow-md`).
  * Crisp header badges with metadata: active persona (`CMD`), live query classification, and timestamp.
* **Refined Typography & Hierarchy**:
  * Clean modern sans-serif headings with high-contrast numerical metrics (KPIs prominently styled with contextual trend pills).
  * Executive spacing and breathing room (uncluttered whitespace, generous card padding).
* **Minimalist Canvas Focus**:
  * Keep the UI 90% content-focused: charts, document drafts, and data tables take center stage.
  * Floating voice/chat controls tuck away smoothly when inspecting data.
  * Light-mode default optimized for reading formal documents and board memos.

### 3. Acceptance Criteria
- [ ] Clean, uncluttered layout maintaining single-click access to all actions.
- [ ] Polished executive styling for all rendered tables, charts, and document previews.

---

## FEAT-006: CMD Actionable Employee-Level Roster (Drilldown from Aggregates)

### 1. User Problem Statement
Currently, HR tenure questions (e.g. *Delhi office for 5+ years*) only render an aggregated donut or bar chart showing high-level counts (e.g. 419 executives). A CMD cannot take decisions or initiate transfer actions without seeing the actual names and service histories of the individuals.

### 2. Required Behavior
* **Granular Table Drilldown**: When the CMD asks *"Can you give me a list of all the people who are employed in the Delhi office for more than 5 years? Give me their name, designation, seniority, tenure in ONGC, and time in the Delhi office"*, the system renders an interactive, sortable roster table.
* **Required Column Schema**:
  1. `PERNR` (Employee ID / CPF)
  2. `name` (Full Employee Name)
  3. `designation` (Official ONGC designation, e.g. Chief Manager, DGM)
  4. `grade` (Executive seniority level: E1 to E9)
  5. `discipline` (Domain: Production, Drilling, Finance, HR, IT, Legal)
  6. `total_tenure_years` (Total years of service in ONGC)
  7. `delhi_tenure_years` (Station tenure in Delhi office / WC-DEL)
* **RBAC & Data Privacy Enforcement** (D-5): CMD **and all Directors** get the unmasked roster plus actions. E1–E4 personas get an aggregate or a refusal per FEAT-010 / OD-3.
* **Direct Transfer Action Triggers**:
  * Row multi-select checkboxes allowing CMD to click individual employees and trigger:
    * *"Draft Transfer Note"* (generates formal transfer proposal document).
    * *"Export to Excel / PDF"* (downloads active filtered list).

### 3. Acceptance Criteria
- [ ] Asking for employee names in Delhi for 5+ years returns individual rows, not just aggregate counts.
- [ ] Columns include Name, Designation, Grade, Total Tenure, and Delhi Station Tenure.
- [ ] Table supports sorting by tenure and filtering by discipline/grade.
- [ ] E1–E4 personas (E2_HR, E3_FIN) receive an aggregate or a refusal (no names), and `access.status` matches the text and the visual.

### 4. Update 2026-10-22 (audit + Verbatim 14)
* **Data correction:** the roster data already exists in `hrfin_gold.ssot_workforce_employee` (`emp_name`, `grade_id`, `discipline_name`, `total_tenure_years`, `continuous_stay_years`, `wc_id`; all 692 active Delhi executives are named). The `dim_employee` / `fct_posting` tables proposed in `data_gap_analysis_employee_roster.md` do not exist and are **not needed**. Remaining data check: designation field (`grade_designation` in SSOT vs `current_designation` in `mart_workforce`).
* **Value-case trap:** BigQuery stores `employment_status = 'Active'` while the catalog says `'active'`, which silently returns 0 rows. Fixed by FEAT-008.
* **RBAC per D-5:** CMD **and all Directors** get the unmasked roster. E1–E4 get an aggregate or a refusal per FEAT-010 (OD-3).



---

## FEAT-007: Answer Contract v2 (Forward-Compatible UI ↔ Brain)

### 1. Problem
The UI is built first (D-4), but it must render what the brain will produce later. Contract v1 has a single `visual` and free-text `insights`, with no slot for drill-downs, comparisons, roster masking or the turn's query context.

### 2. Required Behavior
* Add **optional** fields to `answer_contract.schema.json` and `answerContract.ts` (v1 contracts stay valid):
  * `insights_v2[]`: `{kind: share|rank|delta|vs_target|outlier|named_exception|policy_flag, text, value, ref}`
  * `drilldowns[]`: `{label, intent, spec_patch}` (rendered as chips)
  * `context_chips[]`: e.g. `CMD · Delhi HQ · Executives · FY26 · Source: SSOT`
  * `query_spec`: the QuerySpec the answer came from (B2), echoed for follow-ups
  * `visual.compare`: side-by-side / grouped comparison payload
  * `visual.table.masking`: `{masked_columns[], policy_ref, persona}` and `row_actions[]`
* The backend may emit the v2 fields **before** the brain exists (empty or heuristic), so the UI is exercised end to end.

### 3. Acceptance Criteria
- [ ] All existing fixtures and 28 backend tests still validate.
- [ ] New v2 fixtures (roster, compare, insights, drill-downs) validate and render.
- [ ] TypeScript types match the schema (`tsc` clean).

---

## FEAT-008: Generated Semantic Layer (Catalog = Data Truth)

### 1. Problem
The hand-written catalog disagrees with BigQuery (`'active'` vs `'Active'`, `cadre` case, WC codes that differ across modules), so generated SQL silently returns 0 rows and the app falls back to canned answers.

### 2. Required Behavior
* A script generates `semantic_catalog.json` from `INFORMATION_SCHEMA` plus profiled distinct values (categoricals ≤ 200 values), ranges and grain notes, for every SSOT, gold and silver table the agent uses.
* **One** work-centre / field / discipline dictionary (codes ↔ names ↔ aliases, including Hindi/Hinglish), imported by every module.
* SQL filters on categoricals are normalised to case-insensitive matches automatically.
* A CI test fails if any code or value used in code or templates doesn't exist in the profiled catalog.

### 3. Acceptance Criteria
- [ ] Zero catalog/data mismatches (test).
- [ ] `session_memory`, `router`, `query_data` and `turn_runner` all use the single dictionary.
- [ ] "last year" resolves to FY25 relative to the FY26 as-of date.

---

## FEAT-009: QuerySpec Planner & Compiler (Replaces Keyword Fast-Paths)

### 1. Problem
About 1,000 lines of keyword fast-paths in `turn_runner.py` answer before the question is understood. They return canned aggregates, hijack unrelated questions, and can't express follow-ups ("compare this with Mumbai").

### 2. Required Behavior
* **QuerySpec** (Pydantic): `subject, grain (aggregate|roster|trend|compare|distribution|lookup), measures[], dimensions[], filters{}, time{}, compare_to{}, columns[], sort, limit`.
* **Planner:** Gemini structured output; input = question + previous QuerySpec + semantic catalog summary; output = new QuerySpec **or** a patch to the previous one.
* **Compiler:** QuerySpec → certified template (exact match) or generated SQL over the semantic layer → dry-run validate → execute (async).
* Fast-paths are reduced to greeting and screen-control only. Runs behind `YUKTI_PLANNER=1` until its gate passes.

### 3. Acceptance Criteria
- [ ] The flagship chain works: *Delhi 5+ yrs → give me their names → by discipline → compare with Mumbai → only E5 and above → last year → draft transfer note*.
- [ ] Eval: root ≥ 80%, follow-ups ≥ 60% at the B2 gate (≥ 90% / ≥ 85% at H1).
- [ ] No answer is produced from a keyword fast-path for data questions.
- [ ] Finance flagship chain works: *most profitable / loss-making fields FY26 → by capex invested → under-invested vs reserves → vs MoU target → draft board note* (V4).

---

## FEAT-010: Granular-Data RBAC Policy (Row/Column Masking)

### 1. Policy (Verbatim 14 D-5; Verbatim 15 D-10, D-11)
| Persona class | Personas | Granular / named data | Statutory-confidential (individual pay, APAR, vigilance, POSH, medical) |
|---|---|---|---|
| **Leadership** | CMD | ✅ Full | ✅ Full (D-10) |
| **Directors** | DIR_HR, DIR_FIN | ✅ Full (names, designation, grade, tenure, posting) | ✅ Full (D-10) |
| **Junior (E1–E4)** | E2_HR, E3_FIN (+ future E1/E4) | ❌ Aggregated summary only (no names; cells < 5 suppressed) (D-11) | ❌ Refused (D-11) |

### 2. Required Behavior
* A policy table (`rbac_policy.yaml`) maps persona class × data class → `allow | mask | aggregate | refuse`, applied to the QuerySpec (pre-query) and the result columns (post-query).
* **Consistency rule:** `access.status`, the spoken text and the visual must agree. A refusal never ships a granular chart.
* The UI shows a masked-column state (🔒 badge, policy reference) and an aggregate-instead banner.

### 3. Acceptance Criteria
- [ ] RBAC matrix test: every persona × data class gives the expected outcome (100%).
- [ ] Zero leaks in the eval refusal suite.
- [ ] E2_HR "names in Delhi 5+ yrs" → aggregate summary or refusal, with `access.status` matching.

---

## FEAT-011: Insight Engine & Drill-Down Chips ("Granular Insights")

### 1. Problem
Answers narrate rows. Nothing computes the "so what": share, rank, change, gaps vs target, outliers, named exceptions, or the next decision.

### 2. Required Behavior
* A deterministic insight library runs on every result set: total and share, top/bottom-N with names, change vs last year and vs sanctioned/target, concentration, outliers (robust z-score), and policy flags (e.g. 5-year rotation, retiring ≤ 3 yrs, exemption tags).
* Each data answer carries **2–4 insights** (FEAT-007 `insights_v2`) and **2–3 drill-down chips** (gates check the minimum: ≥ 2 each) (names / by grade / compare / trend / draft note).
* The narrator may cite only computed insight values. A numeric-grounding check rejects any number not in the result or insight set.

### 3. Acceptance Criteria
- [ ] ≥ 2 grounded insights per data answer across the question bank.
- [ ] 0 ungrounded numbers in the eval (automated check).
- [ ] Drill-down chips execute as follow-up QuerySpec patches.
- [ ] Finance answers (P&L, capex, under-investment) carry the same insight types as HR answers (V4).
- [ ] Spoken answers are **brief: 2–4 sentences** (V8 §4: neither one-liner nor full answer).

---

## FEAT-012: Reliability, Safety & Performance Hardening

Covers the remaining items from the 2026-10-22 bug audit (P2 2.11–2.16, 2.22; P3):
* Async BigQuery and embeddings (`asyncio.to_thread`), and voice tool calls moved off the Gemini receive loop.
* SQL safety: re-validate repaired SQL, parameterised certified fallbacks, allow-list that can't be bypassed via backticks or other projects.
* Contract validation errors are caught; bounded session, ADK and visual-history memory; no in-place mutation of cached objects.
* `server.js` HTTPS backend support, and upstream abort on client disconnect.
* Export filename sanitisation (path traversal).

**Acceptance:** each item has a regression test or a documented check; p50 ≤ 5.0 s.

---

## FEAT-013: Voice Pipeline Quality

* Barge-in uses raw mic RMS (no synthetic floor). Local stop also drops incoming audio and sends `interrupt` to the server.
* An in-flight guard on mic start (no leaked `getUserMedia` streams). Final frame flushed on stop; playback context closed on unmount.
* The SpeechRecognition fallback runs only when Live is down, with no duplicate REST and Live turns, and no relaunch loop on fatal errors.
* Fixes for the stale `onclose` after `reconfigure()`, Devanagari command regexes, and aborted-turn `busy` handling.

**Acceptance:** scripted voice tests (`voice_e2e_test.js`) pass. On speakers Yukti isn't cut off by her own echo. Double-click on the mic opens one stream.

---

## FEAT-014: Eval-Gated Release & Cloud Run Redeploy

* Re-run the 773-turn cache-OFF eval on `baseline-v0.2` (U0) to set the real baseline after the P1 fixes.
* A fast **gate subset** (≈ 120 turns: flagship chains, RBAC suite, a paraphrase sample) runs at every B-phase gate; the full eval runs at H1.
* The scorecard is stored per gate in `yukti/backend/eval/gates/<phase>.md`.
* Cloud Run redeploy (`yukti-ai`, asia-south1) only after H1 sign-off; smoke test via `gcloud run services proxy`.

---

## FEAT-015: Any-Chart Re-presentation & Chart Excellence

### 1. User Problem Statement (Verbatim 15)
The same data should be presentable in many ways. The system picks a sensible default, but the CMD can say *"show this as a pie chart"* (even when the default was a histogram) and the interface re-plots the **same data** in that form. Charts are the platform's **first impression**, so they must be elegant and of the highest professional standard.

### 2. Required Behavior
* **Chart compatibility matrix:** for every data shape (categorical × 1 measure, categorical × n measures, time series, distribution/raw numeric, two numerics, hierarchy, part-to-whole, geo, ranked list, single KPI) define the valid chart types and the **transform** each one needs, for example:
  * histogram → pie/donut: bins become slices (`"25–30 yrs"`), with "Other" collapsing above 8 slices
  * raw rows → bar: aggregate by the chosen dimension
  * multi-measure → pie: ask which measure, or default to the primary one
  * time series → pie: allowed only as a "share of total over period", with a note
* **Re-plot engine (frontend, data-preserving):** re-plots instantly from the data already on the card (no new query) for any compatible type. When a type is incompatible, it shows the **closest valid alternative** and a one-line explanation ("A pie needs parts of a whole; showing a donut of the 6 age bands instead").
* **Voice/text and toolbar parity:** "plot as pie / histogram / treemap / line / table…" by voice or text and the chart-type switcher give identical results. Supported set: `bar, hbar, stacked_bar, grouped_bar, line, area, combo, pie, donut, histogram, scatter, bubble, treemap, heatmap, waterfall, funnel, gauge, bullet, map, table, kpi`.
* **Chart design system (ECharts theme):**
  * Tokenised palette (D-13) with a categorical sequence, a sequential ramp and a diverging ramp (loss in maroon/red).
  * Typography that matches the UI, tabular numerals, and Indian number formatting (₹ Cr / Lakh, %).
  * Subtle gridlines, no chart junk, direct labels where possible, and smart label collision avoidance.
  * Rich tooltips (value, share, rank), tasteful entry/morph animation (≤ 400 ms) when switching type, and light/dark parity.
  * Export-quality rendering: PNG/SVG at 2× resolution.
* **Chart quality rubric** used at every visual review: hierarchy, clarity, labelling, colour semantics, density, accessibility (colour-blind-safe palette, contrast), motion, and consistency.

### 3. Acceptance Criteria
- [ ] Compatibility matrix documented (`docs/chart_compatibility.md`) and implemented as one function used by voice, text and toolbar.
- [ ] For every data-shape fixture, every compatible chart type renders without error (automated sweep), and incompatible requests show the nearest alternative plus an explanation.
- [ ] "Show this as a pie chart" on a histogram card re-plots in ≤ 300 ms with no backend call, and the slices equal the bins.
- [ ] Every chart type scores ≥ 4/5 on each rubric criterion in the U5 visual review (sponsor confirms).

---

## FEAT-016: AI Aura Visual Language

**Source:** Verbatim 16 · **Decision:** D-16 · **Prototype:** `/design-system` → "AI Aura" (U1.6)

* Google brand hues rendered as **feathery pastel light** (never solid): a thin rotating arc with an outside-only halo for the ask bar, orb and newest-answer edge, plus a pale bloom behind the greeting.
* Motion encodes state: idle (slow drift, 16 s), listening (6 s), thinking (2.8 s); reduced-motion safe.
* **Scope:** AI-presence elements only. Never data, page backgrounds or text.

**Acceptance:** U4 ask bar, greeting and newest-answer edge plus the U3 orb use the aura tokens/classes; `lint:tokens` and `lint:contrast` OK; sponsor confirms in the main app at the U4/U3 gates.
