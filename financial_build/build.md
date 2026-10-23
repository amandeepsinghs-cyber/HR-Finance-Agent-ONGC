# Step-by-Step Build Plan (`build.md`) — ONGC 10-Year Financial Intelligence & Hybrid Contextual RAG Database

This master build plan (`financial_build/build.md`) defines the end-to-end execution stages to construct, verify, and serve ONGC's 10-year (`FY17–FY26`) financial statements, historical context reports, line-item causal knowledge graph, and Director (Finance) action engine.

---

## Stage 1: 10-Year Historical + Present Financial Dataset Construction (`FY17–FY26`) — [COMPLETED]
- **Script:** `financial_build/scripts/build_10yr_financials.py`
- **Inputs:** ONGC Audited Annual Reports (`FY17–FY26`, Schedule III Standalone + Notes 5–37) & Yahoo Finance (`ONGC.NS` Consolidated Filings).
- **Outputs Generated in `financial_build/data/`:**
  1. `ongc_10yr_corporate_wide.json` (`10` FY rows × `144` columns — Standalone + Consolidated P&L, Balance Sheet, Cash Flow, Ratios, Production, Macro).
  2. `ongc_10yr_schedule_iii_lines.json` (`230` rows = `23` Schedule III P&L lines × `10` FYs).
  3. `ongc_10yr_balance_sheet_lines.json` (`240` rows = `24` Schedule III Balance Sheet lines × `10` FYs).
  4. `ongc_10yr_cash_flow_lines.json` (`180` rows = `18` Ind-AS 7 Cash Flow lines × `10` FYs).
  5. `ongc_10yr_ratios_lines.json` (`180` rows = `18` Financial Ratios & Unit Economics lines × `10` FYs).

---

## Stage 2: Automated 200-Check Accounting Identity Gate (`FY17–FY26`) — [COMPLETED]
- **Script:** `financial_build/scripts/verify_pnl_identities.py`
- **Verification Scope:** `20` mathematical identities × `10` fiscal years = **`200` checks** across P&L (`Gross Revenue + Other Income = Total Income`, `Total Income - Total Expenses = PBT`, `PBT - Tax = PAT`, `EBITDA` bridge), Balance Sheet (`Total Assets == Total Equity + Total Liabilities`, `Net Debt == Total Borrowings - Cash`), and Cash Flow (`OCF - Capex == FCF`).
- **Result:** `200 / 200 PASSED WITH 0.00 CRORE DISCREPANCY`.

---

## Stage 3: BigQuery SSOT Loading & Top-Down Sub-Ledger Reconciliation — [COMPLETED]
- **Script:** `financial_build/scripts/load_and_reconcile_bq.py`
- **Tables Loaded in `ongc-hr-finance-agent`:**
  1. `hrfin_silver.corporate_financials` & `hrfin_gold.ssot_corporate_annual_360` (`10` rows × `144` cols)
  2. `hrfin_gold.ssot_corporate_pnl_lines` (`230` rows)
  3. `hrfin_gold.ssot_corporate_balance_sheet_lines` (`240` rows)
  4. `hrfin_gold.ssot_corporate_cash_flow_lines` (`180` rows)
  5. `hrfin_gold.ssot_corporate_ratios_lines` (`180` rows)
  6. `hrfin_gold.agg_field_pnl_summary` & `hrfin_gold.ssot_field_economics_360` (`530` rows = `53` fields × `10` FYs, top-down scaled so `SUM(field) == Corporate Standalone P&L`)
  7. `hrfin_silver.subsidiary_financials` (`50` rows = `5` subsidiaries × `10` FYs, reconciled to Consolidated Revenue `₹6,41,890 Cr` & PAT `₹36,240 Cr`).

---

## Stage 4: Context Reports, Line-Item Context Bridge (`ssot_financial_line_context`) & Vector Knowledge RAG (`financial_notes_chunks`) — [COMPLETED]
- **Architecture Folder:** `reference_architecture/` & `financial_build/reference_architecture/`
- **Persisted Markdown Context Reports (`financial_build/context_reports/`):**
  1. `01_FY17_to_FY26_Chronological_MDA_Dossier.md` — Complete 10-year historical & present MD&A chronicle (`FY17–FY26`).
  2. `02_Schedule_III_Notes_5_to_37_Context_Catalog.md` — Audited Schedule III Note disclosures (`Notes 5–37`) across Balance Sheet, P&L, and Cash Flow.
  3. `03_Director_Finance_Action_Playbook.md` — Quantified Finance Director interventions mapped to each variance trigger.
- **Script:** `financial_build/scripts/build_and_load_financial_rag.py`
- **BigQuery Context & Vector Tables:**
  1. `hrfin_gold.ssot_financial_line_context` (`100` rows keyed by `(fy, statement_type, line_code, note_ref)` across `FY17–FY26` with `what_happened_summary`, `annual_report_context`, `historical_10yr_context`, and `director_finance_action`).
  2. `hrfin_docs.financial_notes_chunks` (`129` rich narrative + quantitative bridge chunks across all 10 years `FY17–FY26`, Notes 5–37, and Director Finance actions, embedded with `768-d` Vertex AI `text-embedding-005`).

---

## Stage 5: Hybrid Retrieval & Table-First / Waterfall-on-Demand Engine Integration — [COMPLETED]
- **Backend Modules (`yukti/backend/app/brain/`):**
  - `semantic_model.yaml`, `planner.py`, `compiler.py`, `presenter.py`, `insight_context.py`, `narrator.py`, `drilldowns.py`, `ui_control.py`, `pipeline.py`.
  - **Table-First Visual Rule:** Queries for `pnl_statement`, `balance_sheet`, `cash_flow_statement`, or `financial_ratios` render `visual.type = "table"` by default; Waterfall Chart (`chart.kind = "waterfall"`) renders on demand.
  - **Hybrid Context Enrichment (`insight_context.py` + `presenter.py`):** Queries both `hrfin_gold.ssot_financial_line_context` (deterministic key lookup on `fy`, `statement_type`, `line_code`) and `hrfin_docs.financial_notes_chunks` (`text-embedding-005` Cosine Vector Search) so every single-year or 10-year historical response includes the exact **Annual Report Context (`what_happened_summary`)** and **Director (Finance) Action Recommendation (`director_finance_action`)**.
- **Frontend (`yukti/frontend/src/components/AnswerCard.tsx`):**
  - Renders indented Schedule III hierarchy, Note references, YoY deltas, `% of Revenue`, on-demand Waterfall bridges, and contextual Executive Briefings with citations.

---

## Stage 6: Autonomous 30-Scenario × 4-Turn (120-Turn) Verification & Self-Healing — [COMPLETED: 120 / 120 PASS (100.0%)]
- **Script:** `financial_build/scripts/run_30x4_stress_test.py`
- **Curated Catalog:** `financial_build/05_curated_30_questions_and_followups.md` & `financial_build/data/stress_test_120_turns_results.json`
- **Result:** `120 / 120` conversational turns (`30` root questions + `90` multi-turn follow-ups across all 6 Financial & HR Pillars) verified end-to-end against live Gemini 2.5 Flash + BigQuery SSOT + Hybrid Contextual Vector RAG (`100.0%` pass rate).
