# Yukti AI: Step-by-Step Upgrade Checklist (`UPGRADE_CHECKLIST.md`)

**Process:** every step goes through the five gates in [`BUILD.md`](BUILD.md) §4. **Features:** [`feature_list.md`](feature_list_and_verbatims/feature_list/feature_list.md) · **Decisions:** [`docs/DECISIONS.md`](docs/DECISIONS.md) · **Reviews:** `docs/reviews/<step-id>.md`
**Baseline:** `baseline-v0.2` (`fbe3594`) · **Order:** U0 → U1 → **U4 → U3 → U2 → U5** (visual-first, D-17) → B1 → B2 → B3 → B4 → H1

**Owner legend:** `O` Opus lead · `F` Flash · `FL` Flash-lite · `O→F` Opus skeleton, Flash completes · `F→O` Flash drafts, Opus finalises · `FL→O` Flash-lite runs, Opus interprets · `O→F + FL` Opus specifies, Flash builds, Flash-lite runs · `O + S` Opus executes with sponsor go-ahead · `S` Sponsor. Rules in [`DELEGATION.md`](DELEGATION.md); **every step gets a G4 review by a fresh Opus reviewer (R-O); F/FL steps also get the delegation consistency checks**.
**Gate legend per step:** `G1` spec confirmed · `G3` verified (evidence) · `G4` independent review approved (link) · `G5` sponsor sign-off (phase end). **Packet** files are written by Opus at G1, before delegation; links show `n/a` for Opus-owned steps.
**Status legend:** ⬜ not started · 🟦 in progress · 🟨 in review · ✅ done · ⛔ blocked (decision)

---

## Phase U0: Governance & Baseline · *gate: docs confirmed (U1 may start after U0.2 + OD-1; U0.4/U0.5 run in parallel)*

| Step | Owner | Task | Acceptance criteria | Verification | Status | Packet | G3 | G4 | G5 |
|---|---|---|---|---|---|---|---|---|---|
| **U0.1** | `O` | Commit and tag the baseline | `baseline-v0.2` tag exists; tree clean | `git log`, `git tag` | ✅ | n/a | ✅ | waived (V14) | ✅ (V14) |
| **U0.2** | `O` | `BUILD.md`, feature list v2, this checklist, decision log, review template, `DELEGATION.md` | Docs exist, cross-linked, and every feature maps to ≥ 1 step | Doc review by reviewer agent | ✅ | n/a | ✅ | ✅ [review](docs/reviews/U0.2.md) | ✅ (V15) |
| **U0.3** | `S` | Resolve open decisions OD-1 … OD-5 | Each recorded as D-x in `DECISIONS.md` | Sponsor answers | ✅ (OD-5 deferred to B3) | n/a | ✅ | n/a (sponsor decision) | ✅ (V15) |
| **U0.4** | `O→F + FL` | Re-run the cache-OFF eval on `baseline-v0.2`; build the fast **gate subset** (~120 turns) | Scorecard at `yukti/backend/eval/gates/U0.md`; subset script runs in < 15 min | Eval run log | ⬜ | [packet](docs/delegation/packets/U0.4.md) | | | |
| **U0.5** | `FL` | Visual baseline: Playwright screenshots of the current UI (light/dark, key states) | `docs/reviews/assets/U0_*.png` | Screenshot script | ✅ | [packet](docs/delegation/packets/U0.5.md) | ✅ |✅ [evidence](docs/reviews/U0.5.md) (O spot-check) | |

---

## Phase U1: Design System Foundation (FEAT-005, FEAT-015 chart theme) · *gate: visual review sign-off (incl. D-13 palette confirmation)*

