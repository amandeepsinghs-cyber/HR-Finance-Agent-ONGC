-- Answer Key Follow-up SQL: P15__compare_or_so_what
-- Question: How does our FY26 CSR spend compare with the mandatory 2% average net profit calculation under Section 135 of the Companies Act?
-- Type: policy_plus_data
-- Semantic audit 2026-10-20: Old SQL split spend by operational/aspirational district (did not compute the 2% obligation).
-- Semantic audit 2026-10-20: Now FY22-FY26: obligation = 2% x average PBT of the three preceding FYs (corporate_financials),
-- Semantic audit 2026-10-20: actual CSR disbursed (csr_projects), surplus and spend as % of obligation. FY20-FY21 PBT used for FY22-FY23 bases.
WITH pbt AS (
    SELECT fiscal_year, pbt_inr_cr,
           AVG(pbt_inr_cr) OVER (ORDER BY fiscal_year ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING) AS avg_pbt_prev3,
           COUNT(*) OVER (ORDER BY fiscal_year ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING) AS n_prev
    FROM corporate_financials
),
csr AS (SELECT fiscal_year, SUM(actual_disbursed_inr_cr) AS spend_cr FROM csr_projects GROUP BY 1)
SELECT
    p.fiscal_year,
    ROUND(p.avg_pbt_prev3, 1) AS avg_net_profit_prev3_cr,
    ROUND(0.02 * p.avg_pbt_prev3, 1) AS obligation_2pct_cr,
    ROUND(c.spend_cr, 1) AS csr_spend_cr,
    ROUND(c.spend_cr - 0.02 * p.avg_pbt_prev3, 1) AS surplus_cr,
    ROUND(100 * c.spend_cr / (0.02 * p.avg_pbt_prev3), 1) AS spend_pct_of_obligation
FROM pbt p
JOIN csr c ON c.fiscal_year = p.fiscal_year
WHERE p.n_prev = 3 AND p.fiscal_year BETWEEN 'FY22' AND 'FY26'
ORDER BY p.fiscal_year;
