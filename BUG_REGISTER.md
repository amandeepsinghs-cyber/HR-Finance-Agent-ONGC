# Yukti AI — Bug Register (`BUG_REGISTER.md`)

**Opened:** 23-Oct-2026 (deep diagnosis) · **Owner:** Opus lead · **Process:** a bug closes only when its checklist step passes G4 with a regression test (BUILD §4.2) · **Sources:** feedback/feedback1–4.md, current_refinements.md, diagnosis reports A–E (`yukti_deep_diagnosis.md` §3)

> [!IMPORTANT]
> **BLUF:** 41 bugs logged (6 closed): **14 Blockers, 26 Important, 1 Cosmetic group**. The three that hurt the CMD demo most are **BUG-02** (wrong balance-sheet and cash-flow numbers labelled "Audited"), **BUG-06** (an E-level user can escalate to CMD by voice) and **BUG-08** (the waterfall chart is mathematically wrong).

**Status legend:** 🔴 Open · 🟠 Fix in progress (uncommitted WIP in `wip/pre-v3-snapshot`, unverified) · ✅ Closed (G4 + test) · ↩ Regressed

## Blockers

| ID | Status | Symptom | Root cause (file:line) | Fix | Step | FEAT |
|---|---|---|---|---|---|---|
| BUG-01 | ✅ | Every answer: "Data is currently not available" | ADC expired (`RefreshError`, 157× in backend log since 06:29 UTC 23-Oct) | Sponsor re-auth; `/health` auth status + UI banner | P0.1 | 032 |
| BUG-02 | ✅ | BS/CF/ratios wrong (FY24 total assets 4,22,820 vs AR 4,46,021; FY25 CFO 63,180 vs 73,010; ROCE ~2×) yet labelled "Audited + Yahoo" | Hard-coded literals `financial_build/scripts/build_10yr_financials.py:29-1120`; plugs `:1193-1199`, `:1223`; labels `compiler.py:552,587,632,667,708,743`, `presenter.py:155,487` | Labels removed now (P0.3); rebuild from AR (P1) | P0.3, P1.2–P1.10b | 018, 032 |
| BUG-03 | ✅ | Same metric, three values (FY17 royalty 7,635 / 8,548 / AR 11,575) | `data_bank/landing/governance/corporate_financial_summary.csv` vs JSON vs AR | Single `fact_financial_statement_line` | P1.6, P1.10b | 018 |
| BUG-04 | ✅ | Answers say "Compiled SQL / BigQuery" but come from local JSON | Silent fallback `compiler.py:867-1007` | `source=local_snapshot` + badge | P0.3 | 032 |
| BUG-05 | ✅ | feedback4: "data only up to 2026… balance sheet for 2024 not available" → apology/flip loop | Legacy ADK prompt lacks statement tables, says FY18–FY27 (`semantic_layer.py:60`); no coverage source of truth; statement route absent in HEAD | Planner regex fix in WIP (keyword phrasings only); coverage manifest; one brain | P1.10a, P1.11, P5.1, P5.3 | 030 |
| BUG-06 | ✅ | E2_HR says "switch role to CMD" → becomes CMD (verified by curl) | `turn_runner.py:265-268`; `page.tsx:330`; persona in request body (`main.py`) | Server-side persona; no free-text role switching | P0.4, P2H.2 | 031 |
| BUG-07 | ✅ | Every junior sees Pooja Verma's (EMP-102451) leave/transfer data | `yukti/backend/certified/library.yaml:1617,1649,1673,1743` hard-coded emp_id | `dim_app_user` + `@self_emp_id` | P2H.1 | 017, 031 |
| BUG-08 | ✅ | "Express this as a waterfall" → Total ≈ 3× revenue | `turn_runner.py:275-296` and `compat.ts:71-73` discard the correct `presenter.py:192-216` bridge; `options.ts:392-420` sums untyped rows | Keep `chart.data`; signed bridge helper; test ends at PAT | P4.1 | 026 |
| BUG-09 | ✅ | Waterfall invents EBITDA (`rev*0.68`, `(rev+pbt)/2`) | `plan.ts:146`, `compat.ts:130`, `chart_rules.py` single-row branch | Delete synthesis; re-query or refuse | P4.1 | 026 |
| BUG-10 | ✅ | "Can you export this as an Excel file" not understood | `ui_control.py:291`, `uiCommands.ts:251` literal phrases only | Broad EN/HI intent + columns + link | P2H.4 | 023 |
| BUG-11 | ✅ | "Draft an email to Director HR" → canned AGT proposal ("401 net recommendations" vs "146 relocations") | No email type; `_DOC_RE` lacks email (`pipeline.py:36`); static numbers `tools/draft_document.py:105-131`; routing `turn_runner.py:1140-1245` | Email agent from the session cohort | P2H.4 | 023 |
| BUG-12 | ✅ | Hard-coded answers/numbers (Parliament "143 vacancies", Champang EBITDA-negative, `or 33108.97`, "42.6%/29.1%", FX 84.0) | `turn_runner.py:1541-1550, 1609-1613, 2192-2228`; `draft_document.py:54-63` | Delete; derive from query results | P2H.4 (`draft_document.py` literals), P5.1 | 030 |
| BUG-13 | 🔴 | Cloud Run = baseline rev `00001`; `financial_build/` not in the image | `Dockerfile:29-36`; (was untracked; now in the snapshot) | Packaging decision; redeploy from green | P0.9, P5.6 | 014 |
| BUG-35 | 🟠 | Container image cannot build: Dockerfile `lint:tokens` gate fails on raw colours | Pre-existing hard-coded rgba/hex in `FloatingConversationPanel.tsx`, `TopBar.tsx`, `VoiceOrb.tsx` (found in P0.9) | Move colours to design tokens; keep the gate | P4.9, P5.6 | 014 |