| Step | Owner | Task | Acceptance criteria | Verification | Status | Packet | G3 | G4 | G5 |
|---|---|---|---|---|---|---|---|---|---|
| **U1.1** | `O→F` | Design tokens (colour per OD-1, surfaces, borders, radii, shadows, motion durations) as CSS variables + Tailwind theme | One token source; no hard-coded hex in components (lint/grep check) | `grep` check + build | ✅ | [packet](docs/delegation/packets/U1.1.md) | ✅ |✅ [review](docs/reviews/U1.1.md) | |
| **U1.2** | `F` | Typography scale and tabular numerals for KPIs; number formatting (₹ Cr / Lakh, %) centralised | KPI numerals use `font-variant-numeric: tabular-nums`; all ₹/%/count formatting goes through one util (grep: 0 ad-hoc `toLocaleString` in components) | Screenshot diff | ✅ | [packet](docs/delegation/packets/U1.2.md) | ✅ |✅ [review](docs/reviews/U1.2_U1.4.md) | |
| **U1.3** | `O→F` | Surface primitives: `Card`, `CardHeader`, `Chip`, `Badge`, `Toolbar` (frosted glass, hairline borders, ambient shadow) | Primitives (`Card`, `CardHeader`, `Chip`, `Badge`, `ContextChips`, `Toolbar`, `IconButton`) exported from `src/components/ui/primitives.tsx`; rendered on the `/design-system` showcase page in light + dark; tokens only (lint OK). Adoption: new components from U2 on (TurnCard U2.3); legacy Canvas/Panel/TopBar migrated in U4 (D-15) | `/design-system` showcase page (screenshots light + dark) | ✅ | [packet](docs/delegation/packets/U1.3.md) | ✅ |✅ [review](docs/reviews/U1.3_U1.5.md) | |
| **U1.4** | `F` | Light theme as default; dark theme parity | No contrast failures on primary text (≥ 4.5:1) | Automated contrast check | ✅ | [packet](docs/delegation/packets/U1.4.md) | ✅ |✅ [review](docs/reviews/U1.2_U1.4.md) | |
| **U1.5** | `O` (Flash part not needed; reference charts built in U1.3 page) | **Chart design system** (FEAT-015): ECharts theme from tokens (categorical/sequential/diverging palettes), typography, grid/axis/label/tooltip standards, animation timings, Indian number formats, light/dark parity; chart quality rubric doc | One `yukti` ECharts theme used by every chart; rubric at `docs/chart_quality_rubric.md`; 6 reference charts (bar, hbar, donut, line, histogram, treemap) on `/design-system` score ≥ 4/5 on the rubric | Screenshot review vs rubric (light + dark) | ✅ | n/a | ✅ |✅ [review](docs/reviews/U1.3_U1.5.md) | |
| **U1.6** | `O` | **AI Aura** (FEAT-016, Verbatim 16): aura tokens (ring + bloom tints of Google hues), `.yk-aura-ring` (rotating arc + outside-only feathered halo, idle/listening/thinking speeds, reduced-motion safe) and `.yk-aura-bloom`; prototype on `/design-system` | Sponsor confirms the feel against the AI Mode reference; tokens-only (lint OK) | Screenshots light/dark vs reference photo | ✅ | n/a | ✅ | ✅ sponsor-reviewed prototype (3 iterations) | ✅ ("yes", 06:57) |

---

## Phase U2: Conversation Feed + Contract v2 (FEAT-001, FEAT-007) · *gate: Verbatim 11 criteria in a browser test*

