# Yukti AI — Feature List v3 & Requirements Specification

**Location**: `feature_list_and_verbatims/feature_list/` · **Version**: v3 (re-baselined 23-Oct-2026 after the deep diagnosis) · **Prior version**: [`docs/archive/v2_2026-10-22/feature_list_v2.md`](../../docs/archive/v2_2026-10-22/feature_list_v2.md)
**Linked Verbatims**: [`../verbatims/`](../verbatims/) (V1–V23) · **Process**: five gates in [`BUILD.md`](../../BUILD.md) §4 · **Steps**: [`UPGRADE_CHECKLIST.md`](../../UPGRADE_CHECKLIST.md) (v3) · **Specs**: [`docs/specs/`](../../docs/specs/) · **Behaviours**: [`docs/behaviour/`](../../docs/behaviour/) · **Bugs**: [`BUG_REGISTER.md`](../../BUG_REGISTER.md)

> [!IMPORTANT]
> **BLUF:** of 32 features, **3 are verified working**, **12 partial**, **12 broken** and **5 missing**. The v2 list marked all 16 features "Done"; five of those claims (FEAT-002, 009, 010, 013, 014) are contradicted by code or sponsor feedback and are downgraded here. The critical path is **FEAT-018 (real finance SSOT) → FEAT-024 (V20) → FEAT-029 (DCF)** and **FEAT-017/021/023 (personas, Employee-360, V19)**.

**Status legend** (evidence-based, from the 23-Oct diagnosis):
✅ **Implemented-verified** · 🟡 **Partial** (works for some paths/cases) · 🔴 **Broken** (claimed or built, but wrong/failing) · ⛔ **Missing** (no code)

---

## Feature Index (v3)

