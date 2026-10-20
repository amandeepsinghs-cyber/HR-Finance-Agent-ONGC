-- Answer Key SQL: P15
-- Question: Did we meet the 2% CSR obligation in FY26? Which states got the most?
-- Type: policy_plus_data
-- Semantic audit 2026-10-20: Old SQL ranked states only and never tested the 2% obligation. Section 135 obligation for FY26 =
-- Semantic audit 2026-10-20: 2% of average net profit (PBT proxy, corporate_financials.pbt_inr_cr) of the three preceding FYs
-- Semantic audit 2026-10-20: (FY23, FY24, FY25). Each state row carries FY26 total spend, obligation and % of obligation.
-- Semantic audit 2026-10-20: Removed the never-matching '2026' fiscal_year alternate.
WITH obligation AS (
    SELECT 0.02 * AVG(pbt_inr_cr) AS obligation_cr, AVG(pbt_inr_cr) AS avg_pbt_3yr_cr
    FROM corporate_financials
    WHERE fiscal_year IN ('FY23', 'FY24', 'FY25')
),
st AS (
    SELECT c.state_code, g.state_name, SUM(c.actual_disbursed_inr_cr) AS spend_cr, COUNT(*) AS projects
    FROM csr_projects c
    LEFT JOIN dim_geography g ON g.state_code = c.state_code
    WHERE c.fiscal_year = 'FY26'
    GROUP BY 1, 2
)
SELECT
    st.state_name,
    st.state_code,
    st.projects,
    ROUND(st.spend_cr, 2) AS csr_spend_cr,
    ROUND(100 * st.spend_cr / SUM(st.spend_cr) OVER (), 1) AS share_of_fy26_spend_pct,
    ROUND(SUM(st.spend_cr) OVER (), 2) AS fy26_total_spend_cr,
    ROUND(o.avg_pbt_3yr_cr, 1) AS avg_net_profit_fy23_fy25_cr,
    ROUND(o.obligation_cr, 1) AS obligation_2pct_cr,
    ROUND(100 * SUM(st.spend_cr) OVER () / o.obligation_cr, 1) AS spend_pct_of_obligation,
    SUM(st.spend_cr) OVER () >= o.obligation_cr AS obligation_met
FROM st, obligation o
ORDER BY csr_spend_cr DESC, state_name;