| Step | Owner | Task | Acceptance criteria | Verification | Status | Packet | G3 | G4 | G5 |
|---|---|---|---|---|---|---|---|---|---|
| **U2.1** | `O` | Contract v2 optional fields in schema + TS types (`insights_v2`, `drilldowns`, `context_chips`, `query_spec`, `visual.compare`, `table.masking`, `row_actions`) | `contract_version: 2` field; `query_spec`/`spec_patch` JSON shape frozen and versioned; existing fixtures + 28 tests still pass; new v2 fixtures validate | `pytest`, `tsc`, fixture check | ✅ | n/a | ✅ | ✅ [review](docs/reviews/U2.md) | |
| **U2.1b** | `F` | Contract-v2 fixtures: roster (419 + 2,000 rows), compare (Delhi vs Mumbai), insights + drill-downs, masked/aggregate states, finance P&L | All validate against schema v2; rendered in U2–U5 tests | Fixture check script | ✅ | [packet](docs/delegation/packets/U2.1b.md) | ✅ | ✅ [review](docs/reviews/U2.md) | |
| **U2.2** | `O` | Feed state model: `turns[]` (question, contract, status, timestamps); replaces single `contract` + history strip | Asking B after A keeps A; state survives voice + text turns | Unit test on reducer | ✅ | n/a | ✅ | ✅ [review](docs/reviews/U2.md) | |
| **U2.3** | `O` | `TurnCard` component: question → brief answer → visual → insights → drill-down chips → actions (export) | Each historic card stays interactive (tooltips, toggles); **export to Sheets, Docs, Word and PDF works from the current and historic cards**; feed gated by `NEXT_PUBLIC_FEED_V2` | Playwright: hover + export on card N-1 | ✅ | n/a | ✅ | ✅ [review](docs/reviews/U2.md) | |
| **U2.4** | `F` | Scroll behaviour: auto-scroll to the latest card; pause when the user scrolls up; "jump to latest" pill | Auto-scroll disabled after the user scrolls up > 100 px; "jump to latest" pill appears; clicking it returns to the bottom and re-enables auto-scroll | Playwright scroll test | ✅ | [packet](docs/delegation/packets/U2.4.md) — done by O | ✅ | ✅ [review](docs/reviews/U2.md) | |
| **U2.5** | `O` | Refine vs new-turn semantics: re-plot/"show as table" updates the **current** card in place; a new question appends | Chart switch doesn't add a card; a new question does | Playwright | ✅ | n/a | ✅ | ✅ [review](docs/reviews/U2.md) | |
| **U2.6** | `O→F` | "New session" clears the feed and backend context (new `session_id`) | Follow-up after reset doesn't inherit the old context | API + UI test | ✅ | [packet](docs/delegation/packets/U2.6.md) — done by O | ✅ | ✅ [review](docs/reviews/U2.md) | |
| **U2.7** | `F` | Floating panel and feed layout reconciled (docked / fullscreen / minimised) | All 3 modes: no overlap between the panel and the active card, text ≥ 14 px, all controls reachable, at 1440p and 4K | Screenshots at 1440p and 4K | ✅ | [packet](docs/delegation/packets/U2.7.md) — done by O | ✅ | ✅ [review](docs/reviews/U2.md) | |

---

## Phase U3: Infinity-Ribbon Voice Orb + Voice Quality (FEAT-004, FEAT-013) · *gate: 4 states distinct, ≥ 55 fps (target 60), voice tests* · *palette per D-13*

| Step | Owner | Task | Acceptance criteria | Verification | Status | Packet | G3 | G4 | G5 |
|---|---|---|---|---|---|---|---|---|---|
| **U3.1** | `O` | Canvas-2D ribbon renderer: 3–4 harmonic Bézier/sine ribbons on an ∞ path, gradient strokes, `lighter` blending, soft bloom | No dots/particles; DPR-aware; reduced-motion fallback; **`VoiceOrb.tsx` TEMP_ALLOW entry removed from `scripts/check_tokens.mjs` and `lint:tokens` OK** | Visual review + rAF profile | ✅ | n/a | ✅ | ✅ [review](docs/reviews/U3.md) | |
| **U3.2** | `O` | State dynamics: idle (0.4–0.6 Hz breathe), listening (mic RMS → amplitude/thickness), thinking (orbiting pulse), speaking (playback analyser → resonance) | Each state has distinct parameters (frequency, amplitude, colour intensity per the spec table) verified in a 4-panel capture; the sponsor identifies all 4 states blind | Screen recording | ✅ (sponsor blind-ID open) | n/a | ✅ | ✅ [review](docs/reviews/U3.md) | |
| **U3.3** | `O` | Single level source: raw worklet RMS for listening, output analyser for speaking; `getMicLevel` becomes a pure read | No synthetic floor; level reaches ~0 in silence | Unit + manual | ✅ | n/a | ✅ | ✅ [review](docs/reviews/U3.md) | |
| **U3.4** | `O` | Barge-in fix: local stop drops incoming chunks + sends `interrupt`; threshold on raw RMS | On speakers Yukti isn't cut off by her own echo; a real interruption stops the audio within ≤ 300 ms | `voice_e2e_test.js` + manual | ✅ (sponsor speaker test open) | n/a | ✅ | ✅ [review](docs/reviews/U3.md) | |
| **U3.5** | `O` | Mic lifecycle: in-flight start guard, stop-during-start handling, final-frame flush, close `playCtx` on unmount | Double-click opens 1 stream; mic indicator turns off on stop | Playwright fake-media test | ✅ | n/a | ✅ | ✅ [review](docs/reviews/U3.md) | |
| **U3.6** | `O` | SpeechRecognition fallback only when Live is down; cancelled-recognizer flag; no relaunch on fatal errors; stale `onclose` guard | No duplicate REST + Live turns in a 20-turn scripted session | Scripted test log | ✅ | n/a | ✅ | ✅ [review](docs/reviews/U3.md) | |
| **U3.7** | `FL` | Performance budget | ≥ 55 fps (target 60) on the **demo laptop at 4K / big screen** (V8 §7); idle CPU < 10% | Chrome perf trace | ✅ headless 60 fps 1440p/4K; demo-laptop check open | [packet](docs/delegation/packets/U3.7.md) — done by O, not FL | ✅ | ✅ [review](docs/reviews/U3.md) | |

