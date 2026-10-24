# Yukti AI: Step-by-Step Upgrade Checklist v3 (`UPGRADE_CHECKLIST.md`)

**Version:** v3 (23-Oct-2026) · **Charter:** [`BUILD.md`](BUILD.md) (five gates + truth rules §4.3) · **Features:** [`feature_list.md`](feature_list_and_verbatims/feature_list/feature_list.md) · **Bugs:** [`BUG_REGISTER.md`](BUG_REGISTER.md) · **Specs:** [`docs/specs/`](docs/specs/) · **Behaviours:** [`docs/behaviour/`](docs/behaviour/) · **Packets:** [`docs/delegation/packets/v3/`](docs/delegation/packets/v3/) · **v2 checklist (archived):** [`docs/archive/v2_2026-10-22/UPGRADE_CHECKLIST.md`](docs/archive/v2_2026-10-22/UPGRADE_CHECKLIST.md)

> [!IMPORTANT]
> **BLUF:** 62 v3 steps across P0–P5 (incl. hotfix P0.10); live counts in [`PROGRESS.md`](PROGRESS.md). Step IDs match the packet files in `docs/delegation/packets/v3/` one-to-one (**51 packets**; indexes: `_INDEX_P0_P2H1-4_P4.md`, `_INDEX_P1_P2F_P3.md`, `_INDEX_P2H5-8.md`). Critical path: **P0 → P1 (real finance SSOT) → P2F → P3 (DCF)**. P2H (personas, V19, Employee-360) and P4 (visuals) run in parallel after P0. Every data step needs numeric acceptance (BUILD §4.3).

**Owners (v3.1, D-59):** `O` = **A** (Gemini 4 Argon) on backend/data steps, **L** (lead, Opus) on frontend steps; see [`DELEGATION.md`](DELEGATION.md) v3.1. **Legend (step lifecycle):** ⬜ To do → 🔄 In progress → 🔨 Built (committed, pre-G4) → 🔍 In review → ✅ Done (only with a `docs/reviews/<step>.md` APPROVE) · ⛔ Blocked · **Owner:** O = Opus lead · F = Flash (needs a packet) · FL = Flash-lite runner · S = Sponsor · `O→F` = Opus spec/skeleton, Flash completes

> [!TIP]
> **Live dashboard:** [`PROGRESS.md`](PROGRESS.md) is generated from this file + `BUG_REGISTER.md` + feature list + packets + reviews + git. **Update rule (every completion):** change the Status cell here → close linked bugs in `BUG_REGISTER.md` → run `python3 scripts/progress/build_progress.py` (regenerate) + `--check` (validate) → commit all three together.

---

## Part A — What is already implemented (carried forward from v2; verified 23-Oct)

| Capability | Verbatim | Status | Evidence | Remaining gap → v3 step |
|---|---|---|---|---|
| Conversation feed with history, auto-scroll, refine in place | V8, V11 | ✅ | `ConversationFeed.tsx`, `state/feed.ts`; tsc/lint clean | Voice duplicate bubbles → P5.2 |
| Floating right panel (dock / minimise / fullscreen), voice screen commands | V9 | ✅ | `FloatingConversationPanel.tsx`, `ui_control.py:276-281` | Orb hidden when docked → P4.9 |
| Light default + dark mode; contrast lint | V9 | ✅ | `page.tsx:56`; `lint:contrast` 58 pairs OK | — |
| Name "Yukti", greeting, Leda voice, EN/HI detection | V8, V10 | ✅ | `/health` voice Leda; Hindi fast-path R4 | Hindi narration → P5.2 |
| Design system, tokens, executive polish | V12 | ✅ | U1/U4 reviews | — |
| RBAC masking engine (named → aggregate, k<5 suppression, pay/APAR refuse) | V3, V14 | 🔴 (FEAT-010; BUG-06, BUG-07) | 77 offline tests pass (5 personas) | 11 personas, identity → P0.4, P2H.1–2 |
| QuerySpec planner + compiler + follow-up patches | V11 | 🔴 (FEAT-009; BUG-05, BUG-12, BUG-21) | B2; works on the planner path | One brain → P5.1 |
| Named roster (Delhi > 5 yrs) SQL + roster table + export button | V13 | 🟡 | `presenter.py:128`, `RosterTable.tsx` | Realistic data → P2H.5–6; intent → P2H.4 |
| Statements default to table (P&L/BS/CF) | V21 | 🟡 | `presenter.py:218/271/332` | Real data → P1; statement visual → P4.2–4.3 |
| ECharts portfolio (~15 types), any-chart re-plot engine | V7, V15 | 🟡 | `plan.ts`, `options.ts`, `compat.ts` | Waterfall + missing kinds → P4.1, P4.4–4.5 |
| xlsx + docx export | V2 | 🟡 | `export_tool.py` | Full suite → P4.6–4.7 |
| Real public sources on disk (ARs FY21–26, BRSR, 50+ policies) | V18 | ✅ | `knowledge/public_sources/` | Extract → P1 |
| Synthetic HR headcount/diversity calibrated to AR/BRSR | V19 | ✅ | diag_B §6 | Realism + benefits → P2H.5 |
| Policy clauses (incl. Gemini-generated R16) | V2 | 🟡 | `rulebooks_clause_index.csv` | Label "Illustrative" → P0.7 (D-35) |

