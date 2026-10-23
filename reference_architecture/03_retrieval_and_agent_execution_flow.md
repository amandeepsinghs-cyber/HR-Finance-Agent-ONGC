# Retrieval & Agent Execution Flow: Combining Present + 10-Year Historical Numbers with Annual Report Context

## 1. End-to-End Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor DF as Director (Finance) / CMD
    participant UI as Next.js Canvas (:3200 / :3300)
    participant PL as Planner (planner.py)
    participant CM as SQL Compiler (compiler.py)
    participant BQ as BigQuery SSOT (hrfin_gold)
    participant IC as Hybrid Context Engine (insight_context.py)
    participant VR as Vector RAG (hrfin_docs.financial_notes_chunks)
    participant PR as Presenter (presenter.py)

    DF->>UI: "Show ONGC Profit & Loss statement for FY26" (or 10-Yr historical / Balance Sheet / Why query)
    UI->>PL: POST /api/turn (utterance, persona, session_id)
    PL->>PL: Classify Subject (corporate / field_finance / subsidiary_finance)\n& Visual Rule (Table-First for statements; Waterfall on demand)
    PL->>CM: Emit QuerySpec (metric, period FY26 or FY17..FY26, grain, chart_kind)
    par Deterministic SQL Numbers (0 Hallucination)
        CM->>BQ: Execute compiled SQL against ssot_corporate_*_lines or ssot_corporate_annual_360
        BQ-->>CM: Return exact Schedule III rows (amount_cr, prev_amount_cr, yoy_delta_pct, note_ref)
    and Hybrid Context & Action Retrieval
        IC->>BQ: Path A: Deterministic lookup in ssot_financial_line_context by (fy, statement_type, line_code)
        IC->>VR: Path B: Embed query with text-embedding-005 & run Cosine Distance search on financial_notes_chunks
        BQ-->>IC: Return exact Note breakdown, 10-Yr historical context & Director (Finance) Action
        VR-->>IC: Return top-K cited Annual Report Note & MD&A chunks
    end
    CM->>PR: Exact SQL Rows + Computed Subtotals
    IC->>PR: Structured Context + Vector RAG Chunks + Director (Finance) Action Items
    PR->>UI: Return AnswerContract (Table-First visual, Waterfall payload, Contextual Bullets, Action Item, Note Citations, Follow-up Chips)
```

---

## 2. Visual & Analytical Governance Rules

1. **Table-First by Default for Financial Statements:**
   - Any request for a **Profit & Loss Statement**, **Balance Sheet**, **Cash Flow Statement**, or **Financial Ratios Scorecard** renders `visual.type = "table"` with full Schedule III hierarchy, Note references (`Note 5`–`Note 36`), prior-year comparison (`FY25`), YoY change (`₹ Cr` and `%`), and `% of Revenue` / `% of Assets`.
2. **Waterfall Chart Only on Explicit Demand:**
   - When the Finance Director clicks `"Show FY26 P&L Waterfall"` / `"Show FY26 Cash Flow Waterfall"` or asks for a waterfall/bridge chart, Yukti switches `visual.type = "chart"` (`chart.kind = "waterfall"`) while preserving the full Schedule III table below the chart.
3. **10-Year Historical Continuity (`FY17–FY26`):**
   - Every single metric and statement line exists across all 10 years (`FY17–FY26`), enabling instant multi-year trend comparisons (`"Compare Revenue, Statutory Levies, and PAT from FY17 to FY26"`) alongside the chronological Annual Report explanation of each regime shift (`FY20` COVID crash & impairment, `FY22–FY23` post-Ukraine crude spike & SAED windfall tax imposition, `FY25` SAED abolition & OPaL equity restructuring, `FY26` KG-98/2 Cluster-2 ramp-up).
4. **Mandatory Director (Finance) Actionability:**
   - Every financial response surfaces not only *what* changed and *why* (cited to the exact Annual Report Note), but also the **Director (Finance) Recommended Action** from `ssot_financial_line_context`.