---

## Phase U4: Executive Polish (FEAT-005, FEAT-016) · *gate: before/after main-app screenshots, sponsor sign-off (light + dark)* · spec: [`docs/design/U4_spec.md`](docs/design/U4_spec.md)

| Step | Owner | Task | Acceptance criteria | Verification | Status | Packet | G3 | G4 | G5 |
|---|---|---|---|---|---|---|---|---|---|
| **U4.1** | `O` (executed by Opus per U4 spec) | TopBar: persona, language, theme, session, connection state; quiet and compact | Single row of `3.5rem` on the fluid scale (D-22); ≤ 7 controls; every action one click | Screenshot review | ✅ | [packet](docs/delegation/packets/U4.1.md) | ✅ |✅ [review](docs/reviews/U4.md) | |
| **U4.2** | `O` (moved from F: same file as Opus-owned U4.6/U4.7, to avoid concurrent edits) | Context chips on every card (`CMD · Delhi HQ · Executives · FY26 · Source`) from `context_chips` / derived | Present on all data cards | Playwright | ✅ | [packet](docs/delegation/packets/U4.2.md) | ✅ |✅ [review](docs/reviews/U4.md) | |
| **U4.3** | `F` | KPI cards with delta pills; table polish (sticky header, zebra, inline bars, number alignment) | Sticky header, zebra rows, right-aligned tabular numbers, inline bars for numeric columns, KPI delta pill (▲/▼ + colour per tokens) | Screenshot diff vs U0 | ✅ | [packet](docs/delegation/packets/U4.3.md) | ✅ |✅ [review](docs/reviews/U4.md) | |
| **U4.4** | `F` | Contextual voice pill: chat collapses to a glowing pill when a full-screen visual is shown; expands on hover/voice | Pill collapses within 300 ms when a visual is full-screen; expands on hover or voice activity; never covers the active chart's data area | Playwright | ✅ | [packet](docs/delegation/packets/U4.4.md) | ✅ |✅ [review](docs/reviews/U4.md) | |
| **U4.5** | `O` (executed by Opus per U4 spec) | Greeting/home screen refresh: calm, brand-correct, suggested prompts by persona | 4 persona-specific suggested prompts (CMD/DIR_HR/DIR_FIN/E-level) incl. ≥ 1 finance prompt; greeting text from V10; tokens only (0 hard-coded hex) | Screenshot review | ✅ | [packet](docs/delegation/packets/U4.5.md) | ✅ |✅ [review](docs/reviews/U4.md) | |
| **U4.6** | `O` | **Ask bar** rebuilt on primitives with the AI aura ring bound to orb state (idle/listening/thinking); suggestion chips above, never truncated | Aura state follows `orbState`; chips fully visible at 1440p/4K; typing + mic + send unchanged functionally | Playwright + screenshots | ✅ | n/a | ✅ |✅ [review](docs/reviews/U4.md) | |
| **U4.7** | `O` | **Newest-answer aura edge** (fades ~4 s) | Appears only on the newest card; respects reduced motion | Screen capture | ✅ | n/a | ✅ |✅ [review](docs/reviews/U4.md) | |
| **U4.8** | `F` | **Legacy migration** of CanvasView / FloatingConversationPanel / TopBar to U1 primitives (D-15) | No ad-hoc card/chip/button styles left in these files; `lint:tokens` OK; smoke test passes | grep + Playwright | ⏭ deferred to U2 (D-23) | [packet](docs/delegation/packets/U4.8.md) | | | |