---

## Part B — v3 steps

### Phase P0 — Stabilise · *gate: env green, honest labels, escalation closed*

| Step | Task | Owner | FEAT | Spec/BEH | Bugs | Acceptance (checkable) | Packet | Status |
|---|---|---|---|---|---|---|---|---|
| P0.0 | Snapshot all WIP to `wip/pre-v3-snapshot` (local, no push) | O + S | — | — | — | Commit `e7de82f`; tree clean | — | ✅ |
| P0.1 | ADC restore, `/health.auth_ok`, auth banner, safe error copy | O + S → F | 032 | SPEC-11, BEH-07 | 01, 33 | Forced RefreshError → banner + generic copy; `/health.auth_ok=true` after re-auth | [P0.1](docs/delegation/packets/v3/P0.1.md) | ✅ |
| P0.2 | Fix `resolve_fy("FY 2024-25")` regression | F | 030 | SPEC-11 | 20 | 2 red tests green + new EN/HI FY-format cases | [P0.2](docs/delegation/packets/v3/P0.2.md) | ✅ |
| P0.3 | Remove false "Audited/Yahoo/Compiled SQL" labels; explicit `local_snapshot` badge | F | 032 | SPEC-11 | 02 (labels), 04 | Grep = 0 false labels; 20 sampled answers carry correct badges | [P0.3](docs/delegation/packets/v3/P0.3.md) | ✅ |
| P0.4 | Server-side persona token; block free-text role switching; audit log | O | 031 | SPEC-06 §4.4, BEH-01 | 06 | E2_HR "switch role to CMD" → refused, persona unchanged; tampered token → least privilege | [P0.4](docs/delegation/packets/v3/P0.4.md) | ✅ |
| P0.5 | CORS allow-list + admin route lock | O→F | 031 | SPEC-06 §4.7 | 32 | `/admin/*` 401 without admin claim; disallowed origin rejected | [P0.5](docs/delegation/packets/v3/P0.5.md) | ✅ |
| P0.6 | True test baseline + evidence pack (after P0.1) | FL | 014 | BUILD G3 | — | Pass/fail lists; environment-caused failures = 0 | [P0.6](docs/delegation/packets/v3/P0.6.md) | ✅ |
| P0.7 | "Illustrative" labels on synthetic clauses (JRTP Rev 4, R16) | F | 032 | SPEC-07 §4.2, SPEC-11 | 31 | Every synthetic clause answer shows the Illustrative badge (D-35) | [P0.7](docs/delegation/packets/v3/P0.7.md) | ✅ |
| P0.8 | v3 doc set (feature list, BUILD, checklist, bug register, SPEC-01…11, BEH-01…07, 51 packets) | O | — | all | — | G4 doc review approve + sponsor confirm | — | ✅ |
| P0.9 | Packaging: data-in-image vs BigQuery-only; Dockerfile fix | F | 014 | SPEC-11 | 13 (part) | Container smoke: finance answer works or shows an honest degraded badge | [P0.9](docs/delegation/packets/v3/P0.9.md) | ✅ |
| P0.10 | **Hotfix (sponsor-requested 23-Oct):** voice self-interruption. Half-duplex mic gate while Yukti speaks (browser + backend, +300 ms tail); deliberate interrupt (orb/Stop/Space; voice barge-in needs sustained louder speech ~0.4 s); lower Live start-of-speech sensitivity; `speak_id` gating so an interrupt never clears speak-only; no orphan/duplicate bubbles | O | 013 | SPEC-11 §6.3, BEH-07 | 17, 18 | Live test on the laptop with speakers: 5/5 answers play to the end without self-interrupt; tap-to-stop works 5/5; no duplicate/fragment bubbles in 5 voice + 5 typed turns; unit tests for the gate | (inline: this row) | ✅ |

