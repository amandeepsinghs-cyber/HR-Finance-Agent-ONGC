-- Answer Key Follow-up SQL: D4__compare_or_so_what
-- Question: What were ONGC's total standalone capex spend and revenue reported in the last audited financial year?
-- Type: refusal
-- Semantic audit 2026-10-20: Added fiscal_year and capex-to-revenue ratio; removed dead '2026' alternate. Values unchanged.

SELECT
    fiscal_year,
    gross_revenue_inr_cr,
    total_capex_spent_inr_cr,
    ROUND(total_capex_spent_inr_cr * 100.0 / gross_revenue_inr_cr, 1) AS capex_to_revenue_pct
FROM corporate_financials
WHERE fiscal_year = 'FY26';