---

## Phase U5: Visual System, Any-Chart Re-plot, Roster & Comparison Components (FEAT-003, FEAT-015, FEAT-006 UI, FEAT-010 UI, FEAT-011 UI) · *gate: every question-bank visual type renders from fixtures* · *policy per D-10/D-11*

| Step | Owner | Task | Acceptance criteria | Verification | Status | Packet | G3 | G4 | G5 |
|---|---|---|---|---|---|---|---|---|---|
| **U5.1** | `F→O` | Visual audit: map every question-bank item (107) → best visual type; record gaps | `docs/visual_audit.md` with a mapping table and gap list | Doc review | ✅ | [packet](docs/delegation/packets/U5.1.md) | ✅ | ✅ [review](docs/reviews/U5.md) | |
| **U5.2** | `O→F` | **Roster table component:** sort, filter (grade/discipline), search, row multi-select, action bar (`Draft Transfer Note (N)`, `Export`), masked-column state (🔒 + policy ref) | Works on the **419-row Delhi 5+ yrs roster fixture** and a 2,000-row stress fixture; virtualised scroll ≥ 55 fps; sort/filter/search/select/export each verified | Playwright | ✅ | [packet](docs/delegation/packets/U5.2.md) | ✅ | ✅ [review](docs/reviews/U5.md) | |
| **U5.3** | `F` | **Comparison view:** side-by-side KPIs + grouped bar for `visual.compare` (e.g. Delhi vs Mumbai) | Renders a compare fixture; labels are entity-correct | Playwright | ✅ | [packet](docs/delegation/packets/U5.3_U5.5.md) | ✅ | ✅ [review](docs/reviews/U5.md) | |
| **U5.4** | `O→F` | Insight list + drill-down chips rendering (`insights_v2`, `drilldowns`); chips send follow-up turns | Click on a chip → a new turn with `spec_patch` | Playwright + mock backend | ✅ | [packet](docs/delegation/packets/U5.4.md) — done by O | ✅ | ✅ [review](docs/reviews/U5.md) | |
| **U5.5** | `O→F` | Normalise table rows (array → object) everywhere (charts, switcher, export) | Array-row fixture charts and exports correctly | Unit + Playwright | ✅ | [packet](docs/delegation/packets/U5.3_U5.5.md) | ✅ | ✅ [review](docs/reviews/U5.md) | |
| **U5.6** | `F` | Fill the visual gaps from U5.1 (e.g. KPI + delta, distribution, map polish) | All 107 mapped items render a fitting visual from fixtures | Fixture sweep script | ⬜ | [packet](docs/delegation/packets/U5.6.md) | | | |
| **U5.7** | `O` | **Chart compatibility matrix + transform engine** (FEAT-015): data shape → valid chart types + transforms (bins→slices, aggregate, top-N + Other, measure selection) + nearest-alternative fallback with explanation | `docs/chart_compatibility.md`; one function used by voice, text and toolbar; unit tests for every shape × type | Unit tests | ✅ | n/a | ✅ | ✅ [review](docs/reviews/U5.md) | |
| **U5.8** | `O→F` | **Re-plot by voice/text/toolbar** for the full supported set; morph animation; no backend call for re-plots | Histogram → pie in ≤ 300 ms, slices = bins; voice "show as treemap/line/table…" and toolbar give identical output; incompatible request → alternative + 1-line note | Playwright sweep (every shape fixture × every type) | ✅ | [packet](docs/delegation/packets/U5.8.md) — done by O | ✅ | ✅ [review](docs/reviews/U5.md) | |
| **U5.9** | `O` + `S` | **Chart excellence review:** every chart type scored against the rubric (light + dark), fixes applied | Every type ≥ 4/5 on each rubric criterion; sponsor confirms visually | Rubric scorecard `docs/reviews/U5.9.md` + screenshots | ⬜ | n/a | | | |

---

## Phase B1: Semantic Layer Truth (FEAT-008) · *gate: zero catalog/data mismatches*

