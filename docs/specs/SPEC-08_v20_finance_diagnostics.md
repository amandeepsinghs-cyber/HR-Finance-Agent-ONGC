# SPEC-08: V20 Finance Diagnostics (year clarification → statement → WACC → why → top-5 actions)

**Features:** FEAT-024 (V20 finance diagnostics) · uses FEAT-018/020 (SSOT + AR RAG), FEAT-025 (statement visual), FEAT-028 (`fin_diagnostics_agent`) · **Phase:** P2F (P2F.1–P2F.6; golden chain in P1.11 / P5.4) · **Spec owner:** O · **Status:** Draft v3 (23-Oct-2026) · **Behaviour:** [BEH-03](../behaviour/BEH-03_v20_finance_chain.md)

> [!IMPORTANT]
> **BLUF.** The V20 chain fails after its first step today. There is no year question, no multi-year table and no WACC. "Why" and "actions" are canned text, and the grounding check is circular (BUG-14/15/16/22).
> Rebuild it as five deterministic stages over the verified SSOT: (1) a **year clarification** with chips and voice; (2) a **multi-year, Yahoo-style statement** (4–10 FY columns); (3) a **WACC 5/10-yr chart** (SPEC-02); (4) a **variance-attribution engine**: each line's YoY Δ is split into price / volume / FX / levy-rate / unit-cost / one-off components where the data allows, and the drivers are ranked; "why" is answered from those rows plus real AR MD&A chunks with page cites; (5) a **top-5 action generator**: lever library → ₹ impact → owner (CMD / DIR_FIN / DIR_HR) → evidence. It ends with an explicit "five things for others to act on" table.
> No sentence may contain a number that is not in a data row.

---

## 1. Purpose and verbatim trace (V20)
| Verbatim | Stage | Section |
|---|---|---|
| "Can I see the income statement? It should ask me of what year, the present year or the last year" | Year clarification | §3 |
| "display the income statement as you see in Yahoo Finance" | Multi-year statement | §4 |
| "what was the weighted average cost of capital for the past five years or 10 years? Then it should plot it" | WACC chart | §5 |
| "why it was high in this particular year, why it was low" | Variance attribution + grounded why | §6 |
| "if the cost were high in any particular line item, it should identify why … and recommend the next step" | Line-level drivers → levers | §6–§7 |
| "five things that the CMD or the HR or Director Finance would like the other people to act on … over-inventory" | Top-5 actions with owner | §7 |

