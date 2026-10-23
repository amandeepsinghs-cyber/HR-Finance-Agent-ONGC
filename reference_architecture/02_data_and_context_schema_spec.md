# Data & Context Schema Specification (BigQuery SSOT + Context Bridge + Vector RAG)

## 1. BigQuery Dataset Topology (`ongc-hr-finance-agent`)

| Dataset | Table Name | Grain | Rows | Purpose |
|---|---|---|---:|---|
| `hrfin_gold` | `ssot_corporate_annual_360` | `1 row / FY` (`FY17–FY26`) | `10` | Wide 144-column corporate table covering Standalone + Consolidated P&L, Balance Sheet, Cash Flow, Ratios, Production, and Macro benchmarks. |
| `hrfin_gold` | `ssot_corporate_pnl_lines` | `(fy, line_code)` | `230` | Normalized 23-line Schedule III Statement of Profit & Loss (`FY17–FY26`) with `amount_cr`, `prev_amount_cr`, `yoy_delta_cr`, `yoy_delta_pct`, `pct_of_rev`, and `note_ref`. |
| `hrfin_gold` | `ssot_corporate_balance_sheet_lines` | `(fy, line_code)` | `240` | Normalized 24-line Schedule III Balance Sheet (`FY17–FY26`) across Non-Current Assets, Current Assets, Equity, Non-Current Liabilities, and Current Liabilities. |
| `hrfin_gold` | `ssot_corporate_cash_flow_lines` | `(fy, line_code)` | `180` | Normalized 18-line Ind-AS 7 Cash Flow Statement (`FY17–FY26`) with Operating, Investing, Financing bridges and Free Cash Flow (`FCF`). |
| `hrfin_gold` | `ssot_corporate_ratios_lines` | `(fy, line_code)` | `180` | Normalized 18-line Financial Ratios & Credit Scorecard (`FY17–FY26`) across Profitability, Return, Liquidity, Leverage, Working Capital, and Upstream Unit Economics. |
| `hrfin_gold` | `agg_field_pnl_summary` | `(fy, field_code)` | `530` | 53 ONGC oil & gas fields × 10 FYs (`FY17–FY26`) top-down reconciled so `SUM(field) == Standalone Corporate P&L`. |
| `hrfin_silver` | `subsidiary_financials` | `(fy, entity_code)` | `50` | 5 Group entities (`HPCL`, `MRPL`, `OVL`, `OPaL`, `OTPC`) × 10 FYs reconciling Standalone (`₹1,31,492 Cr`) to Consolidated (`₹6,41,890 Cr`). |
| `hrfin_gold` | **`ssot_financial_line_context`** | `(fy, statement_type, line_code)` | `110` | **Deterministic Line-Item Causal Context & Finance Director Action Ledger** covering all 10 years (`FY17–FY26`) and all major statement lines. |
| `hrfin_docs` | **`financial_notes_chunks`** | `chunk_id` | `85` | **768-d `text-embedding-005` Semantic Vector Knowledge Base** indexing Annual Report Notes (Notes 5–37), 10-year MD&A narratives, and Director (Finance) action playbooks. |

---

## 2. Schema of `hrfin_gold.ssot_financial_line_context`

```sql
CREATE TABLE IF NOT EXISTS `ongc-hr-finance-agent.hrfin_gold.ssot_financial_line_context` (
  context_id STRING NOT NULL,
  fy STRING NOT NULL,                      -- 'FY17' .. 'FY26', or 'FY17_FY26'
  statement_type STRING NOT NULL,          -- 'PNL' | 'BALANCE_SHEET' | 'CASH_FLOW' | 'RATIOS' | 'SUBSIDIARY' | 'FIELD_ECON'
  line_code STRING NOT NULL,               -- e.g. 'PAT', 'REV_OPS', 'BS_NON_CURR_INV', 'CF_OPERATING', 'RAT_ROCE'
  line_name STRING NOT NULL,               -- Human-readable Schedule III line item
  note_ref STRING,                         -- e.g. 'Note 24', 'Note 8', 'Note 26', 'Ind-AS 7'
  amount_cr FLOAT64,                       -- Audited amount in ₹ Crore (or ratio value)
  prev_amount_cr FLOAT64,                  -- Prior FY amount in ₹ Crore
  yoy_delta_cr FLOAT64,                    -- YoY absolute change
  yoy_delta_pct FLOAT64,                   -- YoY percentage change
  what_happened_summary STRING NOT NULL,   -- Concise 1-line BLUF of what drove the number
  annual_report_context STRING NOT NULL,   -- Detailed breakdown from ONGC Annual Report Note & MD&A
  historical_10yr_context STRING NOT NULL, -- 10-year FY17–FY26 historical trajectory & structural context
  director_finance_action STRING NOT NULL, -- Concrete financial/operational action for Director (Finance)
  source_citation STRING NOT NULL          -- Audited Annual Report Note & Section reference
);
```

---

## 3. Schema of `hrfin_docs.financial_notes_chunks`

```sql
CREATE TABLE IF NOT EXISTS `ongc-hr-finance-agent.hrfin_docs.financial_notes_chunks` (
  chunk_id STRING NOT NULL,
  fy STRING NOT NULL,                      -- 'FY17' .. 'FY26' or 'FY17_FY26'
  statement_type STRING NOT NULL,          -- 'PNL' | 'BALANCE_SHEET' | 'CASH_FLOW' | 'RATIOS' | 'CONSOLIDATED' | 'FIELD_ECON' | 'CHRONOLOGY'
  note_ref STRING NOT NULL,                -- e.g. 'Note 24', 'Note 8', 'MD&A FY20', 'Action Playbook'
  line_codes ARRAY<STRING>,                -- Linked Schedule III line codes & semantic metric names
  title STRING NOT NULL,
  content STRING NOT NULL,                 -- Full narrative + quantitative bridge + Director Finance action
  source_citation STRING NOT NULL,
  embedding ARRAY<FLOAT64>                 -- 768-d Vertex AI text-embedding-005 vector
);
```
