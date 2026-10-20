-- Answer Key Follow-up SQL: M4__compare_or_so_what
-- Question: What was the total operating profit (EBITDA) reported by ONGC in the last audited annual financial statements?
-- Type: refusal
-- Semantic audit 2026-10-20: Old SQL returned a single unlabelled EBITDA value.
-- Semantic audit 2026-10-20: Now: last audited year (FY26) with FY25 comparator - revenue, EBITDA, EBITDA margin and PAT from corporate_financials.

SELECT
    fiscal_year,
    gross_revenue_inr_cr,
    ebitda_inr_cr,
    ROUND(ebitda_inr_cr * 100.0 / NULLIF(gross_revenue_inr_cr, 0), 1) AS ebitda_margin_pct,
    pat_inr_cr
FROM corporate_financials
WHERE fiscal_year IN ('FY25', 'FY26')
ORDER BY fiscal_year DESC;
