-- Probe ID: X10
-- Parent ID: None
-- Answer Type: sql
-- Question: *Unprompted:* "3 projects slipped this week; 42 rotation cases overdue; Field X lifting cost up 12%."
-- Personas: CMD
-- Tables: project_progress, posting_history, field_pnl_annual
-- Drill Dims: 
-- Story IDs: S36
-- Expected Output: table
-- Handcrafted: true
-- Story Target: 3.0 (slipped_project_milestones_count)
-- Expected Range: 2.7 - 3.3 (tolerance: ±10.0%)

WITH p AS (
    SELECT COUNT(DISTINCT prj_id) AS metric_1 FROM project_progress WHERE schedule_slippage_months > 0
),
numbered_postings AS (
    SELECT
        p.emp_id,
        p.wc_id,
        p.from_date,
        p.to_date,
        ROW_NUMBER() OVER (PARTITION BY p.emp_id ORDER BY p.from_date, p.posting_id) -
        ROW_NUMBER() OVER (PARTITION BY p.emp_id, p.wc_id ORDER BY p.from_date, p.posting_id) AS island_id
    FROM posting_history p
),
islands AS (
    SELECT emp_id
    FROM numbered_postings
    GROUP BY emp_id, wc_id, island_id
    HAVING BOOL_OR(to_date IS NULL)
       AND datediff('month', MIN(from_date), DATE '2026-10-19') >= 36
),
h AS (
    SELECT COUNT(DISTINCT emp_id) AS metric_2 FROM islands
),
f AS (
    SELECT AVG(lifting_cost_per_boe_usd) AS metric_3 FROM field_pnl_annual
)
SELECT p.metric_1, h.metric_2, f.metric_3
FROM p, h, f;