| Step | Owner | Task | Acceptance criteria | Verification | Status | Packet | G3 | G4 | G5 |
|---|---|---|---|---|---|---|---|---|---|
| **B1.1** | `O→F` | Catalog generator from INFORMATION_SCHEMA + profiled values → `semantic_catalog.json` | Covers: `hrfin_gold.ssot_workforce_employee`, `ssot_work_centre_360`, `ssot_field_economics_360`, `ssot_corporate_annual_360`, all `hrfin_gold.mart_*`/`agg_*`, and the `hrfin_silver` tables referenced in `semantic_layer.py` + `certified/library.yaml` (list frozen in the B1.1 packet) | Script run + diff | ⬜ | [packet](docs/delegation/packets/B1.1.md) | | | |
| **B1.2** | `O` | Single entity dictionary (WC/field/discipline codes ↔ names ↔ aliases incl. Hindi/Hinglish); remove duplicates in `session_memory`/`router`/`turn_runner`/`query_data` | One import site; old maps deleted | grep + tests | ⬜ | n/a | | | |
| **B1.3** | `O→F` | Case-insensitive categorical filter normalisation; FY resolution ("last year" = FY25) | Unit tests on rewrites + FY resolver | `pytest` | ⬜ | [packet](docs/delegation/packets/B1.3.md) | | | |
| **B1.4** | `F` | Catalog consistency CI test (codes/values used in code and templates exist in data) | Test fails on an injected bad code | `pytest` | ⬜ | [packet](docs/delegation/packets/B1.4.md) | | | |
| **B1.5** | `FL→O` | Gate-subset eval for B1 | Scorecard `yukti/backend/eval/gates/B1.md`; no regression vs the previous gate | Eval run log | ⬜ | [packet](docs/delegation/packets/B1.5.md) | | | |

## Phase B2: QuerySpec Planner & Compiler (FEAT-009, FEAT-002) · *gate: eval root ≥ 80%, follow-ups ≥ 60%*

| Step | Owner | Task | Acceptance criteria | Verification | Status | Packet | G3 | G4 | G5 |
|---|---|---|---|---|---|---|---|---|---|
| **B2.1** | `O` | `QuerySpec` model + patch semantics | Unit tests for patch ops (filter add, compare, grain switch, time shift) | `pytest` | ⬜ | n/a | | | |
| **B2.2** | `O` | Planner (Gemini structured output) using catalog summary + previous spec | ≥ 30 golden specs (HR + finance flagship chains, paraphrases, Hinglish) correct | Golden tests | ⬜ | n/a | | | |
| **B2.2b** | `F` | Golden-test cases (≥ 30) written from O-specified chains (HR + finance flagship, paraphrases, Hinglish) | Each case: question, prior spec, expected spec; O approves the expected specs | `pytest` collection | ⬜ | [packet](docs/delegation/packets/B2.2b.md) | | | |
| **B2.3** | `O` | Compiler: certified-template match → generated SQL → dry-run → async execute | 100% of compiled SQL passes dry-run on the golden set | `pytest` + BigQuery dry-run | ⬜ | n/a | | | |
| **B2.4** | `O` | Wire behind `YUKTI_PLANNER=1`; shrink fast-paths to greeting + screen control | Flag off = baseline behaviour; flag on = planner | Both modes tested | ⬜ | n/a | | | |
| **B2.5** | `O` | Session stores spec history; follow-ups resolve as patches; `query_spec` echoed in the contract | Flagship 7-turn chain passes end to end | Scripted API test | ⬜ | n/a | | | |
| **B2.6** | `FL→O` | Gate eval (subset) | Root ≥ 80%, follow-ups ≥ 60%, no RBAC regressions | `yukti/backend/eval/gates/B2.md` | ⬜ | [packet](docs/delegation/packets/B2.6.md) | | | |

## Phase B3: Granular Data + RBAC Policy (FEAT-006 data, FEAT-010) · *gate: roster correct vs BigQuery; RBAC matrix 100%* · *needs OD-2, OD-3*