### Phase P1 — Real Finance SSOT & Public Data · *gate: 100% AR subtotals ±₹0.05 cr; finance golden set 100%*

| Step | Task | Owner | FEAT | Spec/BEH | Bugs | Acceptance | Packet | Status |
|---|---|---|---|---|---|---|---|---|
| P1.1 | Acquire ARs FY16–FY20, NSE XBRL, Yahoo, RBI, Damodaran; manifest with sha256 | FL→O | 018, 019 | SPEC-01 | — | **23-Oct:** ARs FY16–FY19 (text) ✅, FY20 image-only; 12 NSE XBRL ✅; Damodaran ✅; **Yahoo HTTP 429 (retry pending)**; **RBI FY-end yields need a manual download** (Handbook Table 178). See `knowledge/public_sources/MANIFEST_v3_acquisition.md` | — | 🔄 |
| P1.2 | AR 10-yr table parser (FY13–FY26) | F | 018 | SPEC-01 §4.2 | 02 | Cross-AR overlaps agree or flagged restated; 60-line spot set = AR | [P1.2](docs/delegation/packets/v3/P1.2_ar_10yr_table_parser.md) | ✅ |
| P1.3 | Full statements + notes (S + C) incl. Notes 35, 35.1, 37, 44.2–44.5, production table | F (+O Gemini fallback) | 018 | SPEC-01 §4.3 | 02 | Every AR subtotal reproduced; A = E + L vs AR totals; cash ties | [P1.3](docs/delegation/packets/v3/P1.3_ar_full_statement_extraction.md) | ✅ |
| P1.4 | NSE XBRL parser | F | 018 | SPEC-01 §4.4 | — | XBRL vs AR agreement report; FY18/FY19 revenue & PAT exact | [P1.4](docs/delegation/packets/v3/P1.4_xbrl_parser.md) | ✅ |
| P1.5 | Yahoo loader + market provider chain (optional, retryable) | F | 019 | SPEC-01 §9.1 | — | FY26 consolidated = AR ±₹1 cr when Yahoo reachable; fallback chain works | [P1.5](docs/delegation/packets/v3/P1.5_yahoo_loader.md) | ✅ |
| P1.6 | Mapping, gates V01–V12, gold + snapshot, BigQuery load (`fact_financial_statement_line`, `dim_financial_line`; as-reported + restated vintages) | O (+F gates, FL evidence) | 018 | SPEC-01 §5–§6 | 03 | 0 plug lines; 100% reported lines `verified=TRUE`; gate report | [P1.6](docs/delegation/packets/v3/P1.6_fact_tables_bq_load_and_gates.md) | 🔍 |
| P1.7 | Anchor tables (segment, production, reserves, HR aggregates, realisation) | O→F | 018, 021, 022 | SPEC-01 §10 | — | Each row cites doc + page; totals = AR | [P1.7](docs/delegation/packets/v3/P1.7_anchor_tables.md) | ✅ |
| P1.8 | AR text chunks + embeddings + VECTOR_SEARCH retriever | F / O | 020 | SPEC-01 §8 | 16 (part) | 0 generated chunks; page refs verified; safe parameterised retriever (retrieval quality target moved to P2F.5, D-58) | [P1.8](docs/delegation/packets/v3/P1.8_ar_text_chunks_vector.md) | ✅ |
| P1.9 | WACC inputs + `fact_wacc_annual` (manual RBI seed CSV with lineage; Rf = raw INR 10-yr G-sec at FY-end) | F (+O load, human RBI seed) | 024, 029 | SPEC-02 §3 | 15 | Every input has source + date; re-run gives identical `wacc_pct` (±0.001pp); W1–W4 pass; SPEC-02 §10 fixture WACC 14.3090% | [P1.9](docs/delegation/packets/v3/P1.9_wacc_inputs.md) | ⬜ |
| P1.10a | Compiler on verified rows + honest provenance (`YUKTI_FIN_SSOT_V3`) | O | 018, 032 | SPEC-01 §7 | 02, 05 | "balance sheet for 2024" → total assets ₹4,46,021 cr with AR FY24 page cite | [P1.10a](docs/delegation/packets/v3/P1.10a_compiler_switch_verified_rows.md) | ⬜ |
| P1.10b | Retire LLM-authored artefacts (`build_10yr_financials.py`, generated corpus, governance CSV) | F | 018 | SPEC-01 §11 | 02, 03 | No code path reads retired files | [P1.10b](docs/delegation/packets/v3/P1.10b_retire_legacy_financials.md) | ⬜ |
| P1.11 | Finance golden set (P1 gate) + V20 chain (P2F gate) | F + FL | 030 | SPEC-11 §8, BEH-03 | 05 | 100% exact on the P1 build | [P1.11](docs/delegation/packets/v3/P1.11_finance_golden_set_and_v20_chain.md) | 🔄 |

