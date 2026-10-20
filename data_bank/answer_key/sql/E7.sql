-- Answer Key SQL: E7
-- Question: What was ONGC's published annual profit last year? *(public data)*
-- Type: data
-- Semantic audit 2026-10-20: Added fiscal year and prior-year PAT / YoY so 'last year' (FY26) is explicit; value unchanged.

WITH f AS (
    SELECT fiscal_year, pat_inr_cr,
           LAG(pat_inr_cr) OVER (ORDER BY fiscal_year) AS prior_year_pat_inr_cr
    FROM corporate_financials
    WHERE fiscal_year IN ('FY25', 'FY26')
)
SELECT
    fiscal_year,
    pat_inr_cr,
    prior_year_pat_inr_cr,
    ROUND((pat_inr_cr - prior_year_pat_inr_cr) * 100.0 / prior_year_pat_inr_cr, 1) AS yoy_change_pct
FROM f
WHERE fiscal_year = 'FY26';
