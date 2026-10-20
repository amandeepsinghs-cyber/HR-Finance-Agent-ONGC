-- Answer Key Follow-up SQL: H8__why
-- Question: Why did executives in high-workload operational assets (Drilling, Offshore Production) achieve fewer training hours than target?
-- Type: data
-- Semantic audit 2026-10-20: old SQL joined training_records to ALL posting_history rows of type 'rotation' (fan-out: each
-- record repeated per historic posting) with no FY filter. Now: FY26 hours per Drilling/Production executive split by current
-- work location (offshore / onshore / corporate), share trained, versus the company executive average.
WITH execs AS (
    -- executives on rolls at FY26 end (31-Mar-2026): active today or separated after FY26
    SELECT e.emp_id, e.discipline_id, e.current_wc_id
    FROM employee_master e
    JOIN dim_grade g ON g.grade_id = e.current_grade_id
    WHERE LOWER(g.cadre) = 'executive'
      AND (LOWER(e.employment_status) = 'active' OR e.separation_date > DATE '2026-03-31')
),
tr AS (
    SELECT emp_id, SUM(training_hours) AS hours
    FROM training_records
    WHERE fiscal_year = 'FY26'
    GROUP BY emp_id
),
base AS (
    SELECT x.*, IFNULL(t.hours, 0) AS hours, t.emp_id IS NOT NULL AS trained
    FROM execs x LEFT JOIN tr t ON t.emp_id = x.emp_id
)
SELECT
    d.name AS discipline,
    w.onshore_offshore AS location_class,
    COUNT(*) AS executives,
    ROUND(COUNTIF(b.trained) * 100.0 / COUNT(*), 1) AS pct_trained,
    ROUND(SUM(b.hours) / COUNT(*), 1) AS hours_per_executive,
    (SELECT ROUND(SUM(hours) / COUNT(*), 1) FROM base) AS company_hours_per_executive
FROM base b
JOIN dim_discipline d ON d.discipline_id = b.discipline_id
JOIN dim_work_centre w ON w.wc_id = b.current_wc_id
WHERE d.name IN ('Drilling', 'Production')
GROUP BY d.name, w.onshore_offshore
ORDER BY hours_per_executive;