| ID | Feature | Verbatims | Pri | Phase (v3) | Spec | v2 claim | **v3 status** | Evidence / gap (diagnosis ref) |
|---|---|---|---|---|---|---|---|---|
| FEAT-001 | Scrollable conversation feed (history) | V8, V11 | P0 | — | — | Done | ✅ | `ConversationFeed.tsx`, `state/feed.ts`; panel thread duplicates in voice mode → BUG-17 |
| FEAT-002 | Multi-turn context & entity carry-over | V11 | P0 | P5 | SPEC-11 | Done | 🟡 | Planner path only; legacy/fast-paths push `{}` (turn_runner.py:577); no year clarification; `resolve_fy` regression BUG-20 |
| FEAT-003 | Visual presentation audit | V7, V11 | P1 | — | — | Done | ✅ | `docs/visual_audit.md` (superseded by FEAT-025/026 for finance) |
| FEAT-004 | Voice orb (Aurora wave) | V12 | P2 | P4 | SPEC-09 | Done | 🟡 | Built, but only shown when panel minimised (FloatingConversationPanel.tsx:236-247) |
| FEAT-005 | Executive UI modernisation | V12 | P1 | — | — | Done | ✅ | U1/U4 design system; tsc + lint clean |
| FEAT-006 | CMD named employee roster | V13 | P0 | P2H | SPEC-07 | Done | 🟡 | Roster SQL works; data realism defects (E1 median 19.6 yrs service, 1,393 names) → FEAT-021 |
| FEAT-007 | Answer contract v2 | V14 | P0 | P3 | SPEC-03 | Done | 🟡 | Works; lacks `proposed_action`, `job`, `statement` visual → v3 contract |
| FEAT-008 | Generated semantic layer | audit | P0 | P1 | SPEC-01 | Done | 🟡 | Exists; no pay components, WACC, statement-coverage manifest |
| FEAT-009 | QuerySpec planner & compiler (replaces fast-paths) | V11, V13 | P0 | P5 | SPEC-11 | Done | 🔴 | ~25 keyword branches + hard-coded answers still run before the planner (turn_runner.py:1541-1550, 2161-2228) |
| FEAT-010 | Granular-data RBAC (row/column masking) | V3, V13, V14 | P0 | P0/P2H | SPEC-06 | Done | 🔴 | Masking engine ✅ (77 tests), but persona escalation by voice (BUG-06) and hard-coded self emp_id (BUG-07) |
| FEAT-011 | Insight engine & drill-down chips | V13, V14 | P0 | P2F | SPEC-08 | Done | 🟡 | Works for HR; finance "why/action" is canned text with circular grounding (BUG-16) |
| FEAT-012 | Reliability, safety, performance | audit | P1 | P0 | SPEC-11 | Done | 🟡 | H1 work done; CORS `*`, open admin route (BUG-32), error leakage (BUG-33) |
| FEAT-013 | Voice pipeline quality (no duplicate turns) | V6, V8 | P1 | P5 | SPEC-11 | Done | 🔴 | Duplicate/fragment bubbles from barge-in echo (live_session.py:804; BUG-17, BUG-18) |
| FEAT-014 | Eval-gated release & Cloud Run redeploy | V14 | P1 | P5 | SPEC-11 | Done | 🔴 | Cloud Run = baseline rev 00001; 70 failing tests; stress test is shape-only |
| FEAT-015 | Any-chart re-presentation & chart excellence | V7, V15 | P0 | P4 | SPEC-09 | Done | 🟡 | ~15/29 types; waterfall re-plot wrong (BUG-08); explicit kind overridden (BUG-22) |
| FEAT-016 | AI aura visual language | V16 | P2 | P4 | SPEC-09 | Done | 🟡 | Only a 2.5 px ask-bar arc; V21 marks low priority |
| **FEAT-017** | **Eleven-persona matrix + function split + `self` scope** | V17 | **P0** | P2H | SPEC-06 | — | 🔴 | 5 of 11 personas; unknown → E2_HR; no HR/Finance split; juniors see EMP-102451 data |
| **FEAT-018** | **Real financial SSOT with page lineage + verification gates** | V18 | **P0** | P1 | SPEC-01 | — | 🔴 | Current data LLM-authored with plugs (build_10yr_financials.py:29-1120, :1193, :1223); BS/CF 1/17 match |
| **FEAT-019** | **Yahoo Finance ingestion (consolidated view) + market data** | V18, V20, V22 | **P0** | P1 | SPEC-01/02 | — | ⛔ | Never ingested; only labels. Endpoints reachable; FY23–FY26 consolidated |
| **FEAT-020** | **Knowledge RAG over real AR text** | V18, V20 | P1 | P1 | SPEC-01 | — | 🔴 | Corpus = f-strings over invented numbers; keyword retrieval; BQ vectors never queried |
| **FEAT-021** | **Employee-360 enterprise table (realistic, reconciled)** | V13, V19, V23 | **P0** | P2H | SPEC-04 | — | 🟡 | Granular data exists (22,798 active, 198,880 postings, 1.68M payslips); realism defects; no benefits/insurance/CTC; no AR reconciliation |
| **FEAT-022** | **Field economics-360 reconciled to company AR totals** | V18, V23 | **P0** | P2H | SPEC-05 | — | 🔴 | Field P&L "scaled" top-down to invented totals (load_and_reconcile_bq.py:204-258); production off vs AR |
| **FEAT-023** | **V19 transfer workflow: Excel intent + Email agent** | V19 | **P0** | P2H | SPEC-07 | — | 🔴 | Steps 1–3 OK in code; step 4 intent missing (ui_control.py:291); step 5 missing (canned proposal, draft_document.py:105-131) |
| **FEAT-024** | **V20 finance diagnostics (year-clarify, multi-year statement, WACC, why, top-5 actions)** | V20 | **P0** | P2F | SPEC-08, SPEC-02 | — | ⛔ | No year question; no WACC; 1 canned action per statement-year |
| **FEAT-025** | **Financial statement table visual** | V21 | **P0** | P4 | SPEC-09 | — | 🟡 | Defaults to table ✅, but generic sortable grid (no indent/subtotals/(neg)/FY columns) |
| **FEAT-026** | **Chart portfolio completion + correct waterfall** | V7, V15, V21 | **P0** | P4 | SPEC-09 | — | 🔴 | Waterfall total ≈ 3× revenue; EBITDA fabricated (`rev*0.68`); combo/heatmap/box/gauge no renderer |
| **FEAT-027** | **Export suite** | V2, V7, V21 | P1 | P4 | SPEC-10 | — | 🟡 | xlsx (unformatted), docx ✅; PDF ₹/Hindi broken; fake Docs URL; no CSV/PNG/SVG |
| **FEAT-028** | **Coordinator + agent registry + jobs + permission UX** | V22 | **P0** | P3 | SPEC-03 | — | ⛔ | No orchestrator/sub-agents/jobs/permission field |
| **FEAT-029** | **DCF valuation agent** | V22 | **P0** | P3 | SPEC-02 | — | ⛔ | No DCF/WACC code; no market inputs |
| **FEAT-030** | **One-brain consolidation + numeric golden eval** | bugs | **P0** | P5 | SPEC-11 | — | ⛔ | 3 divergent brains; shape-only stress test |
| **FEAT-031** | **Identity & security hardening** | V3, V17 | **P0** | P0 | SPEC-06 | — | 🔴 | Client-asserted persona; CORS `*`; unauthenticated admin route |
| **FEAT-032** | **Provenance honesty & degraded-mode transparency** | V18, V23 | **P0** | P0 | SPEC-11 | — | 🔴 | False "Audited + Yahoo / BigQuery" labels while serving local JSON; Gemini clauses unlabeled |

