# Data Gap Analysis: CMD Named Employee Roster & Transfer Actionability

**Location**: `feature_list_and_verbatims/feature_list/data_gap_analysis_employee_roster.md`  
**Linked Feature**: [`FEAT-006`](./feature_list.md#feat-006-cmd-actionable-employee-level-roster-drilldown-from-aggregates)  
**Linked Verbatim**: [`Verbatim 13`](../verbatims/verbatim_13_named_employee_roster.md)  
**Audit Date**: October 22, 2026

---

## Executive Summary

The synthetic data foundation **already contains realistic employee names and postings**, but the pipeline and UI currently only aggregate these into high-level counts. To fulfill the CMD's requirement to see individual names, seniority, and tenures, we must bridge three specific layers: a BigQuery station tenure join, a roster answer fixture/query, and an actionable drilldown table in the frontend.

---

## 1. What Exists Today (Verified in Data Bank)

* **Synthetic Names**: `data_bank/generators/hr/gen_21_hr_core.py` generates all 23,117 employees with realistic first/last names (e.g. *Suresh Patel, Pooja Verma, Rajesh Kulkarni*).
* **Landing CSVs**: `data_bank/landing/sap/PA0002_PA0001.csv` stores `PERNR`, `name`, `current_designation`, `PERSK` (Grade), and `total_tenure_years`.
* **Posting Records**: `data_bank/landing/sap/PA0001.csv` stores historical and current station postings (`WERKS = 'WC-DEL'`, `tenure_months`, `is_current_posting = True`).

---

## 2. Identified Data & Pipeline Gaps

| # | Layer | Current Gap | Required Action |
| :- | :--- | :--- | :--- |
| **G-1** | **BigQuery SQL / Gold Layer** | Gold models only expose pre-aggregated count slices (e.g. `count(*) by grade, discipline`) used for donut charts. | Create a view `gold.hr_station_tenure_roster` joining `PA0002` (names, grade, total tenure) with `PA0001` (station tenure months at `WC-DEL`). |
| **G-2** | **Continuous Station Tenure Metric** | Station tenure in `PA0001` is stored in individual posting segments. | Calculate cumulative continuous tenure at the current work center (`WC-DEL`) in years (`ROUND(tenure_months / 12, 1)`). |
| **G-3** | **Mock Router & Fixtures** | Frontend `mockRouter.ts` maps any Delhi tenure query exclusively to `c1_donut.json` (pie chart with 419 executives). | Add fixture `c1_delhi_roster_table.json` containing the top 50–100 individual records, and route *"give me their names / list of people"* queries to this table contract. |
| **G-4** | **RBAC Filter Masking** | Backend agent returns raw SQL results without per-column persona masking. | Enforce column-level masking in `yukti/backend/app/turn_runner.py`: if `persona not in ['CMD', 'Director (HR)']`, replace `name` with `"[REDACTED - PRIVACY POLICY]"`. |
| **G-5** | **UI Action Triggers** | `TableRenderer.tsx` is read-only. | Add row selection checkboxes with an executive action bar: `[Draft Transfer Memo (N selected)]` and `[Export to Excel]`. |

---

## 3. Required Data Schema for the CMD Roster

```sql
SELECT 
  emp.PERNR AS emp_id,
  emp.name AS full_name,
  emp.current_designation AS designation,
  emp.PERSK AS grade,                 -- E1, E2, E3, E4, E5, E6, etc.
  disc.discipline_name AS discipline, -- Production, Drilling, HR, Finance, IT
  ROUND(emp.total_tenure_years, 1) AS ongc_tenure_years,
  ROUND(post.tenure_months / 12.0, 1) AS delhi_tenure_years,
  emp.category,
  post.order_no AS last_posting_order
FROM `ongc-hr-finance-agent.hrfin_gold.dim_employee` emp
JOIN `ongc-hr-finance-agent.hrfin_gold.fct_posting` post 
  ON emp.PERNR = post.PERNR 
  AND post.is_current_posting = TRUE
  AND post.WERKS = 'WC-DEL'
WHERE (post.tenure_months / 12.0) >= 5.0
ORDER BY delhi_tenure_years DESC, grade DESC;
```
