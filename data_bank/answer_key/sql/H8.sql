-- Answer Key SQL: H8
-- Question: What were training hours per executive last year, and which disciplines are below target?
-- Type: data
-- Semantic audit 2026-10-20: old SQL averaged hours per training RECORD for all employees (incl. non-executives) and defined
-- no target. Now: FY26 (last full FY) training hours per executive on rolls at 31-Mar-2026 (untrained executives count as 0),
-- per trained executive (MET-HR-037) and a below-company-average flag. No discipline-level training target exists in the
-- data (GAP), so the company executive average is the benchmark.
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
    COUNT(*) AS executives,
    COUNTIF(b.trained) AS trained_executives,
    ROUND(SUM(b.hours), 1) AS total_hours,
    ROUND(SUM(b.hours) / COUNT(*), 1) AS hours_per_executive,
    ROUND(SUM(b.hours) / NULLIF(COUNTIF(b.trained), 0), 1) AS hours_per_trained_executive,
    ROUND(SUM(SUM(b.hours)) OVER () / SUM(COUNT(*)) OVER (), 1) AS company_hours_per_executive,
    SUM(b.hours) / COUNT(*) < SUM(SUM(b.hours)) OVER () / SUM(COUNT(*)) OVER () AS below_company_average
FROM base b
JOIN dim_discipline d ON d.discipline_id = b.discipline_id
GROUP BY d.name
ORDER BY hours_per_executive;