**Counts:** ✅ 3 · 🟡 12 · 🔴 12 · ⛔ 5 = 32 (per-verbatim scorecard: diagnosis §2).

---

## v3 Feature Definitions (FEAT-017 → FEAT-032)

### FEAT-017 — Eleven-Persona Matrix, Function Split & `self` Scope (V17)
- **Problem:** only CMD, DIR_HR, DIR_FIN, E2_HR, E3_FIN exist; HR and Finance juniors share one policy; juniors' "my" questions resolve to one hard-coded employee.
- **Required:** personas CMD, DIR_HR, DIR_FIN, E1_HR, E2_HR, E3_HR, E4_HR, E1_FIN, E2_FIN, E3_FIN, E4_FIN, each seeded from a real synthetic employee row (`dim_app_user`). Juniors: aggregate (k≥5) within their function, HR policy for all, `self` scope (own payslip, leave, posting, entitlements), aggregate pay by grade allowed, named/pay/sensitive refused. Directors: full within function and cross-function aggregates per SPEC-06; CMD: everything.
- **Acceptance:** 11 personas × data classes test matrix 100% pass; zero cross-employee leakage on `self`; any persona can ask any question and gets either an answer + insight or a polite refusal with an allowed alternative (V17 "should get responses and insights").

### FEAT-018 — Real Financial SSOT (V18)
- **Required:** `hrfin_gold.fact_financial_statement_line` built from ONGC ARs (standalone FY17–FY26; consolidated FY22–FY26), NSE XBRL backfill, every row with `source_doc`, `source_page`, `extraction_method`, `verified`. No plug lines. Companion `dim_financial_line`, `fact_segment`, `fact_production_annual` (with `basis`), `fact_reserves`, `fact_hr_aggregates`.
- **Acceptance:** 100% of AR-reported subtotals reproduced within ₹0.05 cr; A = E + L; closing cash ties; cross-AR comparatives agree or are flagged restated; app reads only `verified=TRUE`; UI shows doc + page. Old `build_10yr_financials.py` and `corporate_financial_summary.csv` retired.

