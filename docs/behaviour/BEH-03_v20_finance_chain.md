# BEH-03: V20 Finance Chain (income statement → year → Yahoo-style table → WACC → why → top-5 actions)

**Features:** FEAT-024, FEAT-018, FEAT-020, FEAT-025, FEAT-032 · **Steps:** P2F.1–P2F.6, P1.11 (V20 chain) · **Specs:** [SPEC-08](../specs/SPEC-08_v20_finance_diagnostics.md), [SPEC-01](../specs/SPEC-01_financial_ssot.md), [SPEC-02](../specs/SPEC-02_wacc_dcf_engine.md) §5, [SPEC-09](../specs/SPEC-09_statement_visual_chart_portfolio.md), [SPEC-11](../specs/SPEC-11_one_brain_provenance_eval.md) §8.4 · **Golden chain:** `V20` in `eval/golden_v3/chains.yaml`

> [!IMPORTANT]
> **BLUF.** This script is the acceptance test for V20. Each scenario has a fixed user line, an exact expected visual type and exact numbers from the verified SSOT, each cited to an AR page.
> Every turn must also carry the stated provenance badge. Any wrong number on a KPI line fails the chain.
> Default persona is **CMD** in a fresh session, with BigQuery and the LLM healthy, unless stated. Money is standalone ₹ crore. "10-yr" = AR FY2025-26 "A Decade of Operational and Financial Excellence – Standalone", printed p.21–22 (PDF p.23–24).

---

## Conventions
- `= SSOT(<line>, <FY>)` means the value read from `fact_financial_statement_line` (single FY: as-reported vintage; multi-year: latest restated vintage, SPEC-01 §7.1). The literal in brackets is the expected value today.
- "AR FY24 p.245" = printed folio, as shown in the UI (PDF page = folio + 2 for AR FY24–FY26).
- Visual types follow SPEC-09: `statement`, `chart:<kind>`, `kpi`, `table`, `actions`, `none`.
- "Spoken" = `spoken_summary` (voice reads it verbatim, SPEC-11 §6).

## BEH-03.01 Year clarification (no FY given)
**Given** a fresh session (no FY in context)
**When** the user says "Can I see the income statement?"
**Then**
- `visual.type = none`; contract `clarify.slot = fiscal_period` with exactly 4 options in this order: "FY26 (latest)", "FY25 (last year)", "Last 5 years", "Last 10 years" (generated from coverage).
- Spoken: "Which year would you like: FY26, FY25, or the last five or ten years?"
- No statement rows are returned. No FY26 default is applied silently (fixes BUG-14).

## BEH-03.02 Answer "the present year" → single-FY statement
**Given** BEH-03.01 is pending
**When** the user says "the present year" (or taps "FY26 (latest)")
**Then**
- `visual.type = statement`, columns `FY26 | FY25` (FY + comparative), rows indented per `dim_financial_line`, subtotals bold, negatives in parentheses.
- Revenue from operations FY26 `= SSOT(PL.REV_OPS, FY26)` (₹1,32,508.14 cr, AR FY26 p.295); Profit before tax `=` ₹42,414.89 cr; Total tax expense `=` ₹9,520.87 cr; Profit for the year `=` ₹32,894.02 cr; EPS ₹26.15.
- FY25 comparative column: Revenue ₹1,37,846.29 cr; PAT ₹35,610.32 cr (AR FY26 p.295 comparative = AR FY25 p.271).
- Footer: "Source: ONGC Integrated Annual Report FY2025-26, Standalone Statement of Profit and Loss, p.295". Badge **Verified · Annual Report**.
- Spoken (template): "Here is ONGC's standalone income statement for FY26. Revenue from operations was ₹1,32,508 crore, down 3.9% on FY25, and profit after tax was ₹32,894 crore."

