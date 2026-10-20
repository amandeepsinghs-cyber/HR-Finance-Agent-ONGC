-- Answer Key SQL: X6
-- Question: How much capex went to ONGC Green / renewables vs. the Net Zero 2038 path, and how many people have been reskilled?
-- Type: data
-- Semantic audit 2026-10-20: Answers all three parts: green capex per FY (FY22-FY26) with running cumulative (sum of annual_capex -
-- the stored cumulative_capex column does not reconcile), share of company capex, MW installed, roadmap milestone
-- flag, and distinct employees completing renewable reskilling (counted once, at first completion). Old SQL showed FY26 by technology only, no reskilling.
-- GAP: no Net Zero 2038 spend trajectory exists in the data; only a boolean milestone flag.
WITH g AS (
    SELECT fiscal_year,
        SUM(annual_capex_inr_cr) AS green_capex_cr,
        SUM(installed_capacity_mw) AS installed_mw,
        LOGICAL_AND(net_zero_2038_roadmap_milestone_met) AS all_roadmap_milestones_met
    FROM energy_transition
    GROUP BY fiscal_year
),
first_completion AS (
    SELECT emp_id, MIN(fiscal_year) AS first_fy
    FROM training_records
    WHERE is_renewable_reskilling AND LOWER(completion_status) = 'completed'
    GROUP BY emp_id
),
r AS (
    SELECT first_fy AS fiscal_year, COUNT(*) AS employees_newly_reskilled
    FROM first_completion
    GROUP BY first_fy
)
SELECT
    g.fiscal_year,
    ROUND(g.green_capex_cr, 1) AS green_capex_cr,
    ROUND(SUM(g.green_capex_cr) OVER (ORDER BY g.fiscal_year), 1) AS cumulative_green_capex_cr,
    c.total_capex_spent_inr_cr AS company_capex_cr,
    ROUND(g.green_capex_cr * 100 / c.total_capex_spent_inr_cr, 1) AS green_share_of_capex_pct,
    g.installed_mw,
    g.all_roadmap_milestones_met,
    r.employees_newly_reskilled,
    SUM(r.employees_newly_reskilled) OVER (ORDER BY g.fiscal_year) AS cumulative_distinct_employees_reskilled
FROM g
JOIN corporate_financials c ON c.fiscal_year = g.fiscal_year
LEFT JOIN r ON r.fiscal_year = g.fiscal_year
ORDER BY g.fiscal_year;