### FEAT-019 — Yahoo Finance & Market Data (V18, V20, V22)
- **Required:** raw Yahoo fundamentals (annual + quarterly) and prices (ONGC.NS, ^NSEI) stored as `source='yahoo', basis='consolidated'`; a "Yahoo view" statement layout; cross-check vs AR consolidated within ₹1 cr; market inputs for WACC/DCF.
- **Acceptance:** "show the Yahoo Finance income statement" renders FY23–FY26 consolidated with a basis label; FY26 values equal AR consolidated.

### FEAT-020 — Knowledge RAG over Real AR Text (V18, V20)
- **Required:** `doc_chunks_ar` from AR MD&A, Directors' Report, Notes (page-referenced), embedded; BQ `VECTOR_SEARCH` + structured line lookup; every "why" sentence cites doc + page.
- **Acceptance:** 0 generated-narrative chunks in the corpus; retrieval eval ≥ 80% hit@5 on a 30-question set.

### FEAT-021 — Employee-360 Enterprise Table (V13, V19, V23)
- **Required:** one analysis-ready BigQuery table `hrfin_gold.ssot_employee_360` (grain per SPEC-04) with identity, org, tenure/postings, full monthly pay (basic, IDA/DA, HRA, cafeteria/perks, field/offshore/hard-duty allowances, overtime hours & amount, PRP), employer benefits (CPF, PRBS, gratuity, PRMB, health/group insurance, medical scheme, leave encashment, LTC, housing), deductions, CTC, capitalised vs expensed cost, leave, training, APAR (sensitive), attrition flags, cost-centre/field link. Realistic career pyramid and names.
- **Acceptance:** Σ annual employee cost per FY = AR employee-benefit expense (tolerance per SPEC-04); FY-end headcount = AR "Number of Employees"; gender/category/PwD/age-band shares = AR/BRSR; `recon_checks` all PASS; derived KPIs (revenue/employee, cost/employee, overtime %, etc.) exposed in the semantic model.

### FEAT-022 — Field Economics-360 Reconciled to Company (V18, V23)
- **Required:** `hrfin_gold.ssot_field_economics_360` (field × month / FY): production (basis), price, revenue, levies, opex by nature (incl. employee cost from FEAT-021), DD&A, exploration write-off, EBITDA, PBT, opex/boe, capex, headcount. Field splits modelled and labelled; totals real.
- **Acceptance:** Σ fields + explicit HQ/unallocated = AR standalone P&L lines per FY exactly; Σ offshore/onshore = AR segment note; Σ production = AR/PPAC totals per basis.

### FEAT-023 — V19 Transfer Workflow Completion
- **Required:** Delhi-by-level (ordered E1→E9) → >5 yrs (one canonical definition) → names roster → "export as Excel" (any phrasing, EN + Hindi, requested columns) → "draft an email to Director HR" (editable draft, cohort counts, Illustrative JRTP clause + real J-03 anchor, xlsx attached, .eml/.docx/mailto).
- **Acceptance:** BEH-02 5-turn chain passes for CMD and DIR_HR; E-level personas get aggregate/refusal at step 3; no hard-coded numbers.

### FEAT-024 — V20 Finance Diagnostics & Prescriptive Actions
- **Required:** year clarification chips; Yahoo-style multi-year statement (4–10 FY columns); WACC 5/10-yr chart from `fact_wacc_annual`; variance attribution per line item; "why" grounded in data + AR chunks; top-5 actions (lever, ₹ impact, owner, evidence).
- **Acceptance:** BEH-03 chain passes with exact SSOT values; every action has a quantified impact and cited evidence; zero canned text.

### FEAT-025 — Financial Statement Table Visual (V21)
- **Required:** `visual.type="statement"`: indented hierarchy, bold subtotals with rules, `(negatives)`, lakh-crore grouping, FY columns, sticky first column, no sorting/inline bars, footnote with source + page.
- **Acceptance:** finance rubric (SPEC-09) ≥ 9/10 on IS/BS/CF in light + dark.

