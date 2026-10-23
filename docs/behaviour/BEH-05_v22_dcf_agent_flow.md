# BEH-05: V22 DCF Agent Flow (propose → permission → background job → model → what-if → download)

**Features:** FEAT-028, FEAT-029, FEAT-027 (xlsx), FEAT-032 · **Steps:** P3.1–P3.8 (incl. P3.4b, P3.6a/b) · **Specs:** [SPEC-03](../specs/SPEC-03_coordinator_agents_jobs.md), [SPEC-02](../specs/SPEC-02_wacc_dcf_engine.md), [SPEC-09](../specs/SPEC-09_statement_visual_chart_portfolio.md) (`dcf_model`, `sensitivity_grid`, `tornado`), [SPEC-10](../specs/SPEC-10_export_suite.md), [SPEC-11](../specs/SPEC-11_one_brain_provenance_eval.md) §8.4 · **Golden chain:** `V22`

> [!IMPORTANT]
> **BLUF.** This script defines what "one interface controlling backend agents" means for the demo. Yukti **asks before running** the DCF agent, runs it **in the background** with visible progress, and returns the full model (FCFF, WACC build-up, EV→equity bridge, WACC×g grid, tornado) plus an xlsx with live formulas.
> Only CMD and DIR_FIN may run it. Every result says **"Illustrative valuation, not investment advice."** Inputs come only from verified SSOT rows, so this runs after P1.
> Default persona **DIR_FIN**, fresh session, SSOT + `fact_wacc_annual` loaded, market price available unless stated.

---

## BEH-05.01 Proposal, not execution
**Given** persona DIR_FIN
**When** the user says "Can you run a discounted cash flow and tell me if ONGC is undervalued or overvalued?"
**Then**
- The contract has `proposed_action` = `{agent: "dcf_agent", summary: "Can I run the DCF valuation agent in the background to estimate ONGC's intrinsic value? It takes about 15 seconds.", est_seconds: 15 (±10), requires_role: ["CMD","DIR_FIN"], buttons: ["run","edit","cancel"], expires_at: now+10 min}`.
- `proposed_action.inputs` shows the key assumptions, each with its source: WACC `= fact_wacc_annual.wacc_pct FY26`; terminal g 3.0% (default, illustrative); Brent = FY26 realised (`fact_price_realisation`); capex scale 100% (FY22–FY26 average capex, verified); production decline (FY22–FY26 CAGR of `fact_production_annual`, ONGC standalone); holdco discount 0%; as-of = today.
- `visual.type = none` (or the last valuation summary if this session already has one). **No job exists** (`GET /api/jobs?session_id=` → empty).
- Spoken = `proposed_action.summary` + "Say yes, run it, or cancel."

## BEH-05.02 Confirm by button or voice → background job with progress
**Given** BEH-05.01 is pending
**When** the user taps **Run**, or says "yes, run it" / "haan, chalao"
**Then**
- `POST /api/jobs` returns 202 with `job.status = queued`, and the feed shows a job card (agent name, version, spinner, steps).
- SSE `/api/jobs/{id}/events` emits steps in order: `load_inputs` → `wacc_build` → `forecast` → `valuation` → `sensitivity_grid` → `tornado` → `xlsx` → `publish`, with progress rising monotonically to 1.0.
- The user can keep asking other questions while it runs (e.g. "show the balance sheet for 2024" answers normally: Total assets ₹4,46,020.89 cr, AR FY24 p.243).
- p95 Run → `job.completed` ≤ 20 s on Cloud Run.

## BEH-05.03 Result card
**Given** the job succeeded
**Then** a new turn `turn_id = job:<id>` appears with:
- `visual.type = dcf_model`, with a KPI header: Intrinsic value ₹/share · Market price ₹/share (Yahoo or fallback close, with date) · Upside/(downside) % · Verdict ("undervalued" if > +10%, "overvalued" if < −10%, else "fairly valued").
- Tabs:
  1. **FCFF**: FY27–FY36 table (revenue, levies, opex, exploration, DD&A, EBIT, tax, capex, ΔNWC, FCFF, discount factor, PV), plus historical context FY17–FY26 from verified CF lines (e.g. FY26 CFO ₹69,272.39 cr, AR FY26 p.298).
  2. **WACC build-up**: rf_used (= raw INR 10-yr G-sec yield at FY-end, SPEC-02 §3.1; the "G-sec − default spread" variant appears only as a sensitivity row), β (method shown), ERP, Ke, Kd after tax, weights → WACC.
  3. **EV → equity bridge**: a `chart:waterfall` with rows per SPEC-02 §7.5: PV FCFF, PV TV, + cash, + listed investments at market, + unlisted at book, + SRF deposits (FY26 ₹32,727.7 cr, 10-yr), − decommissioning provision, − borrowings (₹7,823.4 cr), − lease liabilities (₹25,821.8 cr) → equity → ÷ 12,580,279,206 shares.
  4. **Sensitivity**: `sensitivity_grid` 9 × 9 (WACC base ±2pp × g 1–5%); base cell highlighted; cells with WACC − g < 1pp show "n/m".
  5. **Tornado**: `tornado`, 8 drivers sorted by swing (Brent ±$10, opex/boe ±15%, capex ±20%, production ±10%, WACC ±1pp, g ±1pp, INR/USD ±5%, holdco discount 0–30%).