## Important

| ID | Status | Symptom | Root cause | Fix | Step | FEAT |
|---|---|---|---|---|---|---|
| BUG-14 | ✅ | "Show income statement" silently shows FY26 | No period clarification (`pipeline.py`; `normalize.py:6` default) | Clarify chips | P2F.1 | 024 |
| BUG-15 | ✅ | WACC questions → error, or the P&L | No WACC data/metric; `planner.py:~466-480` fin_kw guard | `fact_wacc_annual` + metric | P1.9, P2F.3 | 024 |
| BUG-16 | ✅ | "Why" and actions are canned (1 action per statement-year) | Keyword retrieval over 129 generated chunks `insight_context.py:138-233`; `build_and_load_financial_rag.py` | Variance engine + AR chunks + action generator | P1.8, P2F.4–P2F.5 | 020, 024 |
| BUG-17 | ✅ | Duplicate/fragment bubbles in voice mode (feedback4) | Local barge-in hears Leda's echo; `live_session.py:803-804` clears `_is_speak_only`; stale `turn_complete` `:930-931` | `speak_id` gating; suppress barge-in during speak | P0.10 | 013 |
| BUG-18 | ✅ | Contract text + Live transcript concatenated in one bubble (feedback2/3) | `page.tsx:397-446` | One source of truth per turn | P0.10 | 013 |
| BUG-19 | ✅ | English narration for Hindi questions; Hindi re-voicing appended | Narrator English-only; Live model re-voices | Translate `spoken_summary`; speak verbatim | P5.2 | 030 |
| BUG-20 | ✅ | `resolve_fy("FY 2024-25")` → FY24–FY25 range (2 tests red) | Uncommitted change `semantic/normalize.py` | Treat `YYYY-YY` as a single FY | P0.2 | 030 |
| BUG-21 | ✅ | "Why did revenue fall in FY23" hijacked into the Mumbai High vs Bassein FY26 comparison | Broad regex `turn_runner.py:2161-2165` before the planner | Remove | P5.1 | 030 |
| BUG-22 | ✅ | "… as a line chart" → waterfall; "tabular form" not recognised | `chart_rules.py:31, 42-50` | Explicit kind wins | P4.1 | 026 |
| BUG-23 | ✅ | `combo`/`heatmap`/`box`/`gauge` silently fall back to bar | No branch in `plan.ts:135-211` | Implement renderers | P4.4 | 026 |
| BUG-24 | ✅ | PDF export prints ₹ and Hindi as ■; text only, 90-char truncation | reportlab Helvetica `export_tool.py:142-166` | Embedded Noto fonts + tables + chart image | P4.6 | 027 |
| BUG-25 | ✅ | "Google Docs" opens a dead `docs.google.com/document/d/exp_…` link; "Sheets" downloads xlsx | Dry-run URL treated as real (`AnswerCard.tsx:248-251`; `main.py:343`) | Honest download + toast; Drive OAuth later | P4.6–P4.7 | 027 |
| BUG-26 | 🟠 | E1 salary breakdown: crore totals, then a fudge-scaled per-head; "joining E1 pay" = average of incumbents (19.6 yrs service) | No component metrics; `turn_runner.py:1881-1900` scale factor; no entry-pay logic | Component metrics; entry pay from `dim_grade` | P2H.5–P2H.6 | 021 |
| BUG-27 | ✅ | Only 5 of 11 personas; unknown persona → E2_HR silently | `access_control.py:12,243`; `rbac_policy.yaml:15`; `TopBar.tsx:26-31` | 11 personas + function split | P2H.1 | 017 |
| BUG-28 | ✅ | Juniors refused aggregate pay by grade (V14 allows aggregates) | `topic_keywords.pay` | Allow aggregate by grade | P2H.1 | 017 |
| BUG-29 | 🔴 | SSOT leave balances likely always 0 | `yukti/backend/scripts/build_ssot_gold.py:76-78` filters "EL"; values are `Earned_Leave_EL` | Fix mapping in the Employee-360 build | P2H.5–6 | 021 |
| BUG-30 | ✅ | Age band "30-40" actually spans 30–50; "40-50" has 9 people | `data_bank/generators/hr/gen_21_hr_core.py:280-288` | BRSR bands | P2H.5 | 021 |
| BUG-31 | ✅ | Gemini-generated policy clauses presented as "authentic, statutory-grade ONGC" (R16) | `current_refinements.md:52`; `rulebooks_clause_index.csv` | **Label "Illustrative"** (D-35) | P0.7 | 032 |
| BUG-32 | ✅ | CORS `*` with credentials; unauthenticated `/admin/cache/clear` | `main.py:52-63` | Allow-list; auth | P0.5 | 031 |
| BUG-33 | ✅ | Error text leaks internals ("Reauthentication is needed…") | `turn_runner.py:1448` `str(e)[:100]` | Generic message; log details | P0.1 | 032 |
| BUG-36 | ✅ | A validly signed token with `iat: Infinity` → uncaught OverflowError → HTTP 500 (only a key holder can trigger it); prod with no key says "Unknown persona." | `auth.py` verify_token ~L248 | Bound/validate numeric claims; clearer prod-misconfig copy | P2H.2 | 031 |
| BUG-37 | ✅ | Snapshot finance answers still show an unlabelled "Director (Finance) Action" line (generated text) | `insight_context.py` snapshot path | Label as unverified or drop until P2F.6 | P1.10a | 032 |
| BUG-38 | ✅ | Balance-sheet output: line-item text is cut off and unreadable (sponsor, 23-Oct live test) | Generic `TableRenderer` truncates the first column (fixed widths / ellipsis; no wrap; inline bar column steals width) | `StatementTable`: first column wraps (never truncated), min width ≥ 40% of the card, sticky, tooltip not required; test at 1366 px, 1920 px and big screen | P4.3 | 025 |
| BUG-39 | ✅ | Artificial numbering on balance-sheet items ("A1.", "A2.", "I.") not wanted (sponsor) | Invented `line_name` prefixes in `financial_build/scripts/build_10yr_financials.py` (e.g. "A1. Oil & Gas Producing Properties") | Show the AR line names as reported (`line_name_as_reported`), with hierarchy expressed by indentation only; strip legacy prefixes in the snapshot path now | P1.6, P4.3 | 025 |
| BUG-40 | ✅ | Yukti's voice "breaks a bit" (choppy playback) after the P0.10 fix; sponsor unsure if it's network (23-Oct live test) | To diagnose: network jitter vs. playback scheduling (no jitter buffer / chunk underruns in `audioAnalyser.ts`) vs. CPU on the demo laptop | Measure chunk inter-arrival + underrun counts; add a ~150–250 ms adaptive jitter buffer; test on wired vs. Wi-Fi | P5.2 | 013 |
| BUG-41 | ✅ | Talk-over (voice) interruption is disabled by default (`VOICE_BARGE_IN=false`): a level-based detector cannot reliably separate Yukti's echo from the user's voice (G4 P0.10 r2: slow swells with lag still fire) | Laptop-speaker echo survives browser AEC; detector only sees mic level | Re-enable only with an echo-aware approach: AEC reference/far-end signal, Live server VAD with headset detection, or a push-to-talk hold; tap/Space/Esc/Stop interrupt meanwhile | P5.2 | 013 |
| BUG-42 | ✅ | Revenue answer's hero KPI sums 5 years of revenue ("₹6,74,618 crore across 5 years"); the PDF export repeats it (found in P4.7 testing, 24-Oct) | Presenter/insight KPI builder totals a flow measure across periods | Never total flow measures across fiscal years; use latest FY + CAGR/Δ; KPI rule in SPEC-09 rubric | P2F.2, P4.8 | 025 |
| BUG-43 | ✅ | Multi-series chart legends show raw column keys (`corporate_revenue_cr`, `vap_revenue_cr`) on screen and in PNG/SVG/PDF | Legend names taken from data keys without `humanizeKey`/semantic display names | Series display names from the semantic model; fallback humanise | P4.8 | 026 |
| BUG-44 | ✅ | **RBAC UX (no data leak):** as E2_HR, Hindi "रमेश कुमार का वेतन बताओ" passes the gate (`access.status=allowed`) and the agent asks for the employee ID to reveal individual pay; it also shows generic suggestions (found in lead E2E, 24-Oct 06:09). Supplying the ID is refused correctly, so no pay leaks. The live P0 demo (:8095) behaves the same | Hindi named-pay patterns missing from planner/decide and legacy check_access; tools don't re-check individual pay for juniors | HI/Hinglish named-pay → R-PAY before any LLM call; tool-level Principal check; REST-path tests | P2H.2 | 017, 031 |
| BUG-45 | ✅ | **Security (branch only, not live):** on v3/P2H-hr at 36d2c26+, a composite question ("What is the POSH policy, and what is the salary of Ramesh Kumar?") returns a named salary to E2_HR; "…and show Sunita Sharma's medical history" runs a medical query (G4 P2H.2 r2) | P2H.2 M5 policy early-allow in access_control.py:590 and the sensitive class dropped in rbac.py | No early allow; most-restrictive result across clauses; compile/tool-level re-check; REST composite tests | P2H.2 | 017, 031 |
| BUG-46 | ✅ | Allowed answers in Hindi mode come back with English display text (e.g. "E2 का औसत वेतन" → "Average gross pay (FY26…)") | Narrator/display text not localised for templated answers | Localise templated display/spoken text per BEH-07 | P5 (BEH-07) | 006 |

## Cosmetic

| ID | Status | Symptom | Fix | Step |
|---|---|---|---|---|
| BUG-34 | ✅ | Grade axis ordered by count, not E1→E9; generic titles ("Updated Chart View"); no waterfall connectors; panel thread duplicates the main feed by design | Grade order; insight titles; connectors; hide the thread when the feed is visible | P2H.3, P4.8 |

## Previously reported and fixed (verify in the P5 regression suite)

| Ref | Item | Status |
|---|---|---|
| fb3 / R15 | "Casual leave" → study-leave answer | ✅ Verified live 23-Oct (router guard `router.py:239-245`); add a regression test |
| fb1 / R1 | Mehsana 10-yr production returned a single total | 🟠 Fixed in WIP; verify |
| fb1 | Salary columns labelled "years" (`detect_unit` matched "age" in "average") | 🟠 Fixed in WIP; verify |
| fb2 / R4 | "Hindi bolni aati hai?" → English greeting | 🟠 Fast-path added; verify |