### FEAT-026 — Chart Portfolio & Correct Waterfall (V7, V15, V21)
- **Required:** signed P&L bridge shared backend/frontend (ends at reported PAT); never fabricate values; explicit chart kind wins; add combo dual-axis, 100% stacked, heatmap, sensitivity grid, tornado, box, gauge, sunburst, sankey, bubble, state choropleth; data-shape compatibility matrix (no histogram for statements).
- **Acceptance:** unit test FY24 waterfall ends at PAT ₹40,526 cr (AR); every contract kind has a renderer; rubric scorecards ≥ 9/10.

### FEAT-027 — Export Suite (V2, V7, V21)
- **Required:** formatted xlsx (incl. DCF assumptions sheet), CSV, PDF with embedded Noto fonts + tables + chart image, PNG/SVG, docx, .eml; honest Google Sheets/Docs behaviour until Drive OAuth; voice/text intents per format; RBAC-masked exports + audit log.
- **Acceptance:** ₹ and Devanagari render (pdftotext check); every rendered card exports in ≥ 4 formats.

### FEAT-028 — Coordinator, Agents, Jobs & Permission UX (V22)
- **Required:** one interface; coordinator routes to analyst, fin_diagnostics, dcf, hr_transfer, doc_export agents; contract `proposed_action` + `job`; Run / Edit assumptions / Cancel (voice "yes, run it"); jobs API with progress stream; RBAC gating.
- **Acceptance:** BEH-05 flow passes by voice and text; job progress visible; result persisted in session.

### FEAT-029 — DCF Valuation Agent (V22)
- **Required:** deterministic DCF on verified FCFF; WACC build-up from sourced inputs; terminal value (Gordon + exit-multiple check); EV→equity bridge; per-share value vs market price; WACC×g grid; tornado; xlsx with live formulas; "illustrative valuation" disclaimer.
- **Acceptance:** fixture test matches hand computation to ₹0.01/share; sensitivity grid symmetric checks; conclusion sentence states % under/over-valuation with assumptions.

### FEAT-030 — One Brain & Numeric Golden Eval
- **Required:** every data question through one route; fast-paths and hard-coded answers deleted or turned into deterministic intents; coverage manifest; voice speaks `spoken_summary` verbatim; numeric golden set (~60 user-phrased + V19/V20/V22 chains + voice smoke).
- **Acceptance:** golden eval ≥ 95% exact on numbers; feedback1–4 regressions all pass; Cloud Run redeployed from a green tree.

### FEAT-031 — Identity & Security Hardening
- **Required:** server-side persona (signed token for demo; IAP for prod); no voice/text role switching for non-admins; `@self_emp_id`; CORS allow-list; authenticated admin routes.
- **Acceptance:** escalation tests fail closed; SPEC-06 §7 acceptance criteria 3, 4, 8 and 9 pass.

### FEAT-032 — Provenance Honesty & Degraded Modes
- **Required:** source badges (Verified AR p.N / Yahoo consolidated / Modelled / Illustrative / Local snapshot); Gemini-generated policy clauses labelled **Illustrative** (D-35); synthetic employee records labelled; auth/health banner; generic error text.
- **Acceptance:** no answer claims a source it did not use (automated check in eval).

---

## Legacy Feature Detail (FEAT-001 → FEAT-016, from v2; statuses above supersede any "Done" text below)

### FEAT-001: Scrollable Conversational Feed (History Preservation)

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
- [x] Asking Question B after Question A does not erase Question A's card.
- [x] The user can scroll up to view Question A's exact visual and tabular outputs.
- [x] Responsive across full-screen canvas and floating chat modes.

---

### FEAT-002: Multi-Turn Context & Entity Carryover

### 1. User Problem Statement
Every question is currently evaluated in isolation. If a user asks *"How many employees are in New Delhi?"* and follows up with *"Break them down by discipline"*, the system does not remember that "them" refers to Delhi employees, causing failures or irrelevant answers.