### Phase P2H — HR: Personas, V19, Employee-360, Field Economics · *gate: 11-persona matrix 100%; recon 100%; BEH-02/06 pass*

| Step | Task | Owner | FEAT | Spec/BEH | Bugs | Acceptance | Packet | Status |
|---|---|---|---|---|---|---|---|---|
| P2H.1 | 11 personas + `dim_app_user` + function dimension + `self` scope + `@self_emp_id` + aggregate pay | O (tests F) | 017, 031 | SPEC-06, BEH-01 | 07, 27, 28 | 11 × 18 = 198 matrix cases pass; no cross-employee `self` leakage | [P2H.1](docs/delegation/packets/v3/P2H.1.md) | ✅ |
| P2H.2 | Persona picker, `/api/auth/me` banner, refusal UX copy EN/HI | O→F | 017 | SPEC-06 §4.4, §4.6 | 06 (UI) | Picker issues token; refusals suggest an allowed alternative | [P2H.2](docs/delegation/packets/v3/P2H.2.md) | 🔍 |
| P2H.3 | V19 turns 1–3: ordered levels, `DELHI_GT5_CONT_V1` definition, roster columns, cohort store | O→F | 023, 006 | SPEC-07 §4.1–4.3, BEH-02 | 34 | Exact counts per definition (executives default, all-cadres toggle) | [P2H.3](docs/delegation/packets/v3/P2H.3.md) | 🔍 |
| P2H.4 | V19 turns 4–5: export intent + columns + xlsx link; email agent (.eml/.docx/mailto); delete canned proposal | O→F | 023, 027 | SPEC-07 §4.4–4.5, SPEC-10, BEH-02 | 10, 11, 12 | BEH-02 steps 4–5 pass for 10 phrasings; email counts = roster | [P2H.4](docs/delegation/packets/v3/P2H.4.md) | ⬜ |
| P2H.5 | Employee-360 generator regeneration (realistic pyramid, names, pay + benefits + insurance + CTC, calibrated) | O | 021 | SPEC-04 §5–§7 | 26, 29, 30 | SPEC-04 §7.4 EMP-R01 (employee cost = AR) and EMP-R10 (FY-end headcount 23,117) pass; realism checks + calibrated marginals = AR/BRSR | [P2H.5](docs/delegation/packets/v3/P2H.5_employee360_generator.md) | 🔄 |
| P2H.6 | Employee-360 Dataform build, semantic model (pay components, KPIs, entry pay), certified queries | O→F (O: certified SQL; F: Dataform wiring) | 021, 008 | SPEC-04 §3, §4, §8, §9, BEH-06 | 26, 29 | Dataform green; BEH-06 values exact | [P2H.6](docs/delegation/packets/v3/P2H.6_employee360_dataform.md) | ⬜ |
| P2H.7 | Field Economics-360: production recalibration, RAS allocation engine, Dataform | O | 022 | SPEC-05 | — | Σ fields + CO-HQ = AR lines; segments = AR; production = AR by basis | [P2H.7](docs/delegation/packets/v3/P2H.7_field_economics_recon.md) | ⬜ |
| P2H.8 | Reconciliation gates: `recon_checks` (30 EMP-R + 17 FLD-R), assertions, offline tests, golden eval | O→F (O: recon rules/SQL + BLOCK assertion; F: tests) | 021, 022, 030 | SPEC-04 §7, SPEC-05 | — | 100% PASS; a deliberately broken input fails the build | [P2H.8](docs/delegation/packets/v3/P2H.8_reconciliation_tests.md) | ⬜ |

