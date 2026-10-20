-- Answer Key Follow-up SQL: E5__compare_or_so_what
-- Question: How does the offshore boarding and lodging allowance compare with onshore Class-A city travel entitlements?
-- Type: policy
-- Semantic audit 2026-10-20: Added LOWER(cadre) hygiene and the P1-16 Part 38 rule (free board & lodging -> 1/4 DA) as a column so the offshore side of the comparison is in the result.

SELECT
    grade_id,
    designation,
    ta_da_travel_class,
    daily_lodging_limit_cat_a_inr,
    0.25 AS da_fraction_when_free_board_and_lodging
FROM `ongc-hr-finance-agent.hrfin_silver.dim_grade`
WHERE LOWER(cadre) = 'executive'
ORDER BY level_order;
