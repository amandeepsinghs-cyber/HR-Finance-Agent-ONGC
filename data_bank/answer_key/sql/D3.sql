-- Answer Key SQL: D3
-- Question: Who is getting promoted in the next DPC?
-- Type: refusal

SELECT
    grade_id,
    designation,
    typical_residency_years,
    promotion_mode,
    dpc_evaluation_type
FROM `ongc-hr-finance-agent.hrfin_silver.dim_grade`
WHERE LOWER(cadre) = 'executive'
ORDER BY level_order;