### Phase P2F — Finance Diagnostics (V20) · *gate: BEH-03 passes; actions quantified + cited*

| Step | Task | Owner | FEAT | Spec/BEH | Bugs | Acceptance | Packet | Status |
|---|---|---|---|---|---|---|---|---|
| P2F.1 | Year clarification (chips + voice) | O | 024 | SPEC-08 §3, BEH-03 | 14 | "give me income statement" → clarify card; choice kept in context | [P2F.1](docs/delegation/packets/v3/P2F.1_year_clarification.md) | ⬜ |
| P2F.2 | Multi-year statement payload (4–10 FY columns) | O | 024, 025 | SPEC-08 §4 | — | Every cell = SSOT ± ₹0.05 cr | [P2F.2](docs/delegation/packets/v3/P2F.2_multiyear_statement.md) | ⬜ |
| P2F.3 | WACC metric + chart + driver attribution | O (Shapley → F optional) | 024 | SPEC-02 §5 | 15 | Chart = `fact_wacc_annual` ± 0.01pp, 10 points | [P2F.3](docs/delegation/packets/v3/P2F.3_wacc_metric_chart.md) | ⬜ |
| P2F.4 | Variance-attribution engine (pure module + fixtures) | F | 024 | SPEC-08 §6.1 | 16 | Σ attribution = Δ; FY23→FY24 fixture | [P2F.4](docs/delegation/packets/v3/P2F.4_variance_attribution_engine.md) | ⬜ |
| P2F.5 | Grounded "why" + non-circular grounding | O | 024, 011 | SPEC-08 §6.2–6.3 | 16 | 0 uncited causal claims in BEH-03; held-out retrieval hit@5 ≥ 0.80 (±1 page) on ≥ 30 hand-checked Qs (D-58) | [P2F.5](docs/delegation/packets/v3/P2F.5_grounded_why.md) | ⬜ |
| P2F.6 | Top-5 actions + delegation table | O→F | 024 | SPEC-08 §7, BEH-03 | — | 5 actions, each with ₹ impact, owner, cite | [P2F.6](docs/delegation/packets/v3/P2F.6_top5_action_generator.md) | ⬜ |

### Phase P3 — Coordinator, Agents & DCF (V22) · *starts after P1 (D-39) · gate: BEH-05 by voice + text*

| Step | Task | Owner | FEAT | Spec/BEH | Bugs | Acceptance | Packet | Status |
|---|---|---|---|---|---|---|---|---|
| P3.1 | Contract v3 consolidation: add `proposed_action`, `job`, `provenance`, `dcf_model`; **owns the `contract_version` 3 bump**; consolidates fields added earlier via the SPEC-03 §5.1 ledger (`clarify` P2F.1; `artifacts[]`/`email_draft`/`ui_action.download` P2H.4; `statement` P4.2; `actions` P2F.6) and their fixtures **without re-adding them** | O | 007, 028 | SPEC-03 §5 | — | Schema validates all ledger fixtures; v1/v2 fixtures still validate; every ledger field present exactly once | [P3.1](docs/delegation/packets/v3/P3.1_contract_v3.md) | ⬜ |
| P3.2 | Jobs API + executor + job state store + SSE | O | 028 | SPEC-03 §7 | — | SPEC-03 AC-05 and AC-09 pass; progress events | [P3.2](docs/delegation/packets/v3/P3.2_jobs_api_executor.md) | ⬜ |
| P3.3 | Coordinator + router + agent registry | O | 028 | SPEC-03 §3–4 | — | 40/40 labelled router phrasings (SPEC-03 §11): Q&A / DCF / V19 / export | [P3.3](docs/delegation/packets/v3/P3.3_coordinator_registry.md) | ⬜ |
| P3.4 | DCF engine core | F (O reviews API first) | 029 | SPEC-02 §6–8 | — | Fixture exact to ₹0.01/share | [P3.4](docs/delegation/packets/v3/P3.4_dcf_engine_core.md) | ⬜ |
| P3.4b | dcf_agent wiring + result contract | O | 029 | SPEC-03 §7.3–7.4 | — | Job returns `dcf_model` + grid + tornado | [P3.4b](docs/delegation/packets/v3/P3.4b_dcf_agent_wiring.md) | ⬜ |
| P3.5 | DCF xlsx with live formulas + assumptions sheet | F (+FL parity) | 029, 027 | SPEC-02 §9.2 | — | Changing WACC in Excel recomputes the value | [P3.5](docs/delegation/packets/v3/P3.5_dcf_xlsx_live_formulas.md) | ⬜ |
| P3.6a | Permission UX frontend (Run / Edit assumptions / Cancel, progress, result) | F | 028 | SPEC-03 §6 | — | BEH-05 text path | [P3.6a](docs/delegation/packets/v3/P3.6a_permission_ux_frontend.md) | ⬜ |
| P3.6b | Voice confirm ("yes, run it") + completion announcement | O | 028 | SPEC-03 §6.2, §9 | — | BEH-05 voice path | [P3.6b](docs/delegation/packets/v3/P3.6b_voice_confirm_and_announce.md) | ⬜ |
| P3.7 | Wrap specialist agents (fin_diagnostics, hr_transfer, doc_export) | O→F | 028 | SPEC-03 §4 | — | 3 agents × 3 phrasings routed via the coordinator; contract validates; all 11 personas get SPEC-06-masked results | [P3.7](docs/delegation/packets/v3/P3.7_wrap_specialist_agents.md) | ⬜ |
| P3.8 | V22 golden chain + E2E evidence | F + FL | 030 | SPEC-11 §8.4, BEH-05 | — | Chain passes by voice + text | [P3.8](docs/delegation/packets/v3/P3.8_v22_golden_chain_e2e.md) | ⬜ |

