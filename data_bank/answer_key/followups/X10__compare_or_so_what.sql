-- Answer Key Follow-up SQL: X10__compare_or_so_what
-- Question: How do these operational exception indicators compare with the pre-set threshold limits for Executive Committee notification?
-- Type: data
-- Semantic audit 2026-10-20: Old SQL cited BDP Clause 5.0 (CMD powers), which sets no ExCom notification thresholds.
-- GAP: no Executive Committee exception thresholds exist in the data or corpus. Closest honest comparison: each
-- indicator's actual value vs the value claimed in the alert and the only documented norm (JRTP cl.3.2 5-year window;
-- BDP cl.6.1 Rs 100 cr Board-reserved threshold applied to project cost overruns).
WITH proj AS (
    SELECT p.prj_id, d.name AS project_name, d.status AS project_status,
        MAX(p.schedule_slippage_months) AS slippage_months,
        MAX(p.scheduled_completion_date) AS scheduled_completion,
        MAX(p.anticipated_or_actual_completion_date) AS anticipated_completion,
        MAX(p.cost_overrun_inr_cr) AS cost_overrun_cr,
        ANY_VALUE(p.delay_root_cause_category) AS delay_root_cause,
        COUNTIF(LOWER(p.milestone_status) = 'delayed_critical_path') AS critical_path_milestones_delayed
    FROM project_progress p
    JOIN dim_project d ON d.prj_id = p.prj_id
    WHERE p.schedule_slippage_months > 0
    GROUP BY p.prj_id, d.name, d.status
),
exempt AS (
    SELECT emp_id
    FROM posting_history
    WHERE is_current_posting AND NULLIF(exemption_tag, 'None') IS NOT NULL
      AND (exemption_valid_until IS NULL OR exemption_valid_until >= DATE '2026-10-19')
),
overdue AS (
    SELECT v.emp_id, v.wc_id, v.grade_id, v.continuous_stay_months AS months_at_station
    FROM `ongc-hr-finance-agent.hrfin_gold.v_continuous_stay` v
    WHERE v.is_current_stay AND STARTS_WITH(v.grade_id, 'E') AND v.continuous_stay_months >= 60
      AND v.emp_id NOT IN (SELECT emp_id FROM exempt)
      AND DATE_DIFF(v.retirement_date, DATE '2026-10-19', DAY) > 3 * 365.25
),
f AS (
    SELECT field_id, fiscal_year, lifting_cost_per_boe_usd, total_production_boe
    FROM field_pnl_annual
    WHERE LOWER(line_type) = 'field' AND fiscal_year IN ('FY25', 'FY26')
),
lift AS (
    SELECT a.field_id, d.name AS field_name, a.lifting_cost_per_boe_usd AS lifting_fy25_usd_boe,
        b.lifting_cost_per_boe_usd AS lifting_fy26_usd_boe,
        ROUND((b.lifting_cost_per_boe_usd - a.lifting_cost_per_boe_usd) * 100 / a.lifting_cost_per_boe_usd, 1) AS lifting_change_pct
    FROM f a
    JOIN f b ON a.field_id = b.field_id AND a.fiscal_year = 'FY25' AND b.fiscal_year = 'FY26'
    LEFT JOIN dim_field d ON d.field_id = a.field_id
)
SELECT 'Projects slipped' AS indicator, 3.0 AS alert_claimed_value,
    CAST(COUNTIF(LOWER(project_status) != 'completed') AS FLOAT64) AS actual_value,
    'Rs 100 cr overrun (BDP cl.6.1 Board-reserved)' AS documented_norm,
    CAST(COUNTIF(LOWER(project_status) != 'completed' AND cost_overrun_cr > 100) AS FLOAT64) AS actual_breaching_norm
FROM proj
UNION ALL
SELECT 'Rotation cases overdue', 42.0, CAST(COUNT(*) AS FLOAT64),
    '5 years at station (JRTP cl.3.2)', CAST(COUNT(*) AS FLOAT64)
FROM overdue
UNION ALL
SELECT 'Field lifting cost increase (%)', 12.0, MAX(lifting_change_pct),
    'none documented', CAST(COUNTIF(lifting_change_pct >= 12) AS FLOAT64)
FROM lift
ORDER BY indicator;