### 2. Required Behavior
* **Contextual Entity Resolution**: The agent backend retains the active entity context (e.g. `location: "Delhi"`, `cadre: "Executive"`, `fiscal_year: "FY26"`, `field: "Mumbai High"`) across turns within the same session.
* **Multi-Turn Chat History in Prompts**: The backend passes conversation turn history (user questions, tool outputs, agent summaries) to Gemini so follow-up queries naturally inherit antecedents and filters.
* **Session Reset Option**: A clear "New Session / Clear Context" action allowing the user to start a fresh topic when desired.

### 3. Acceptance Criteria
- [x] Follow-up questions referencing pronouns or implicit filters ("break them down", "compare this with last year", "show only loss-making ones") correctly resolve context from the immediate prior turn.
- [x] Session memory persists across voice and text turns within the current browser session.

---

### FEAT-003: Visual Presentation & Charting Audit

### 1. Objective
Conduct an exhaustive audit of all visual representations (charts, KPI metrics, geospatial maps, data tables, and document drafts) across the entire question bank to identify presentation gaps and elevate visual polish.

### 2. Scope of Upcoming Audit
* Map every data question type (categorical, time-series, geospatial, tabular, hierarchical) to its optimal visual format (ECharts, Survey of India map, structured card, rich document).
* Identify gaps where plain text is returned instead of an actionable visual.
* Ensure visual hierarchy, color palette, and responsiveness match ONGC leadership expectations.

### 3. Acceptance Criteria
- [x] `docs/visual_audit.md` maps all 107 question-bank items to a visual type, with gaps listed.
- [x] Every mapped item renders its visual from a fixture (U5.6 sweep: 0 failures).
- [x] No data answer renders as plain text only when a visual type is mapped.

---

### FEAT-004: Luminous Siri / Infinity Loop Voice Orb

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
- [x] No scattered or vibrating dots.
- [x] Smooth 60fps canvas or SVG rendering without CPU spikes.
- [x] Clear visual distinction between Idle, Listening, Thinking, and Speaking states.

---

### FEAT-005: Executive UI Modernization & Enterprise Material Polish

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
- [x] Clean, uncluttered layout maintaining single-click access to all actions.
- [x] Polished executive styling for all rendered tables, charts, and document previews.

---

### FEAT-006: CMD Actionable Employee-Level Roster (Drilldown from Aggregates)

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
- [x] Asking for employee names in Delhi for 5+ years returns individual rows, not just aggregate counts.
- [x] Columns include Name, Designation, Grade, Total Tenure, and Delhi Station Tenure.
- [x] Table supports sorting by tenure and filtering by discipline/grade.
- [x] E1–E4 personas (E2_HR, E3_FIN) receive an aggregate or a refusal (no names), and `access.status` matches the text and the visual.

### 4. Update 2026-10-22 (audit + Verbatim 14)
* **Data correction:** the roster data already exists in `hrfin_gold.ssot_workforce_employee` (`emp_name`, `grade_id`, `discipline_name`, `total_tenure_years`, `continuous_stay_years`, `wc_id`; all 692 active Delhi executives are named). The `dim_employee` / `fct_posting` tables proposed in `data_gap_analysis_employee_roster.md` do not exist and are **not needed**. Remaining data check: designation field (`grade_designation` in SSOT vs `current_designation` in `mart_workforce`).
* **Value-case trap:** BigQuery stores `employment_status = 'Active'` while the catalog says `'active'`, which silently returns 0 rows. Fixed by FEAT-008.
* **RBAC per D-5:** CMD **and all Directors** get the unmasked roster. E1–E4 get an aggregate or a refusal per FEAT-010 (OD-3).



---

### FEAT-007: Answer Contract v2 (Forward-Compatible UI ↔ Brain)

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
- [x] All existing fixtures and 28 backend tests still validate.
- [x] New v2 fixtures (roster, compare, insights, drill-downs) validate and render.
- [x] TypeScript types match the schema (`tsc` clean).