## BEH-03.03 Answer "last 5 years" → Yahoo-style multi-year statement
**Given** BEH-03.01 is pending (alternative branch)
**When** the user says "last 5 years"
**Then**
- `visual.type = statement`, 5 FY columns newest → oldest: FY26, FY25, FY24, FY23, FY22.
- Revenue from operations row: 1,32,508.1 · 1,37,846.3 · 1,38,402.1 · 1,55,517.3 · 1,10,345.4 (10-yr; FY24 = SSOT value ₹1,38,402 cr, AR FY24 p.245).
- PAT row: 32,894.0 · 35,610.3 · 40,526.0 · 40,096.5 · 40,305.7.
- FY23 column header has a `*` restated marker (the 10-yr table marks FY23). The FY24 *Other income* cell shows 10,735.5 with a `†` footnote: "Restated in AR FY25 p.271; originally ₹10,778.19 cr (AR FY24 p.245)".
- The per-column source footer lists the AR used for each FY.
- Spoken: "Here is the standalone income statement for FY22 to FY26. Revenue peaked at ₹1,55,517 crore in FY23 and was ₹1,32,508 crore in FY26; profit after tax was ₹32,894 crore in FY26."

## BEH-03.04 Voice answer to the clarification (Hindi-English)
**Given** BEH-03.01 is pending in a voice session
**When** the user says "pichhle saal ka dikhao"
**Then** the result is identical to BEH-03.02 but for FY25 (columns FY25 | FY24), with `language = hi-en` and a Hindi spoken summary. Exactly 1 agent bubble is added (SPEC-11 §6.3).

## BEH-03.05 WACC for the past 10 years
**Given** BEH-03.03 is on screen
**When** the user says "What was the weighted average cost of capital for the past 10 years?"
**Then**
- `visual.type = chart:line`, 10 points FY17 → FY26 `= SSOT(fact_wacc_annual.wacc_pct, FYxx)` (oracle values), with dashed secondary series Ke and Kd(1−t).
- Badge **Modelled**. Subtitle names the input sources (FBIL/RBI 10-yr G-sec, Damodaran ERP, 2-yr weekly beta vs NIFTY 50, AR finance cost and debt).
- `sources[]` includes `fact_wacc_input` families. If any FY used a fallback (industry beta, ERP vintage gap), the caveat says so.
- "past five years" gives the same with 5 points FY22–FY26.

## BEH-03.06 Why was WACC high in FY23?
**Given** BEH-03.05 is on screen
**When** the user says "Why was it high in FY23?"
**Then**
- `visual.type = chart:waterfall` from WACC FY22 to WACC FY23 with 5 bars (Rf, ERP, beta, Kd after tax, weights); the bars sum exactly to ΔWACC (±0.001pp; Shapley, SPEC-02 §5.3).
- The narrative names the top 2 factors with values and sources (e.g. "the 10-year G-sec rose from x% to y% (RBI, 31-Mar-2023)"). No number appears that is not in `fact_wacc_input`.

## BEH-03.07 Why did profit fall in FY26? (line-item root cause)
**Given** any prior state
**When** the user says "Why did profit fall in FY26?"
**Then**
- `visual.type = chart:waterfall` (signed PBT bridge) starting at PBT FY25 ₹46,759.8 cr and ending at PBT FY26 ₹42,414.9 cr (Δ −4,344.9; closure ±₹0.1 cr). Bars in this order of |impact|: Revenue −5,338.2 · Statutory levies +4,820.4 · Exchange loss −1,931.7 · Provisions & write-offs −1,142.4 · DD&A −781.4 · Operating expenses −730.1 · Other expenses +710.4 · Other income −123.7 · Exploration write-offs +97.0 · Finance costs +74.7 (10-yr).
- Lead sentence: "Profit before tax fell ₹4,345 crore. The biggest drivers were lower revenue (−₹5,338 crore, mostly crude price including FX, −₹6,108 crore, partly offset by volume +₹383 crore), lower levies (+₹4,820 crore, mainly other levies including SAED +₹3,969 crore) and a higher exchange loss (−₹1,932 crore)."
- Then 1–3 AR excerpts or paraphrases with cites, e.g. "[AR FY26 p.N]", retrieved by `VECTOR_SEARCH` filtered to FY26 and the driver line codes. No AR number is used as a claim unless quoted.
- PAT fall is stated as ₹2,716.3 cr (35,610.3 → 32,894.0).
- No EBITDA is synthesised; the waterfall never ends at a value other than PBT FY26 (BUG-08/09).

