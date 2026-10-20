-- Answer Key SQL: X10
-- Question: *Unprompted:* "3 projects slipped this week; 42 rotation cases overdue; Field X lifting cost up 12%."
-- Type: data
-- Semantic audit 2026-10-20: Each alert component is now computed from its proper source: (1) open capital projects behind schedule
-- (project grain, not milestone rows); (2) executives past the JRTP cl.3.2 5-year rotation window at their current
-- station per hrfin_gold.v_continuous_stay (>=60 months), excluding valid exemption tags and officers within 3 years of
-- superannuation (same rule as C1/H10) (old: anyone incl. non-executives with >=36 months -> 20,488); (3) largest field-level YoY change in
-- lifting cost FY26 vs FY25 on line_type='field' (old: AVG over all line types and years = 68,922,047 USD/BOE).
-- GAP: no weekly project or cost data exists, so 'this week' cannot be evaluated.
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
SELECT '1: Capital projects behind schedule (open)' AS indicator,
    CAST(COUNTIF(LOWER(project_status) != 'completed') AS FLOAT64) AS value,
    CONCAT('max slippage ', CAST(MAX(IF(LOWER(project_status) != 'completed', slippage_months, NULL)) AS STRING), ' months; ',
           CAST(COUNT(*) AS STRING), ' projects incl. completed ones with slippage') AS detail
FROM proj
UNION ALL
SELECT '2: Executives overdue for rotation (>=5 yrs at station, non-exempt, >3 yrs to retirement)',
    CAST(COUNT(*) AS FLOAT64),
    CONCAT('of ', CAST((SELECT COUNTIF(is_current_posting AND STARTS_WITH(grade_id, 'E')) FROM posting_history) AS STRING),
           ' executives in current postings; median ', CAST(APPROX_QUANTILES(months_at_station, 2)[OFFSET(1)] AS STRING), ' months at station')
FROM overdue
UNION ALL
SELECT '3: Largest field lifting-cost increase FY26 vs FY25 (%)',
    MAX(lifting_change_pct),
    CONCAT(ARRAY_AGG(field_name ORDER BY lifting_change_pct DESC LIMIT 1)[OFFSET(0)], '; fields up >=12%: ',
           CAST(COUNTIF(lifting_change_pct >= 12) AS STRING), ' of ', CAST(COUNT(*) AS STRING))
FROM lift
ORDER BY indicator;