---

### FEAT-008: Generated Semantic Layer (Catalog = Data Truth)

### 1. Problem
The hand-written catalog disagrees with BigQuery (`'active'` vs `'Active'`, `cadre` case, WC codes that differ across modules), so generated SQL silently returns 0 rows and the app falls back to canned answers.

### 2. Required Behavior
* A script generates `semantic_catalog.json` from `INFORMATION_SCHEMA` plus profiled distinct values (categoricals ≤ 200 values), ranges and grain notes, for every SSOT, gold and silver table the agent uses.
* **One** work-centre / field / discipline dictionary (codes ↔ names ↔ aliases, including Hindi/Hinglish), imported by every module.
* SQL filters on categoricals are normalised to case-insensitive matches automatically.
* A CI test fails if any code or value used in code or templates doesn't exist in the profiled catalog.

### 3. Acceptance Criteria
- [x] Zero catalog/data mismatches (test).
- [x] `session_memory`, `router`, `query_data` and `turn_runner` all use the single dictionary.
- [x] "last year" resolves to the last complete FY (FY26, anchor 19-Oct-2026, current FY27) per D-30 (was: "FY25 relative to the FY26 as-of date").

---

### FEAT-009: QuerySpec Planner & Compiler (Replaces Keyword Fast-Paths)

### 1. Problem
About 1,000 lines of keyword fast-paths in `turn_runner.py` answer before the question is understood. They return canned aggregates, hijack unrelated questions, and can't express follow-ups ("compare this with Mumbai").

### 2. Required Behavior
* **QuerySpec** (Pydantic): `subject, grain (aggregate|roster|trend|compare|distribution|lookup), measures[], dimensions[], filters{}, time{}, compare_to{}, columns[], sort, limit`.
* **Planner:** Gemini structured output; input = question + previous QuerySpec + semantic catalog summary; output = new QuerySpec **or** a patch to the previous one.
* **Compiler:** QuerySpec → certified template (exact match) or generated SQL over the semantic layer → dry-run validate → execute (async).
* Fast-paths are reduced to greeting and screen-control only. Runs behind `YUKTI_PLANNER=1` until its gate passes.

### 3. Acceptance Criteria
- [x] The flagship chain works: *Delhi 5+ yrs → give me their names → by discipline → compare with Mumbai → only E5 and above → last year → draft transfer note*.
- [x] Eval: root ≥ 80%, follow-ups ≥ 60% at the B2 gate (≥ 90% / ≥ 85% at H1).
- [x] No answer is produced from a keyword fast-path for data questions.
- [x] Finance flagship chain works: *most profitable / loss-making fields FY26 → by capex invested → under-invested vs reserves → vs MoU target → draft board note* (V4).

---

### FEAT-010: Granular-Data RBAC Policy (Row/Column Masking)

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
- [x] RBAC matrix test: every persona × data class gives the expected outcome (100%).
- [x] Zero leaks in the eval refusal suite.
- [x] E2_HR "names in Delhi 5+ yrs" → aggregate summary or refusal, with `access.status` matching.

---

### FEAT-011: Insight Engine & Drill-Down Chips ("Granular Insights")

### 1. Problem
Answers narrate rows. Nothing computes the "so what": share, rank, change, gaps vs target, outliers, named exceptions, or the next decision.

### 2. Required Behavior
* A deterministic insight library runs on every result set: total and share, top/bottom-N with names, change vs last year and vs sanctioned/target, concentration, outliers (robust z-score), and policy flags (e.g. 5-year rotation, retiring ≤ 3 yrs, exemption tags).
* Each data answer carries **2–4 insights** (FEAT-007 `insights_v2`) and **2–3 drill-down chips** (gates check the minimum: ≥ 2 each) (names / by grade / compare / trend / draft note).
* The narrator may cite only computed insight values. A numeric-grounding check rejects any number not in the result or insight set.

