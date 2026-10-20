-- Answer Key Follow-up SQL: X6__why
-- Question: What technical training programmes have been established at ONGC Academy to transition conventional engineers into renewable energy roles?
-- Type: data
-- Semantic audit 2026-10-20: Programme names embed the FY, so the old per-programme COUNT DISTINCT fragmented into 36 rows of 371.
-- Now by delivering institute (ONGC Academy etc.) across FY22-FY27 YTD: completed participants, distinct employees,
-- training days.
SELECT
    REPLACE(institute, '_', ' ') AS institute,
    COUNT(*) AS enrolments,
    COUNTIF(LOWER(completion_status) = 'completed') AS completions,
    COUNT(DISTINCT IF(LOWER(completion_status) = 'completed', emp_id, NULL)) AS distinct_employees_completed,
    SUM(training_days) AS total_training_days,
    MIN(fiscal_year) AS first_fy,
    MAX(fiscal_year) AS latest_fy
FROM training_records
WHERE is_renewable_reskilling
GROUP BY institute
ORDER BY completions DESC;