| Step | Owner | Task | Acceptance criteria | Verification | Status | Packet | G3 | G4 | G5 |
|---|---|---|---|---|---|---|---|---|---|
| **B3.1** | `O→F` | Roster grain in compiler (name, emp_id, designation, grade, discipline, ONGC tenure, station tenure, exemption, retiring ≤ 3 yrs) | Delhi 5+ yrs roster matches a direct BigQuery count and sample | bq spot check | ⬜ | [packet](docs/delegation/packets/B3.1.md) | | | |
| **B3.2** | `FL→O` | Resolve the designation field (`grade_designation` vs `current_designation`) | Field populated for ≥ 99% of rows | bq check | ⬜ | [packet](docs/delegation/packets/B3.2.md) | | | |
| **B3.3** | `O` | `rbac_policy.yaml` (persona class × data class → allow/mask/aggregate/refuse) applied pre- and post-query | RBAC matrix test 100% | `pytest` | ⬜ | n/a | | | |
| **B3.4** | `O` | Consistency rule: `access.status`, text and visual agree; small-cell suppression (< 5) for aggregates | E2_HR names query → aggregate/refusal, status consistent | Scripted test | ⬜ | n/a | | | |
| **B3.5** | `O→F` | Row action: "Draft Transfer Note" from selected roster rows → document with those employees | Document lists the selected people correctly; exports | API + UI test | ⬜ | [packet](docs/delegation/packets/B3.5.md) | | | |
| **B3.6** | `FL→O` | Gate-subset eval for B3 | Scorecard `yukti/backend/eval/gates/B3.md`; no regression vs the previous gate | Eval run log | ⬜ | [packet](docs/delegation/packets/B3.6.md) | | | |

## Phase B4: Insight Engine (FEAT-011) · *gate: ≥ 2 grounded insights/answer; 0 invented numbers*

| Step | Owner | Task | Acceptance criteria | Verification | Status | Packet | G3 | G4 | G5 |
|---|---|---|---|---|---|---|---|---|---|
| **B4.1** | `O→F` | Insight library (share, rank, delta vs last year, vs sanctioned/target, outliers, concentration, named exceptions, policy flags) | Unit tests per insight type | `pytest` | ⬜ | [packet](docs/delegation/packets/B4.1.md) | | | |
| **B4.2** | `O` | Drill-down chip generator (names / by grade / compare / trend / draft) as spec patches | Chips executable; ≥ 2 per data answer | Scripted test | ⬜ | n/a | | | |
| **B4.3** | `O` | Narrator limited to computed facts + numeric-grounding check | 0 ungrounded numbers on the gate subset; spoken answers 2–4 sentences (V8 §4) | Automated check | ⬜ | n/a | | | |
| **B4.4** | `F` | Board note / transfer note drafting uses correct SSOT columns (fixes the zero values) | No zero placeholders where data exists | Document check | ⬜ | [packet](docs/delegation/packets/B4.4.md) | | | |
| **B4.5** | `O→F` | **Finance flagship chain** (V4): loss-making / most profitable fields FY26 → by capex invested → under-invested vs reserves → vs MoU target → draft board note | Golden test passes end to end; ≥ 2 grounded insights per answer; Director (Finance) persona verified | Scripted API test + Playwright | ⬜ | [packet](docs/delegation/packets/B4.5.md) | | | |
| **B4.6** | `FL→O` | Gate-subset eval for B4 | Scorecard `yukti/backend/eval/gates/B4.md`; no regression vs the previous gate | Eval run log | ⬜ | [packet](docs/delegation/packets/B4.6.md) | | | |

## Phase H1: Harden, Full Eval & Deploy (FEAT-012, FEAT-014) · *gate: eval targets met; Cloud Run verified*