### 3. Acceptance Criteria
- [x] ≥ 2 grounded insights per data answer across the question bank.
- [x] 0 ungrounded numbers in the eval (automated check).
- [x] Drill-down chips execute as follow-up QuerySpec patches.
- [x] Finance answers (P&L, capex, under-investment) carry the same insight types as HR answers (V4).
- [x] Spoken answers are **brief: 2–4 sentences** (V8 §4: neither one-liner nor full answer).

---

### FEAT-012: Reliability, Safety & Performance Hardening

Covers the remaining items from the 2026-10-22 bug audit (P2 2.11–2.16, 2.22; P3):
* Async BigQuery and embeddings (`asyncio.to_thread`), and voice tool calls moved off the Gemini receive loop.
* SQL safety: re-validate repaired SQL, parameterised certified fallbacks, allow-list that can't be bypassed via backticks or other projects.
* Contract validation errors are caught; bounded session, ADK and visual-history memory; no in-place mutation of cached objects.
* `server.js` HTTPS backend support, and upstream abort on client disconnect.
* Export filename sanitisation (path traversal).

**Acceptance:** each item has a regression test or a documented check; p50 ≤ 5.0 s.

---

### FEAT-013: Voice Pipeline Quality

* Barge-in uses raw mic RMS (no synthetic floor). Local stop also drops incoming audio and sends `interrupt` to the server.
* An in-flight guard on mic start (no leaked `getUserMedia` streams). Final frame flushed on stop; playback context closed on unmount.
* The SpeechRecognition fallback runs only when Live is down, with no duplicate REST and Live turns, and no relaunch loop on fatal errors.
* Fixes for the stale `onclose` after `reconfigure()`, Devanagari command regexes, and aborted-turn `busy` handling.

**Acceptance:** scripted voice tests (`voice_e2e_test.js`) pass. On speakers Yukti isn't cut off by her own echo. Double-click on the mic opens one stream.

---

### FEAT-014: Eval-Gated Release & Cloud Run Redeploy

* Re-run the 773-turn cache-OFF eval on `baseline-v0.2` (U0) to set the real baseline after the P1 fixes.
* A fast **gate subset** (≈ 120 turns: flagship chains, RBAC suite, a paraphrase sample) runs at every B-phase gate; the full eval runs at H1.
* The scorecard is stored per gate in `yukti/backend/eval/gates/<phase>.md`.
* Cloud Run redeploy (`yukti-ai`, asia-south1) only after H1 sign-off; smoke test via `gcloud run services proxy`.

---

### FEAT-015: Any-Chart Re-presentation & Chart Excellence

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
- [x] Compatibility matrix documented (`docs/chart_compatibility.md`) and implemented as one function used by voice, text and toolbar.
- [x] For every data-shape fixture, every compatible chart type renders without error (automated sweep), and incompatible requests show the nearest alternative plus an explanation.
- [x] "Show this as a pie chart" on a histogram card re-plots in ≤ 300 ms with no backend call, and the slices equal the bins.
- [x] Every chart type scores ≥ 4/5 on each rubric criterion in the U5 visual review (sponsor confirms).

---

### FEAT-016: AI Aura Visual Language

**Source:** Verbatim 16 · **Decision:** D-16 · **Prototype:** `/design-system` → "AI Aura" (U1.6)

* Google brand hues rendered as **feathery pastel light** (never solid): a thin rotating arc with an outside-only halo for the ask bar, orb and newest-answer edge, plus a pale bloom behind the greeting.
* Motion encodes state: idle (slow drift, 16 s), listening (6 s), thinking (2.8 s); reduced-motion safe.
* **Scope:** AI-presence elements only. Never data, page backgrounds or text.

**Acceptance:** U4 ask bar, greeting and newest-answer edge plus the U3 orb use the aura tokens/classes; `lint:tokens` and `lint:contrast` OK; sponsor confirms in the main app at the U4/U3 gates.