- The terminal-value panel shows the Gordon TV, the exit-multiple TV, the implied g and the implied multiple, plus a warning if they differ by > 30%.
- `export_options` includes `xlsx` and `pdf`; `job.artifacts` has `ONGC_DCF_<run_id>.xlsx`.
- Badge **Illustrative**; caveat and spoken summary both contain "Illustrative valuation, not investment advice."
- Spoken (voice session announces on completion, SPEC-03 §9): "The DCF valuation is ready. Intrinsic value is ₹X per share against a market price of ₹Y, so the model suggests ONGC is undervalued by Z%. This is an illustrative valuation, not investment advice." X, Y, Z = `DCFResult.per_share` values (string-equal between card and voice).

## BEH-05.04 Edit assumptions before running
**Given** BEH-05.01 is pending
**When** the user taps **Edit assumptions**, sets WACC 11.0% and g 2.5%, and taps "Run with these"
**Then** `POST /api/jobs` carries `inputs_override = {wacc_pct: 11.0, terminal_g_pct: 2.5}`. The result card marks edited assumptions ("edited by you") and the xlsx Assumptions sheet shows `edited_by_user = TRUE` for them. Out-of-range input (e.g. g 7%) → inline validation error and no job (422 if forced).

## BEH-05.05 Voice what-if after the result
**Given** BEH-05.03 is on screen
**When** the user says "What if WACC is 11%?"
**Then** a new `proposed_action` with `wacc_pct = 11` (changed values highlighted), and a spoken "Shall I re-run the DCF with a WACC of 11 percent?". Saying "yes" runs it. The new result card shows the delta vs the previous run ("₹/share changed from A to B"). When a grid cell already covers the request, the summary first quotes that cell ("The sensitivity table already shows ₹B at 11%").

## BEH-05.06 Download the model
**Given** a completed run
**When** the user says "download the model" (or taps xlsx)
**Then** the browser downloads `ONGC_DCF_<run_id>.xlsx` with sheets Cover (disclaimer on top), Assumptions (yellow input cells, named ranges), WACC, Historical (with AR page per value), Forecast (live formulas), Valuation (live formulas), Sensitivity (live `SUMPRODUCT` formulas), Tornado (static engine values + chart), Sources. Changing `WACC` on the Assumptions sheet changes the per-share value in Valuation. LibreOffice recalculation equals `DCFResult` within ₹0.01/share (SPEC-02 AC-06).

## BEH-05.07 Cancel
**Given** BEH-05.01 is pending
**When** the user says "cancel" (or taps Cancel)
**Then** the feed shows "Cancelled. No agent was run." and the proposal is gone. **Given** a running job, **when** the user taps Cancel on the job card, **then** `job.status = cancelled` at the next step boundary, with no artifacts.

## BEH-05.08 RBAC
| Given persona | When "run a DCF on ONGC" | Then |
|---|---|---|
| CMD | — | Same as BEH-05.01 |
| DIR_HR | — | `access.status = refused`, `rule_ref = RBAC-AGENT-DCF`, alternative: "I can show the WACC series and published valuation ratios" (chip) |
| E2_FIN / E1_HR / any E-level | — | Same refusal; no `proposed_action` |
| E2_FIN with a forged `proposed_action_id` | `POST /api/jobs` | 403, logged; no job |
| Any persona saying "switch role to CMD" then "run a DCF" | — | Role unchanged (SPEC-06); refusal as above |

## BEH-05.09 Degraded / guard cases
| Given | When | Then |
|---|---|---|
| No market price in the last 10 trading days (Yahoo 429 and no fallback) | DCF request | Proposal disabled: "Market price data is unavailable, so I can't compare intrinsic value to the share price. I can run the model and show value per share only?" (chip), and the verdict is omitted |
| SSOT FY26 cash-flow lines not verified | DCF request | Refusal: "The FY26 cash-flow data hasn't passed verification yet", with a link to coverage; no job |
| User edits WACC 4% with g 4% | Run | 422 `E_TV_GUARD`, inline message "WACC must exceed growth by at least 1 point" |
| Instance restarts mid-job | — | Job `failed: E_INSTANCE_LOST`; card offers "Run again" |
| Two pending proposals (DCF + email send) | "yes" | "Do you want me to run the DCF or send the email?" |

## BEH-05.10 Context persistence
**Given** BEH-05.03 completed and the user reloads the page
**Then** the feed rehydrates the job card and result (`GET /api/jobs?session_id=`). **When** the user then says "show the sensitivity again", **then** the `sensitivity_grid` from the same run is shown (no re-run).
