-- Answer Key Follow-up SQL: C5__compare_or_so_what
-- Question: How does our projected technical specialist loss compare with planned deepwater and HP-HT exploration projects?
-- Type: data
-- Semantic audit 2026-10-20: old SQL counted everyone ever employed (incl. 19,373 separated staff) who turns 60
-- by Mar-2030, by discipline (e.g. Drilling 3,332 vs 640 active retirees), and never looked at projects. Now:
-- ongoing deepwater / HP-HT projects in dim_project (name or notes mention deepwater, ultra-deepwater or
-- high-pressure), each with the active subsurface/drilling specialists (Drilling, Geology, Geophysics,
-- Reservoir, Production, Well Services) at the host work centre and how many of them retire by 31-Mar-2030,
-- plus a company-wide specialist line. GAP: there is no project staffing plan, so host-work-centre strength
-- is the closest proxy for project capability.

WITH spec AS (
    SELECT e.emp_id, e.current_wc_id, e.retirement_date
    FROM employee_master e
    WHERE LOWER(e.employment_status) = 'active'
      AND e.current_grade_id LIKE 'E%'
      AND e.discipline_id IN ('DISC-DRL', 'DISC-GEO', 'DISC-GPS', 'DISC-GPW', 'DISC-RES', 'DISC-PRD', 'DISC-WEL')
),
prj AS (
    SELECT prj_id, name, category, asset_wc_id, sanctioned_cost_inr_cr, actual_or_revised_completion
    FROM dim_project
    WHERE LOWER(status) = 'ongoing'
      AND REGEXP_CONTAINS(LOWER(CONCAT(name, ' ', COALESCE(notes, ''))), r'deepwater|deep water|hp-ht|hpht|high-pressure|high pressure')
)
SELECT
    p.name AS project_or_scope,
    w.short_name AS host_work_centre,
    p.category,
    p.sanctioned_cost_inr_cr,
    p.actual_or_revised_completion AS completion_date,
    COUNT(DISTINCT s.emp_id) AS host_specialists_active,
    COUNT(DISTINCT IF(s.retirement_date <= DATE '2030-03-31', s.emp_id, NULL)) AS host_specialists_retiring_by_fy30,
    ROUND(COUNT(DISTINCT IF(s.retirement_date <= DATE '2030-03-31', s.emp_id, NULL)) * 100.0 / NULLIF(COUNT(DISTINCT s.emp_id), 0), 1) AS pct_retiring
FROM prj p
JOIN dim_work_centre w ON w.wc_id = p.asset_wc_id
LEFT JOIN spec s ON s.current_wc_id = p.asset_wc_id
GROUP BY 1, 2, 3, 4, 5
UNION ALL
SELECT
    'All technical specialists (company)', 'All', NULL, NULL, NULL,
    COUNT(DISTINCT emp_id),
    COUNT(DISTINCT IF(retirement_date <= DATE '2030-03-31', emp_id, NULL)),
    ROUND(COUNT(DISTINCT IF(retirement_date <= DATE '2030-03-31', emp_id, NULL)) * 100.0 / NULLIF(COUNT(DISTINCT emp_id), 0), 1)
FROM spec
ORDER BY sanctioned_cost_inr_cr DESC NULLS LAST;
