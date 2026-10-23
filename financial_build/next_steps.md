# Next Steps & Autonomous Execution Roadmap (`next_steps.md`)

This document tracks the end-to-end execution of the **ONGC 10-Year Financial Intelligence & Hybrid Contextual RAG System**, including the **30-Scenario × 4-Turn (120-Turn) Autonomous Verification Suite**, root-cause fixes, and data/context completeness gates.

---

## 1. Completed & Active Build Workstreams

| Workstream | Artifact / Table / Module | Status | Details |
|---|---|---|---|
| **1. 10-Year 3-Statements & Ratios (`FY17–FY26`)** | `ssot_corporate_annual_360` (`10×144`), `ssot_corporate_pnl_lines` (`230`), `ssot_corporate_balance_sheet_lines` (`240`), `ssot_corporate_cash_flow_lines` (`180`), `ssot_corporate_ratios_lines` (`180`) | ✅ Completed | 100% verified across `200 / 200` accounting identity checks (`0.00` discrepancy). |
| **2. Top-Down Sub-Ledger Reconciliation** | `agg_field_pnl_summary` (`530` rows = `53` fields × `10` FYs) & `subsidiary_financials` (`50` rows = `5` subsidiaries × `10` FYs) | ✅ Completed | Exact top-down reconciliation so `SUM(53 fields) == Standalone P&L` and `Standalone + 5 Subsidiaries == Consolidated (ONGC.NS)`. |
| **3. Reference Architecture (`reference_architecture/`)** | `01_hybrid_financial_rag_architecture.md`, `02_data_and_context_schema_spec.md`, `03_retrieval_and_agent_execution_flow.md` | ✅ Completed | 4-Tier Neuro-Symbolic Hybrid Architecture (BigQuery SSOT + Line-Item Context Bridge + `text-embedding-005` Vector RAG + Finance Director Action Engine). |
| **4. Context Reports (`financial_build/context_reports/`)** | `01_FY17_to_FY26_Chronological_MDA_Dossier.md`, `02_Schedule_III_Notes_5_to_37_Context_Catalog.md`, `03_Director_Finance_Action_Playbook.md` | ✅ Completed | Audited Annual Report Note disclosures (`Notes 5–37`), 10-year macro/regulatory chronicle, and quantified Finance Director interventions. |
| **5. Hybrid Context & Vector RAG Tables** | `hrfin_gold.ssot_financial_line_context` (`100` rows) & `hrfin_docs.financial_notes_chunks` (`129` `768-d` embedded chunks) | ✅ Completed | Deterministic foreign-key join on `(fy, statement_type, line_code)` + semantic retrieval over `129` chunks embedded with Vertex AI `text-embedding-005`. |
| **6. Table-First & Waterfall-on-Demand Engine** | `planner.py`, `compiler.py`, `presenter.py`, `insight_context.py`, `narrator.py`, `ui_control.py`, `AnswerCard.tsx` | ✅ Completed | All 4 Financial Statements render `visual.type = "table"` first; Waterfall Chart (`chart.kind = "waterfall"`) renders on demand. |
| **7. Autonomous 120-Turn Stress-Test & Self-Healing Loop** | `financial_build/scripts/run_30x4_stress_test.py` & `05_curated_30_questions_and_followups.md` | ✅ Completed (`120 / 120` PASS — `100.0%`) | Executed 30 root questions + 90 follow-ups across all 6 Pillars; fixed all multi-turn planner, entity-fallback, and grounding edge cases; certified `120 / 120` pass rate. |

---

## 2. Step-by-Step Autonomous Verification & Self-Healing Protocol

1. **Step 1 — Execute 120-Turn Multi-Turn Benchmark (`run_30x4_stress_test.py`):**
   - Tests 30 multi-turn executive conversations (`4` turns each = `120` turns) against live `http://127.0.0.1:8095/api/turn`.
   - Validates:
     - HTTP `200` status & non-empty `spoken_summary`
     - `Table-First` (`visual.type == "table"`) on every Statement request (`pnl_statement`, `balance_sheet`, `cash_flow_statement`, `financial_ratios`)
     - `Waterfall-on-Demand` (`visual.type == "chart"`, `chart.kind == "waterfall"`) on P&L and Cash Flow bridge requests
     - Multi-year (`FY17–FY26`) trend continuity across single metrics and full statements
     - Grounded numbers (`narrator.py`) and presence of **Annual Report Context + Director (Finance) Recommended Actions** (`insight_context.py`).
2. **Step 2 — Inspect Any Failed Turn & Apply Deterministic Root-Cause Fixes:**
   - Any turn in `stress_test_120_turns_results.json` that fails a metric, visual type, chart kind, or row count check is diagnosed and fixed in `planner.py`, `compiler.py`, `presenter.py`, or `insight_context.py`.
3. **Step 3 — Re-Run & Certify 100% Pass Rate (`120 / 120` Turns):**
   - Regenerates `financial_build/05_curated_30_questions_and_followups.md` with the verified questions, SQL shapes, executive briefings, Annual Report Note context, and Finance Director action items.
4. **Step 4 — Hydrate Verified Financial Contracts into Production Startup Cache:**
   - Ensures instant sub-second response times on both `:3200` and `:3300` while maintaining full live LLM + BigQuery + Hybrid RAG execution for arbitrary new follow-ups.