### Phase P4 — Visual 9/10 & Exports (V21) · *can start after P0 · gate: finance rubric ≥ 9/10*

| Step | Task | Owner | FEAT | Spec/BEH | Bugs | Acceptance | Packet | Status |
|---|---|---|---|---|---|---|---|---|
| P4.1 | Signed bridge helper (py + ts), re-plot fix, no EBITDA fabrication, explicit-kind precedence, honest single-value message | O→F | 026 | SPEC-09 §4.3–4.4, BEH-04 | 08, 09, 22 | FY24 bridge ends at PAT ₹40,526 cr; probe phrasings pass | [P4.1](docs/delegation/packets/v3/P4.1.md) | ✅ |
| P4.2 | `visual.type=statement` contract + presenter emit (multi-FY) | O | 025 | SPEC-09 §4.1 | — | Fixture validates; values = SSOT | [P4.2](docs/delegation/packets/v3/P4.2.md) | ✅ |
| P4.3 | `StatementTable` renderer | F | 025 | SPEC-09 §4.2 | 38, 39 | Rubric ≥ 9/10 light + dark; line labels never truncated (wrap) at 1366/1920 px + big screen; no artificial numbering (AR names, hierarchy by indent) | [P4.3](docs/delegation/packets/v3/P4.3.md) | ✅ |
| P4.4 | Portfolio batch A: combo dual-axis, 100% stacked, heatmap, box, gauge, scatter fix; compat matrix | F | 026 | SPEC-09 §4.5–4.6 | 23 | Every kind renders from a fixture | [P4.4](docs/delegation/packets/v3/P4.4.md) | ✅ |
| P4.5 | Portfolio batch B: sensitivity grid, tornado, bubble, sunburst, sankey, India choropleth, `dcf_model`/`actions` composites | F | 026 | SPEC-09 §4.5, §5 | — | Every kind renders from a fixture | [P4.5](docs/delegation/packets/v3/P4.5.md) | 🔄 |
| P4.6 | Export backend: formatted xlsx, CSV, PDF (WeasyPrint + Noto), docx, honest Sheets/Docs, audit, naming | O→F | 027 | SPEC-10 | 24, 25 | pdftotext shows ₹ + Devanagari; 4+ formats per card | [P4.6](docs/delegation/packets/v3/P4.6.md) | ✅ |
| P4.7 | Export frontend: menu, PNG/SVG, intents for all formats EN/HI, toasts | F | 027 | SPEC-10 §4.4, §4.7–4.8 | 25 | BEH-04 export scenarios | [P4.7](docs/delegation/packets/v3/P4.7.md) | ✅ |
| P4.8 | Finance rubric F1–F14 + scorecards | F→O | 025, 026 | SPEC-09 §4.7 | 34 | Scorecards ≥ 9/10 | [P4.8](docs/delegation/packets/v3/P4.8.md) | ⬜ |
| P4.9 | Orb visible in docked mode + optional edge aura (low priority, V21) | F | 004, 016 | SPEC-09 §4.9 | — | Visible in non-idle states; ≥ 55 fps | [P4.9](docs/delegation/packets/v3/P4.9.md) | ✅ |