## BEH-03.08 Express as waterfall / back to table (re-plot honesty)
**Given** BEH-03.02 (single-FY statement) is on screen
**When** the user says "express this as a waterfall"
**Then** `chart:waterfall` built from statement lines: Revenue from operations + Other income → expenses (signed) → PBT 42,414.9 → tax → PAT 32,894.0. The last bar equals PAT FY26 exactly.
**When** the user then says "show it as a line chart"
**Then** the explicit kind wins (`chart:line` over FY columns, or the honest message "A line chart needs more than one year. Showing FY22–FY26?" with a chip), never a waterfall (BUG-22) and never a false "I've switched the view" (diag_D B11).

## BEH-03.09 Top-5 actions ("five things for others to act on")
**Given** BEH-03.07 has been answered (FY26 context)
**When** the user says "What are the top 5 actions?"
**Then**
- `visual.type = actions` with ≤ 5 cards, each with: title, what to do, ₹ impact (low–mid–high, `Modelled estimate`, one-off or annual), owner ∈ {CMD, DIR_FIN, DIR_HR}, horizon, KPI, evidence (data row + AR page when found), confidence.
- Must include **L02 Receivables** (debtor days 32 in FY26 vs 29 in FY25, 10-yr ratios), owner DIR_FIN; and **L08 FX exposure** (exchange loss ₹2,698.9 cr vs ₹767.2 cr), owner DIR_FIN. **L09 Provisions** fires (₹3,947.6 cr vs ₹2,805.2 cr, +40.7%).
- Under the cards: the table **"Five things for others to act on"** (Owner | Ask | By when | KPI | Evidence), with at most 3 rows per owner.
- Same input → same list (deterministic). Badge **Modelled estimate** on the ₹ impacts (`impact.label = "Modelled estimate"`, SPEC-08 §7.3); data cells **Verified**.
- Suggestion chip: "Draft this as a memo to the Directors".

## BEH-03.10 Persona variants
| Given persona | When | Then |
|---|---|---|
| DIR_FIN | BEH-03.09 | Same list; DIR_FIN-owned actions first |
| DIR_HR | BEH-03.09 | HR lever L07 included if it fires (labelled Synthetic, SPEC-04) + company top 2 |
| E2_FIN | BEH-03.09 | Analysis and actions shown **without** owner/assignment column ("for discussion"); statements and WACC allowed |
| E1_HR | "show income statement FY26", then BEH-03.09 | Statement allowed (public AR data, `general_fin` = A per SPEC-06). Actions request → `fin_diagnostics_agent` runs (callable by all 11, SPEC-03 §4.2); the result is masked by `enforce_contract`: analysis and actions **without** the owner/assignment column, `fin_internal` detail aggregated (SPEC-06 §4.3, SPEC-08 §7.4) |

## BEH-03.11 Degraded: BigQuery down
**Given** ADC expired (`/health.adc = expired`)
**When** the user says "balance sheet for 2024"
**Then** a `statement` from the verified local snapshot: Total assets ₹4,46,020.89 cr, Total equity ₹3,05,976.51 cr (AR FY24 p.243). Badge **Local snapshot <date>**, banner shown, and no "Compiled SQL" or BigQuery source claim (BUG-04). Requests for WACC "why" still work from the snapshot; voice is disabled.

## BEH-03.12 Coverage question mid-chain (feedback4 regression)
**Given** BEH-03.02
**When** the user says "when you say up to 2026, is 2024 before 2026? then show it to me"
**Then** the deterministic coverage intent answers "Yes. I have standalone statements from FY17 to FY26, including FY2023-24" and shows the FY24 income statement (Revenue ₹1,38,402.13 cr, AR FY24 p.245). There is no apology/contradiction loop (BUG-05).