| Step | Owner | Task | Acceptance criteria | Verification | Status | Packet | G3 | G4 | G5 |
|---|---|---|---|---|---|---|---|---|---|
| **H1.1** | `O` | Async BigQuery/embeddings; voice tool calls off the receive loop | No event-loop blocking > 100 ms under 3 concurrent sessions | Load script | ⬜ | n/a | | | |
| **H1.2** | `O` | SQL safety (re-validate repaired SQL, parameterised fallbacks, hardened allow-list) | Injection/bypass tests pass | `pytest` | ⬜ | n/a | | | |
| **H1.3a** | `O` | Security hardening: export filename sanitisation (path traversal), `server.js` HTTPS backend + upstream abort | Traversal tests blocked; https backend proxy works; aborted request cancels upstream | `pytest` / node test | ⬜ | n/a | | | |
| **H1.3b** | `F` | Memory bounds (sessions, ADK events, visual history), cache immutability, contract-validation error handling | Regression test per item; memory flat over a 200-turn soak | `pytest` + soak script | ⬜ | [packet](docs/delegation/packets/H1.3b.md) | | | |
| **H1.4** | `FL` | Full 773-turn eval | Targets in `BUILD.md` §6 | `yukti/backend/eval/gates/H1.md` | ⬜ | [packet](docs/delegation/packets/H1.4.md) | | | |
| **H1.5a** | `F` | Update `Dockerfile` / `.dockerignore` / `start_cloudrun.sh` for the new build | `docker build` succeeds locally or via Cloud Build; image runs `/health` 200 | Build log | ⬜ | [packet](docs/delegation/packets/H1.5a.md) | | | |
| **H1.5b** | `O + S` | **Redeploy Cloud Run** (only after sponsor go-ahead) + smoke test | `/health` 200 via proxy; flagship HR + finance chains work on the Cloud Run URL; previous revision noted for rollback | Smoke test | ⬜ | n/a | | | |
| **H1.6** | `F` | Final docs: README, APP_LINK, change log, demo script | README/APP_LINK/demo script reviewed against a live run of the flagship HR + finance chains; every documented command executed successfully | Reviewer agent | ⬜ | [packet](docs/delegation/packets/H1.6.md) | | | |

---

## Appendix A: 2026-10-22 bug audit → step mapping

| Audit item | Step |
|---|---|
| 2.1–2.5 fast-path hijacks, anaphora, WC codes, FY mapping, ui_control rewrites | B1.2, B1.3, B2.4 |
| 2.6 answer-cache poisoning · 2.7 Hinglish fallback · 2.9 C1 columns · 2.10 refusal alternative SQL | B2.3, B2.4, B3.3 |
| 2.8 draft column names (zeros) | B4.4 |
| 2.11–2.16 async, safety-net, SQL safety, validation, hardcoded project, memory | H1.1, H1.2, H1.3b |
| 2.17–2.20 barge-in, level meter, mic leak, SpeechRecognition duplicates | U3.3–U3.6 |
| 2.21 array rows | U5.5 |
| 2.22 server.js HTTPS | H1.3a |
| P3 items | U3.6 (voice), U4/U5 (UI), H1.3a/H1.3b (backend) |
| Verbatim 4 finance questions (profit/loss, investment, under-investment) | B4.5, FEAT-009/011 ACs |

## Appendix B: Sign-off log

| Phase | Date | Sponsor confirmation | Review links | Scorecard | Tag |
|---|---|---|---|---|---|
| Baseline | 2026-10-22 | ✅ "commit the current version… baseline build" (V14) | waived (V14) | 2026-10-20 eval (pre-fix) | `baseline-v0.2` |
| U0 | 2026-10-22 | ✅ "go ahead" (V15) | [`U0.2.md`](docs/reviews/U0.2.md) | `gates/U0.md` (U0.4 pending, runs in parallel) | `upgrade-U0` |
| U1 | 2026-10-22 | ✅ order + aura approved (D-18) | [`U1.1`](docs/reviews/U1.1.md), [`U1.2/U1.4`](docs/reviews/U1.2_U1.4.md), [`U1.3/U1.5`](docs/reviews/U1.3_U1.5.md) | n/a (visual) | `upgrade-U1` |
| U2 | | ⬜ | | n/a (UI tests) | `upgrade-U2` |
| U3 | | ⬜ | | n/a (voice tests) | `upgrade-U3` |
| U4 | | ⬜ | | n/a (visual) | `upgrade-U4` |
| U5 | | ⬜ | | fixture sweep | `upgrade-U5` |
| B1 | | ⬜ | | `gates/B1.md` | `upgrade-B1` |
| B2 | | ⬜ | | `gates/B2.md` | `upgrade-B2` |
| B3 | | ⬜ | | `gates/B3.md` | `upgrade-B3` |
| B4 | | ⬜ | | `gates/B4.md` | `upgrade-B4` |
| H1 | | ⬜ | | `gates/H1.md` | `upgrade-H1` |
