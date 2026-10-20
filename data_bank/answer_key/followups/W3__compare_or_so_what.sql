-- Answer Key Follow-up SQL: W3__compare_or_so_what
-- Question: How does the one-time relocation expenditure compare against the multi-year production gains from enhanced field coverage?
-- Type: what_if
-- Semantic audit 2026-10-20: Old SQL was all literals (200, 6.50, 35878) with no production data.
-- Semantic audit 2026-10-20: Now: one-time cost from posting_history averages vs FY26 net revenue/BOE of the receiving assets (those with executive vacancies) - breakeven production uplift over 1 and 3 years. Actual uplift from coverage is not measurable in the data (GAP).

WITH vac AS (
    SELECT w.wc_id, w.short_name, w.hard_station_cat,
           SUM(s.sanctioned_strength) AS sanc, SUM(s.in_position_strength) AS inpos, SUM(s.vacancy_count) AS vacancies
    FROM dim_work_centre w
    JOIN sanctioned_posts s ON s.wc_id = w.wc_id
    WHERE s.fiscal_year = 'FY26' AND LOWER(s.grade_band) != 'non_executive' AND LOWER(w.type) = 'asset'
    GROUP BY w.wc_id, w.short_name, w.hard_station_cat
),
cost AS (
    SELECT AVG(total_transfer_cost_inr) AS avg_cost
    FROM posting_history
    WHERE fiscal_year = 'FY26' AND LOWER(posting_type) IN ('rotation', 'hard_station')
),
rcv AS (
    SELECT
        COUNT(DISTINCT p.asset_wc_id) AS receiving_assets,
        SUM(p.net_revenue_inr_cr) AS net_rev,
        SUM(p.total_production_boe) AS boe
    FROM field_pnl_annual p
    WHERE p.fiscal_year = 'FY26' AND LOWER(p.line_type) = 'field'
      AND p.asset_wc_id IN (SELECT v.wc_id FROM vac v WHERE v.vacancies > 0)
),
capex AS (
    SELECT total_capex_spent_inr_cr FROM corporate_financials WHERE fiscal_year = 'FY26'
)
SELECT
    200 AS relocated_officers,
    ROUND(200 * cost.avg_cost / 1e7, 2) AS one_time_cost_inr_cr,
    rcv.receiving_assets,
    ROUND(rcv.net_rev, 2) AS receiving_assets_fy26_net_revenue_inr_cr,
    ROUND(rcv.boe / 1e6, 2) AS receiving_assets_fy26_mmboe,
    ROUND(rcv.net_rev * 1e7 / rcv.boe, 0) AS net_revenue_per_boe_inr,
    ROUND(200 * cost.avg_cost / (rcv.net_rev * 1e7 / rcv.boe), 0) AS breakeven_boe_one_year,
    ROUND(200 * cost.avg_cost / 1e7 * 100.0 / rcv.net_rev, 4) AS breakeven_uplift_pct_one_year,
    ROUND(200 * cost.avg_cost / 1e7 * 100.0 / (3 * rcv.net_rev), 4) AS breakeven_uplift_pct_over_3yrs,
    ROUND(200 * cost.avg_cost / 1e7 * 100.0 / capex.total_capex_spent_inr_cr, 4) AS cost_pct_of_fy26_capex
FROM rcv
CROSS JOIN cost
CROSS JOIN capex;