## 2. Current state
| Item | Status | Evidence |
|---|---|---|
| Year clarification | **Missing** | "give me income statement" → FY26 silently; only statement *type* is clarified (`pipeline.py:211-221`); FY default `normalize.py:6` (diag_A Bugs #6) |
| Multi-year statement | **Partial** | Single-year 23/24-row grid; wrong BS/CF data (diag_A §4) |
| WACC | **Missing** | diag_A §5, BUG-15 |
| "Why" | **Broken (canned)** | Token-overlap over 129 hand-written chunks, `insight_context.py:138-191`; FY17 prev = current placeholder |
| Actions | **Broken (canned)** | One `director_finance_action` string per FY×statement, `insight_context.py:224-233`; `FY_DIRECTOR_ACTIONS` hand-written (`build_and_load_financial_rag.py:24+`) |
| Grounding | **Broken (circular)** | `facts=_extract_nums(rag_txt)` whitelists numbers inside the canned text, `insight_context.py:229,233` (BUG-22 / diag_D B22) |
| Waterfall | **Broken** | Re-plot draws Total ≈ 3× revenue (`turn_runner.py:275-296`, `compat.ts:73`); EBITDA invented as `rev*0.68` (`plan.ts:146`) (BUG-08/09) |
| "Why did revenue fall in FY23" | **Broken** | Hijacked by the asset fast-path regex, `turn_runner.py:2161-2165` (BUG-21) |

## 3. Stage 1: Year clarification (P2F.1)
### 3.1 Trigger
A statement metric (`pnl_statement`, `balance_sheet`, `cash_flow_statement`, or the generic "financial statements") with **no FY in the utterance** and **no FY in the last 3 turns' QuerySpecs**. If the context has an FY (e.g. the previous turn was FY24), Yukti uses it and says so ("Showing FY24, as before. Say 'latest' for FY26").

### 3.2 Contract (v3 addition `clarify`, owner O; mirrors SPEC-03 additive rule)
```json
"clarify": {
  "type": "object", "required": ["question", "options", "slot"],
  "properties": {
    "slot": {"enum": ["fiscal_period", "statement", "scope", "entity"]},
    "question": {"type": "string"},
    "options": {"type": "array", "minItems": 2, "maxItems": 6, "items": {"type": "object", "required": ["label", "value"],
      "properties": {"label": {"type": "string"}, "value": {"type": "string"}, "spoken": {"type": "string"}}}},
    "pending_spec": {"$ref": "#/$defs/query_spec"}
  }
}
```
Options for `fiscal_period` (generated from `v_fin_coverage`, never hard-coded): `FY26 (latest)` → `FY26`; `FY25 (last year)` → `FY25`; `Last 5 years` → `FY22..FY26`; `Last 10 years` → `FY17..FY26`. `visual.type="none"`. `spoken_summary`: "Which year would you like: FY26, FY25, or the last five or ten years?"

### 3.3 Answer resolution (deterministic; text or voice)
| Reply | Resolves to |
|---|---|
| "present year", "this year", "current", "latest", "is saal" | latest FY in coverage (FY26) |
| "last year", "previous year", "pichhle saal" | latest − 1 (FY25) |
| "2025", "FY25", "FY 2024-25", "2024-25" | FY25. A bare year = FY ending 31-Mar of that year; the answer states "FY2024-25 (year ended 31-Mar-2025)". Depends on the BUG-20 fix |
| "five years", "5 saal", "last 5" | FY22..FY26 |
| "ten years", "decade", "10 saal" | FY17..FY26 |
| chip click | its `value` |
| Anything else | Treated as a new question; the pending clarify expires after 1 turn |

## 4. Stage 2: Multi-year Yahoo-style statement (P2F.2; layout spec in SPEC-09)
- **Query:** `v_fin_trend_latest` for 2+ columns, `v_fin_statement_as_reported` for a single FY (SPEC-01 §7.1), `scope='standalone'` by default, `fiscal_year IN (…)`. Columns sorted newest → oldest (Yahoo order). Rows from `dim_financial_line` (`level`, `line_kind`, `line_order`).
- **Visual:** `visual.type="statement"` (SPEC-09): indented hierarchy, bold subtotals/totals, negatives as `(1,234.5)`, ₹ crore with Indian grouping and 1 dp, optional YoY % column for 2-column views, restated `†` markers with footnote, and a per-column source footer ("FY24: AR FY24 p.245").
- **Column count:** 1 (single FY) · 2 (FY + comparative, default for a single-FY request) · 5 · 10. For 10 years, FY17–FY21 use the 10-yr summary lines only. Lines without data show "—" with a footnote "line not disclosed in the 10-year summary". Values are never imputed.
- **Scope switch:** "consolidated" → `scope='consolidated'` FY22–FY26. "Yahoo view" → `v_fin_yahoo_view` FY23–FY26 with the **Yahoo view · Consolidated** badge (SPEC-01 §7.3).
- **Spoken summary (template):** "Here is ONGC's standalone income statement for FY22 to FY26 from the annual reports. Revenue from operations was ₹{rev_latest} crore in FY26, {up/down} {x}% on FY25, and profit after tax was ₹{pat_latest} crore." All values come from the rows.

## 5. Stage 3: WACC 5/10-yr (P2F.3)
Defined in SPEC-02 §5: `wacc_pct` line chart with Ke and Kd(1−t), the **Modelled** badge, and a drill-down to the build-up. Follow-ups "why was it high in FY23" → Shapley attribution (SPEC-02 §5.3).

## 6. Stage 4: Variance attribution and grounded "why" (P2F.4, P2F.5)
### 6.1 Engine (`app/agents/fin_diagnostics/variance.py`, deterministic)
Input: `line_code` (or `PL.PBT`/`PL.PAT` for a full bridge), `fy_to`, `fy_from` (default `fy_to − 1`), scope. Output rows in `variance_attribution` (in-memory; cached per run):

| Column | Type | Notes |
|---|---|---|
| `fy_from`, `fy_to`, `scope`, `line_code` | STRING | |
| `delta_inr_cr` | NUMERIC | `value(fy_to) − value(fy_from)` from verified rows |
| `component` | STRING | `volume` · `price` · `fx` · `price_incl_fx` · `levy_base` · `levy_rate` · `policy_levy` · `unit_cost` · `activity` · `one_off` · `sub_line` · `other_unexplained` |
| `impact_inr_cr` | NUMERIC | Signed effect on the line |
| `impact_on_pbt_inr_cr` | NUMERIC | Signed effect on PBT (costs flip sign) |
| `method` | STRING | Formula id (below) |
| `inputs` | ARRAY<STRUCT<line_code, fy, value, source>> | Every number used |
| `coverage` | STRING | `full` · `partial` (some inputs missing → residual shown) |
| `rank` | INT64 | By |impact_on_pbt| within the request |

**Decomposition methods (applied only when all inputs are verified rows; otherwise the method degrades to `sub_line` or `other_unexplained`, and the answer says so)**
| Line family | Method id | Formula |
|---|---|---|
| Crude / gas revenue | `M-REV-PVF` | Volume = ΔQ × P₀; price (USD) = Q₁ × ΔP × FX₀; FX = Q₁ × P₁ × ΔFX. Needs `fact_production_annual(basis='sold')` and `fact_price_realisation` (§6.4). Without realisation data: `M-REV-PV`, where volume = R₀ × (Q₁/Q₀ − 1) and `price_incl_fx` = remainder |
| Royalty, OIDB cess | `M-LEVY` | Base = ΔBase × rate₀; rate = Δrate × Base₁, where the base = the relevant product sales and rate = line ÷ base |
| Other levies incl. SAED | `M-POLICY` | Whole Δ as `policy_levy`, tagged with the AR chunk that explains the levy change |
| Operating expenses | `M-UNIT` | Activity = Δboe × (opex/boe)₀; unit cost = Δ(opex/boe) × boe₁; then `sub_line` from Note 35 components where extracted |
| Exploration write-offs | `M-SUB` | Survey vs exploratory well costs (10-yr children) |
| DD&A | `M-SUB` | Depletion vs depreciation vs impairment (Note 37 where extracted) |
| Finance costs | `M-SUB` | Decommissioning unwinding vs lease interest vs borrowings (Note 36) |
| Other income | `M-SUB` | Dividend vs other non-operating (10-yr children) |
| Exceptional items, provisions & write-offs, exchange loss | `M-ONEOFF` | Whole Δ as `one_off` |
| Tax | `M-TAX` | Base = ΔPBT × t₀; rate = Δt × PBT₁ |
| PBT/PAT bridge | `M-BRIDGE` | Ordered list of the line deltas above; must close exactly (Σ = ΔPBT within ₹0.1 cr); the visual is a signed waterfall starting at PBT(fy_from) and ending at PBT(fy_to) (fixes BUG-08) |

### 6.2 "Why" answer composition (P2F.5)
1. **Lead (data):** the top 3 drivers by |impact on PBT| with ₹ values and direction. Templated text; numbers inserted from rows.
2. **Evidence (AR text):** `ar_retriever` (SPEC-01 §8.2) with `fiscal_year IN (fy_to)`, `line_codes` = the top drivers, sections mdna > directors_report > notes; top 2–3 chunks. The narrator (LLM) may **paraphrase or quote** them, but every claim carries `[AR FY26 p.98]`.
3. **Unexplained remainder:** if `coverage='partial'`, add the sentence "₹X crore of the change is not explained by disclosed volume/price data."
4. **Visual:** `chart` waterfall (`M-BRIDGE`) or a `table` of components for a single line.
5. `sources[]`: SSOT rows (doc + page) + AR chunks (doc + page).

### 6.3 Grounding rule (fixes BUG-16 / BUG-22)
- Delete the corpus-number whitelist (`insight_context.py:229,233`).
- **Allowed numbers** = values in `variance_attribution.inputs`/`impact` + statement rows in the turn, formatted any standard way (₹ cr, %, lakh crore).
- A number that appears only inside a **verbatim quoted** AR excerpt (in quotation marks, with a page cite) is allowed, and it is rendered as a quote, not a claim.
- Any other number → the sentence is dropped and logged (`grounding_drop`). If more than 1 sentence is dropped, the narrative falls back to the template-only text.
- Delete `financial_notes_corpus.jsonl`, `ssot_financial_line_context.json` and `FY_DIRECTOR_ACTIONS` from runtime (SPEC-01 §11).

### 6.4 Data dependency added to SPEC-01 (P1.3 notes)
`hrfin_gold.fact_price_realisation`: `fiscal_year, product (crude|gas|vap), realisation_usd_per_bbl | usd_per_mmbtu, realisation_inr_per_unit, avg_inr_usd, source_doc, source_page, verified`. These are extracted from the AR Directors' Report / MD&A or the results press releases. If they are absent for an FY, `M-REV-PV` is used.

### 6.5 Worked example from real data (FY26 vs FY25, standalone, ₹ cr; AR FY26 10-yr table, PDF p.23–24)
PBT fell **₹4,344.9 cr** (46,759.8 → 42,414.9). Bridge (impact on PBT):

| Driver | Impact on PBT |
|---|---|
| Revenue from operations | −5,338.2 (crude −5,725.1, of which volume +382.8 and price incl. FX −6,107.9; gas +2,512.1; VAP −2,129.4) |
| Statutory levies | +4,820.4 (other levies incl. SAED +3,969.4; OIDB cess +446.7; royalty +402.9) |
| Exchange loss | −1,931.7 |
| Provisions and write-offs | −1,142.4 |
| DD&A and impairment | −781.4 |
| Operating expenses | −730.1 |
| Other expenses | +710.4 |
| Other income | −123.7 (dividend +1,346.4; other non-operating −1,470.0) |
| Exploration write-offs | +97.0 |
| Finance costs | +74.7 |
| **Σ** | **−4,344.9** ✓ |
PAT fell ₹2,716.3 cr (35,610.3 → 32,894.0) after tax fell ₹1,628.6 cr. Crude volume effect uses quantity sold 18.71 → 18.79 MMT (same table).

## 7. Stage 5: Top-5 action generator (P2F.6)
### 7.1 Lever library (`app/agents/fin_diagnostics/levers.yaml`, authored by O, reviewed by S)
| id | Lever | Trigger (all from verified rows / anchors) | ₹ impact estimate (formula) | Owner | KPI |
|---|---|---|---|---|---|
| L01 | Inventory optimisation (over-inventory) | Inventory days (inventories ÷ (opex/365)) > 5-yr median by ≥ 10% | One-off cash release = (days − median) × opex/365; annual carrying saving = release × WACC | DIR_FIN | Inventory days |
| L02 | Receivables collection | Debtor days (AR ratio) > prior-year or 5-yr median (FY26 32 vs FY25 29) | Release = (days − target) × revenue/365; annual = release × Kd | DIR_FIN | Debtor days |
| L03 | Opex per boe | Opex/boe up > inflation (4%) YoY | (opex/boe − target) × boe, target = prior-year × 1.04 | CMD | Opex ₹/boe |
| L04 | Contract renegotiation (charter hire, contractual services) | Note 35 contract lines up > 5% YoY, or lease additions > ₹2,000 cr | 3–5% of addressable spend (assumption, labelled) | DIR_FIN | Contract ₹/boe |
| L05 | Capex phasing / CWIP ageing | CWIP ÷ capex > 5-yr median; development wells in progress up > 25% | Deferral value = deferred capex × WACC | CMD | CWIP days, capitalisation rate |
| L06 | Exploration efficiency | Exploratory well write-offs > 5-yr average by > 20% | (write-off − 5-yr avg) | CMD | Dry-well cost ₹ cr |
| L07 | Employee cost efficiency | Employee cost per employee or per boe up > 5% (SPEC-04 Employee-360; synthetic, labelled) | Overtime/allowance excess vs median | DIR_HR | Cost/employee, revenue/employee |
| L08 | FX exposure / hedging | Exchange loss > ₹1,000 cr or > 2× prior year | Loss avoided at a 50% hedge ratio (assumption) | DIR_FIN | FX loss ₹ cr |
| L09 | Provisions & write-offs review | Provisions up > 25% YoY | Δ provisions | DIR_FIN | Provisions ₹ cr |
| L10 | Lease portfolio | Lease liabilities > ₹20,000 cr and lease interest up YoY | 1pp rate cut × average lease liability | DIR_FIN | Lease interest ₹ cr |

### 7.2 Selection algorithm
1. Evaluate all triggers for `fy_to` (default = the FY in context).
2. `score = impact_mid_inr_cr × confidence` (confidence: 1.0 when all inputs are verified AR rows; 0.7 when any assumption % is used; 0.5 when synthetic HR data is used).
3. Take the top 5 by score, with **owner diversity**: at most 3 per owner. If the persona is DIR_HR, L07 is always included when it fires.
4. If fewer than 5 fire, return those that fire and say "Only N levers are triggered by FY26 data". No filler.
5. Each action gets 1 AR chunk as evidence when retrieval finds one with distance < 0.35. Otherwise the evidence is data-only.

### 7.3 Output: `visual.type="actions"` (defined here; contract v3 addition, owner O; SPEC-09 adds the renderer) + explicit delegation table
```json
"actions": {"type": "object", "required": ["fy", "items", "delegation_table"], "properties": {
  "fy": {"type": "string"},
  "items": {"type": "array", "maxItems": 5, "items": {"type": "object", "required": ["rank", "lever_id", "title", "what_to_do", "impact", "owner", "kpi", "evidence"],
    "properties": {"rank": {"type": "integer"}, "lever_id": {"type": "string"}, "title": {"type": "string"}, "what_to_do": {"type": "string"},
      "impact": {"type": "object", "properties": {"low": {"type": "number"}, "mid": {"type": "number"}, "high": {"type": "number"}, "unit": {"const": "INR_cr"}, "kind": {"enum": ["one_off", "annual"]}, "label": {"const": "Modelled estimate"}}},
      "owner": {"enum": ["CMD", "DIR_FIN", "DIR_HR"]}, "horizon_days": {"enum": [30, 90, 180]}, "kpi": {"type": "string"},
      "evidence": {"type": "array", "items": {"type": "object", "properties": {"type": {"enum": ["data", "ar"]}, "ref": {"type": "string"}}}},
      "confidence": {"type": "number"}}}},
  "delegation_table": {"type": "array", "items": {"type": "object", "properties": {"owner": {"type": "string"}, "ask": {"type": "string"}, "by_when": {"type": "string"}, "kpi": {"type": "string"}, "evidence": {"type": "string"}}}}
}}
```
Each card: `rank, title, what_to_do (template), impact {low, mid, high, unit, kind: one_off|annual, label: "Modelled estimate"}, owner, horizon (30/90/180 days), kpi, evidence [{type: data|ar, ref}], confidence`.
**"Five things for others to act on"** (always rendered under the cards, exportable as a docx memo via `doc_export_agent`):

| # | Owner | Ask | By when | KPI to report | Evidence |
|---|---|---|---|---|---|
| 1 | DIR_FIN | e.g. "Bring debtor days from 32 back to 29" | 90 days | Debtor days | AR FY26 10-yr ratios p.22 |
| … | … | … | … | … | … |

Follow-up "draft this as a memo to the Directors" → `doc_export_agent` creates a docx/email draft with this table (no sending).

### 7.4 Persona variants
CMD: all owners. DIR_FIN: all owners, own actions first. DIR_HR: HR levers first plus the company top 2. E1–E4_FIN and E1–E4_HR: the analysis and actions without the owner/assignment column ("for discussion"); `fin_internal` detail is aggregated for E1–E4_HR per SPEC-06. `fin_diagnostics_agent` is callable by all 11 personas; masking is done by `enforce_contract` per the SPEC-06 matrix (SPEC-03 §4.2, §8).

## 8. Acceptance criteria
| ID | Criterion |
|---|---|
| AC-01 | "Can I see the income statement?" (no FY, fresh session) → `clarify` with 4 options from coverage; 0 statement rows returned |
| AC-02 | Each of the 12 replies in §3.3 resolves to the expected FY set (unit table) |
| AC-03 | 5-yr statement shows 5 columns FY26…FY22, values equal to SSOT (±₹0.05 cr), with a source footer per column |
| AC-04 | `M-BRIDGE` closes to ΔPBT within ₹0.1 cr for every FY pair FY18–FY26; the FY26-vs-FY25 example in §6.5 is reproduced exactly |
| AC-05 | "Why" answers contain 0 numbers outside the allowed set (grounding test over 20 why-questions); each answer cites ≥ 1 AR page when retrieval returns a chunk |
| AC-06 | "Why did revenue fall in FY23" is answered about FY23 standalone revenue (no Mumbai High/Bassein content) |
| AC-07 | Top-5: every action has ₹ impact, owner ∈ {CMD, DIR_FIN, DIR_HR}, KPI and ≥ 1 evidence item; deterministic (same input → same list) |
| AC-08 | 0 references at runtime to `financial_notes_corpus.jsonl`, `ssot_financial_line_context.json`, `FY_DIRECTOR_ACTIONS` (grep) |

## 9. Test plan
Unit: clarify resolution table; variance methods with fixtures from the AR FY26 10-yr table; bridge closure for all FY pairs; lever triggers with synthetic edge cases; grounding filter (sentences with injected wrong numbers are dropped). Golden eval (SPEC-11): BEH-03 chain values. Voice: chip answers by voice ("last year", "pichhle saal").

## 10. Open questions
1. Lever library ownership: the sponsor reviews the 10 levers and the assumption % (L04 3–5%, L08 50% hedge) before P2F.6 ships?
2. Should "Directors (Onshore/Offshore/Exploration)" be valid owners, or keep the three V20 owners only (recommended: three only, for now)?
3. `fact_price_realisation` coverage FY17–FY21 depends on ARs FY16–FY19 downloads; acceptable to use `M-REV-PV` for those years?

## 11. Status matrix
| Stage | Status |
|---|---|
| Year clarification | Missing |
| Multi-year statement | Partial (single-year grid, wrong data) |
| WACC chart | Missing |
| Variance attribution + bridge | Missing (waterfall broken) |
| Grounded why with AR cites | Broken (canned, circular) |
| Top-5 actions + delegation table | Broken (1 canned action) |
