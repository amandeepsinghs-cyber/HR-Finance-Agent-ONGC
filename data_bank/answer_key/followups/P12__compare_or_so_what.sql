-- Answer Key Follow-up SQL: P12__compare_or_so_what
-- Question: How does the promotion clearance rate compare between officers who fulfilled the hardship criteria versus those with waivers?
-- Type: policy_plus_data
-- Semantic audit 2026-10-20: Old SQL mixed every grade's DPC cases since FY01 and tested "any Cat-C posting ever" (even after
-- Semantic audit 2026-10-20: the DPC). Now E4->E5 cases FY22-FY27, Cat-C (hard/NE) service counted only before each case's due_date.
-- Semantic audit 2026-10-20: GAP: no hardship waiver is recorded anywhere (posting_history/employee_master exemption tags only hold
-- Semantic audit 2026-10-20: Impending_Retirement), so officers short of the 3-year norm are the closest proxy for "waived".
WITH c AS (
    SELECT d.dpc_id, d.emp_id, d.status,
        SUM(IF(UPPER(w.hard_station_cat) = 'C' AND p.from_date < d.due_date,
               DATE_DIFF(LEAST(COALESCE(p.to_date, DATE '2026-10-19'), d.due_date), p.from_date, DAY), 0)) AS c_days
    FROM dpc_cases d
    LEFT JOIN posting_history p ON p.emp_id = d.emp_id
    LEFT JOIN dim_work_centre w ON w.wc_id = p.wc_id
    WHERE d.from_grade_id = 'E4' AND d.to_grade_id = 'E5' AND d.fiscal_year BETWEEN 'FY22' AND 'FY27'
    GROUP BY 1, 2, 3
)
SELECT
    CASE WHEN c_days >= 1095 THEN 'Met 3-yr hard/NE norm'
         WHEN c_days > 0 THEN 'Some hard/NE service (<3 yrs)'
         ELSE 'No hard/NE posting' END AS hardship_status,
    COUNT(*) AS e4_e5_cases,
    COUNTIF(LOWER(status) = 'completed') AS cleared,
    COUNTIF(LOWER(status) = 'delayed') AS pending_delayed,
    ROUND(100 * COUNTIF(LOWER(status) = 'completed') / COUNT(*), 1) AS clearance_rate_pct
FROM c
GROUP BY 1
ORDER BY MIN(c_days) DESC;
