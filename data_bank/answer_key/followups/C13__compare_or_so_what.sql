-- Answer Key Follow-up SQL: C13__compare_or_so_what
-- Question: How would the reduction in Delhi/Dehradun corporate overhead compare against improved field asset uptime and supervisor ratios?
-- Type: what_if
-- Semantic audit 2026-10-20: old SQL selected only literals (200, 6.50, 35878.0) - no data at all. Now:
--   * HQ side (Delhi HQ, Dehradun Tel Bhavan): active executives before/after the move (200 split pro-rata to
--     each office's E3-E5 pool) and the annual FY26 gross payroll of the officers leaving (average E3-E5 gross
--     at that office x movers) - this is overhead re-allocated from HQ to the field, not a company saving;
--   * field side (the parent's receiving assets): non-executives per executive (supervision ratio) before and
--     after adding 200 executives, and the FY26 average operational uptime of those assets.
-- GAP: there is no model linking staffing to uptime, so uptime is the baseline only (no "after" value).

WITH hq AS (
    SELECT e.current_wc_id AS wc_id,
           COUNT(DISTINCT IF(e.current_grade_id LIKE 'E%', e.emp_id, NULL)) AS execs,
           COUNT(DISTINCT IF(e.current_grade_id IN ('E3', 'E4', 'E5'), e.emp_id, NULL)) AS e3_e5
    FROM employee_master e
    WHERE LOWER(e.employment_status) = 'active' AND e.current_wc_id IN ('WC-DEL', 'WC-DDN')
    GROUP BY 1
),
pay AS (
    SELECT wc_id, SUM(gross_salary_inr) / COUNT(DISTINCT emp_id) AS avg_gross_inr
    FROM payroll_monthly
    WHERE fiscal_year = 'FY26' AND grade_id IN ('E3', 'E4', 'E5') AND wc_id IN ('WC-DEL', 'WC-DDN')
    GROUP BY 1
),
hq_rows AS (
    SELECT w.short_name AS scope, 0 AS ord, h.execs,
           CAST(ROUND(200 * h.e3_e5 / SUM(h.e3_e5) OVER ()) AS INT64) AS movers, p.avg_gross_inr
    FROM hq h JOIN pay p USING (wc_id) JOIN dim_work_centre w ON w.wc_id = h.wc_id
),
recv AS (
    SELECT w.wc_id
    FROM sanctioned_posts sp JOIN dim_work_centre w ON w.wc_id = sp.wc_id
    WHERE sp.fiscal_year = 'FY26' AND sp.grade_id LIKE 'E%' AND LOWER(w.type) = 'asset'
    GROUP BY w.wc_id HAVING SUM(sp.vacancy_count) > 0
),
field AS (
    SELECT COUNT(DISTINCT IF(e.current_grade_id LIKE 'E%', e.emp_id, NULL)) AS execs,
           COUNT(DISTINCT IF(e.current_grade_id LIKE 'GRP-%', e.emp_id, NULL)) AS non_execs
    FROM employee_master e JOIN recv r ON r.wc_id = e.current_wc_id
    WHERE LOWER(e.employment_status) = 'active'
),
upt AS (
    SELECT AVG(operational_uptime_pct) AS uptime
    FROM production_monthly pm JOIN recv r ON r.wc_id = pm.asset_wc_id
    WHERE pm.fiscal_year = 'FY26'
)
SELECT scope, executives_before, executives_after, ROUND((executives_after - executives_before) * 100.0 / NULLIF(executives_before, 0), 1) AS exec_change_pct,
       payroll_moved_out_cr, non_exec_per_exec_before, non_exec_per_exec_after, avg_uptime_pct_fy26
FROM (
    SELECT scope, ord, execs AS executives_before, execs - movers AS executives_after,
           ROUND(movers * avg_gross_inr / 1e7, 2) AS payroll_moved_out_cr,
           CAST(NULL AS FLOAT64) AS non_exec_per_exec_before, CAST(NULL AS FLOAT64) AS non_exec_per_exec_after,
           CAST(NULL AS FLOAT64) AS avg_uptime_pct_fy26
    FROM hq_rows
    UNION ALL
    SELECT 'Receiving field assets', 1, f.execs, f.execs + 200, NULL,
           ROUND(f.non_execs / f.execs, 2), ROUND(f.non_execs / (f.execs + 200), 2), ROUND(u.uptime, 2)
    FROM field f CROSS JOIN upt u
)
ORDER BY ord, scope;
