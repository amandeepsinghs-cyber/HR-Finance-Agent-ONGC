-- Answer Key Follow-up SQL: X4__compare_or_so_what
-- Question: How does our funded asset coverage ratio under the PRBS trust compare with total actuarial benefit obligations?
-- Type: data
-- Semantic audit 2026-10-20: FY26 plan assets vs obligations per scheme plus an all-schemes total row, and PRBS trust assets as a
-- share of total benefit obligations. Old SQL showed only per-scheme average funded ratios with no total obligation.
WITH s AS (
    SELECT scheme_type AS scheme, actuarial_liability_inr_cr AS l, plan_assets_inr_cr AS a, net_liability_inr_cr AS n
    FROM benefit_liabilities WHERE fiscal_year = 'FY26'
)
SELECT
    COALESCE(scheme, 'All benefit schemes') AS scheme_type,
    SUM(l) AS actuarial_liability_cr,
    SUM(a) AS plan_assets_cr,
    SUM(n) AS net_unfunded_cr,
    ROUND(SUM(a) * 100 / SUM(l), 1) AS funded_ratio_pct,
    ROUND((SELECT a FROM s WHERE LOWER(scheme) = 'prbs pension') * 100 / SUM(l), 1) AS prbs_assets_as_pct_of_obligation
FROM s
GROUP BY ROLLUP (scheme)
ORDER BY scheme IS NULL, actuarial_liability_cr DESC;
