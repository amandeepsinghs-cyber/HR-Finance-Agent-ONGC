-- Answer Key SQL: W3
-- Question: If we move 200 executives from Delhi/Dehradun to field assets, what happens to transfer-grant cost and asset coverage?
-- Type: what_if
-- Semantic audit 2026-10-20: Old SQL hard-coded 200 officers and Rs 6.50 cr, summed vacancies across all cadres (incl. non-executive) for 4 hand-picked work centres (Assam actually has 0 executive vacancies).
-- Semantic audit 2026-10-20: Now: 200 movers allocated pro-rata to FY26 executive vacancies across the 14 operating assets; coverage before/after; cost at the FY26 average cost per transfer from posting_history; movable Delhi+Dehradun pool for feasibility.

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
pool AS (
    SELECT COUNT(DISTINCT v.emp_id) AS movable_pool
    FROM `ongc-hr-finance-agent.hrfin_gold.v_continuous_stay` v
    WHERE v.is_current_stay AND v.wc_id IN ('WC-DEL', 'WC-DDN') AND v.grade_id LIKE 'E%'
      AND v.continuous_stay_months >= 36
      AND DATE_DIFF(v.retirement_date, DATE '2026-10-19', DAY) > 3 * 365.25
),
a1 AS (
    SELECT *, 200.0 * vacancies / SUM(vacancies) OVER () AS raw_alloc FROM vac
),
a2 AS (
    SELECT *, CAST(FLOOR(raw_alloc) AS INT64) AS base_alloc, raw_alloc - FLOOR(raw_alloc) AS frac FROM a1
),
a3 AS (
    SELECT *,
           base_alloc + IF(ROW_NUMBER() OVER (ORDER BY frac DESC, vacancies DESC) <= 200 - SUM(base_alloc) OVER (), 1, 0) AS allocated
    FROM a2
)
SELECT
    a3.short_name AS field_asset,
    a3.hard_station_cat,
    a3.sanc AS exec_sanctioned,
    a3.inpos AS exec_in_position,
    a3.vacancies AS exec_vacancies,
    ROUND(a3.inpos * 100.0 / a3.sanc, 1) AS coverage_pct_now,
    LEAST(a3.allocated, a3.vacancies) AS officers_allocated,
    ROUND((a3.inpos + LEAST(a3.allocated, a3.vacancies)) * 100.0 / a3.sanc, 1) AS coverage_pct_after,
    a3.vacancies - LEAST(a3.allocated, a3.vacancies) AS vacancies_after,
    ROUND(LEAST(a3.allocated, a3.vacancies) * cost.avg_cost / 1e7, 2) AS transfer_cost_inr_cr,
    ROUND(cost.avg_cost, 0) AS avg_cost_per_transfer_inr,
    pool.movable_pool AS delhi_ddn_movable_pool
FROM a3
CROSS JOIN cost
CROSS JOIN pool
ORDER BY exec_vacancies DESC, field_asset;
