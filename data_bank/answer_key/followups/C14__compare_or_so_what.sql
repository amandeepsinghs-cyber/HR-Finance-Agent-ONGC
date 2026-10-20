-- Answer Key Follow-up SQL: C14__compare_or_so_what
-- Question: What is the quantified financial payoff of farm-out/PEC versus continued in-house operation over a 5-year outlook?
-- Type: document
-- Semantic audit 2026-10-20: old SQL listed EBITDA of all 53 fields with no payoff figures. Now: the parent's
-- five lowest-PBT FY26 fields with the recorded 5-year PEC/farm-out payoff (projected_pec_farmout_payoff_5yr)
-- against a flat in-house baseline of 5 x FY26 PBT (no decline assumed - an optimistic in-house case), the
-- difference, and a total row. GAP: payoff estimates exist only for fields with a recorded estimate.

WITH b AS (
    SELECT f.name AS field_name, pnl.pbt_inr_cr, pnl.projected_pec_farmout_payoff_5yr_inr_cr AS pec_payoff_5yr
    FROM field_pnl_annual pnl
    JOIN dim_field f ON pnl.field_id = f.field_id
    WHERE pnl.fiscal_year = 'FY26' AND LOWER(pnl.line_type) = 'field'
    ORDER BY pnl.pbt_inr_cr ASC
    LIMIT 5
),
u AS (
    SELECT field_name, 0 AS ord, pbt_inr_cr, pec_payoff_5yr, pbt_inr_cr * 5 AS inhouse_5yr_pbt FROM b
    UNION ALL
    SELECT 'Fields with a PEC estimate (total)', 1, SUM(pbt_inr_cr), SUM(pec_payoff_5yr), SUM(pbt_inr_cr * 5)
    FROM b WHERE pec_payoff_5yr IS NOT NULL
)
SELECT
    field_name,
    ROUND(pbt_inr_cr, 2) AS pbt_fy26_inr_cr,
    ROUND(inhouse_5yr_pbt, 2) AS inhouse_5yr_pbt_flat_inr_cr,
    pec_payoff_5yr AS pec_farmout_payoff_5yr_inr_cr,
    ROUND(pec_payoff_5yr - inhouse_5yr_pbt, 2) AS pec_advantage_5yr_inr_cr
FROM u
ORDER BY ord, pbt_inr_cr;
