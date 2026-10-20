-- Probe ID: H6
-- Parent ID: None
-- Answer Type: sql_plus_rag
-- Question: Are we compliant with reservation norms (SC/ST/OBC/EWS/PwD) by grade?
-- Personas: Director (HR)
-- Tables: sanctioned_posts, employee_master, dim_grade
-- Drill Dims: sanctioned_posts.grade_id, sanctioned_posts.social_category
-- Story IDs: S16
-- Expected Output: table
-- Handcrafted: false
-- Story Target: 23117.0 (total_regular_headcount)
-- Expected Range: 20805.3 - 25428.7 (tolerance: ±10.0%)

SELECT
    sanctioned_posts.grade_id,
    sanctioned_posts.social_category,
    SUM(sanctioned_posts.in_position_strength) * 100.0 / NULLIF(SUM(sanctioned_posts.sanctioned_strength), 0) AS metric_1
FROM sanctioned_posts
LEFT JOIN employee_master ON employee_master.discipline_id = sanctioned_posts.discipline_id
LEFT JOIN dim_grade ON sanctioned_posts.grade_id = dim_grade.grade_id
WHERE sanctioned_posts.fiscal_year IN ('FY26', '2026')
GROUP BY sanctioned_posts.grade_id, sanctioned_posts.social_category
ORDER BY sanctioned_posts.grade_id
LIMIT 100;