### Phase P5 — One Brain, Eval & Redeploy · *gate: golden ≥ 95% exact; Cloud Run green* · packets written at P5 start

| Step | Task | Owner | FEAT | Spec/BEH | Bugs | Acceptance | Status |
|---|---|---|---|---|---|---|---|
| P5.1 | Remove fast-paths/hard-coded answers (disposition list in SPEC-11); legacy ADK path behind the coordinator only | O | 030, 009 | SPEC-11 | 05, 12, 21 | 0 hard-coded numbers in `turn_runner.py`; golden set unchanged or better | ⬜ |
| P5.2 | Voice: speak `spoken_summary` verbatim (EN/HI), `speak_id` dedupe, barge-in fix | O | 030, 013 | SPEC-11, BEH-07 | 17, 18, 19 | BEH-07.30–.35 (feedback regressions) pass | ⬜ |
| P5.3 | Coverage manifest ("what data do you have") deterministic | O | 030 | SPEC-11 | 05 | feedback4 turns answer correctly | ⬜ |
| P5.4 | Numeric golden eval (~60 Q + V19/V20/V22 chains + voice smoke); replace `run_30x4_stress_test.py` criteria | O→F | 030, 014 | SPEC-11 | — | ≥ 95% exact | ⬜ |
| P5.5 | Full gate run + review | FL→O | 014 | — | — | Scorecard vs BUILD §6 targets | ⬜ |
| P5.6 | Cloud Run redeploy from the green tree (sponsor go-ahead) | O + S | 014 | — | 13 | Revision serves BEH-02/03/05 live | ⬜ |

---

## Part C — Open decisions raised while writing specs (need sponsor input; logged as OD-7…OD-18 in `docs/DECISIONS.md`; renumbered from OD-6…OD-16 because OD-6 was already resolved by D-16)

See `docs/DECISIONS.md` → Open decisions.

## Part E — Sponsor action items

| ID | Action | Needed by | Status |
|---|---|---|---|
| SA-1 | Re-authenticate ADC (`gcloud auth application-default login`) — expires daily | P0.1, P1.6+ | ⬜ **Expired again 24-Oct** (needed for BigQuery steps + live app) |
| SA-2 | Approve v3 doc set + OD-7…OD-18 | P0.8 | ✅ Done 23-Oct (D-43…D-54) |
| SA-3 | Download RBI Handbook Table 178 (month-end G-sec yields) XLSX → `knowledge/public_sources/market_data/rbi/` | P1.9 | ⬜ Pending |
| SA-4 | Download Damodaran Jan-2025 `ctryprem` → `knowledge/public_sources/market_data/damodaran/` | P1.9 | ⬜ Pending |
| SA-5 | Review the 10 finance action levers + assumption % (SPEC-08 §7, D-50) | P2F.6 | ⬜ Pending |
| SA-6 | G5 sign-off at the end of each phase (P0 … P5) | each phase | ✅ P0 signed off 23-Oct 09:52 · ⬜ P1 next |
| SA-7 | Go-ahead for the Cloud Run redeploy (**note:** deploy with `max-instances=1` until exports move to a GCS store; P4.6 G4 r2: the turn registry and export files are per-instance and fail closed with 403 across instances) | P5.6 | ⬜ Pending |

## Part D — Sign-off log

| Phase | G5 date | Sponsor | Notes |
|---|---|---|---|
| **P0 Stabilise (incl. hotfix P0.10)** | 2026-10-23 09:52 UTC | Amandeep Saini ("I am signing off") | Live-tested by sponsor: voice no longer self-interrupts; residuals logged (BUG-38/39 → P4.3, BUG-40 → P5.2). P0.10 G4 approved (r2, voice barge-in off → BUG-41); merged to `main` + tagged `v3-P0` |
| v3 docs (P0.8) | 2026-10-23 | Amandeep Saini ("I approve") | G4 approved (2 rounds); OD-7…OD-18 accepted as D-43…D-54 |
