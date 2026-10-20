-- Answer Key SQL: P14
-- Question: Our MoU rating sets the performance-related pay pool. What's the pay impact if we drop from "Excellent" to "Very Good"?
-- Type: policy_plus_data
-- Semantic audit 2026-10-20: Old SQL listed MoU parameter targets only (no PRP, no rating scenario). Now applies the DPE 3rd PRC
-- Semantic audit 2026-10-20: PRP formula (G-01 Part 13: MoU component = 50% of PRP; eligibility Excellent 100% / Very Good 75% /
-- Semantic audit 2026-10-20: Good 50% / Fair 25%) to the FY26 executive (E1-E9) PRP outgo in payroll_monthly, holding team (30%)
-- Semantic audit 2026-10-20: and individual (20%) components constant. Assumption: FY26 executive PRP outgo = the Excellent-basis pool.
-- Semantic audit 2026-10-20: FY26 MoU composite score and FY27 projected composite are attached for context.
WITH prp AS (
    SELECT SUM(p.prp_inr) / 1e7 AS exec_prp_cr
    FROM payroll_monthly p
    JOIN dim_grade g ON g.grade_id = p.grade_id
    WHERE p.fiscal_year = 'FY26' AND LOWER(g.cadre) = 'executive'
),
mou AS (
    SELECT MAX(IF(fiscal_year = 'FY26', composite_score, NULL)) AS fy26_composite,
           MAX(IF(fiscal_year = 'FY27', projected_composite_score, NULL)) AS fy27_projected_composite
    FROM mou_targets
)
SELECT
    s.mou_rating,
    s.mou_eligibility_pct,
    0.5 * s.mou_eligibility_pct + 50 AS pool_factor_pct,
    ROUND(prp.exec_prp_cr * (0.5 * s.mou_eligibility_pct + 50) / 100, 1) AS exec_prp_pool_cr,
    ROUND(prp.exec_prp_cr * (0.5 * s.mou_eligibility_pct + 50) / 100 - prp.exec_prp_cr, 1) AS change_vs_excellent_cr,
    ROUND(0.5 * s.mou_eligibility_pct + 50 - 100, 1) AS change_vs_excellent_pct,
    mou.fy26_composite AS fy26_mou_composite_score,
    mou.fy27_projected_composite AS fy27_projected_composite_score
FROM prp, mou, UNNEST([
    STRUCT('Excellent' AS mou_rating, 100 AS mou_eligibility_pct),
    STRUCT('Very Good', 75),
    STRUCT('Good', 50),
    STRUCT('Fair', 25)
]) s
ORDER BY s.mou_eligibility_pct DESC;
