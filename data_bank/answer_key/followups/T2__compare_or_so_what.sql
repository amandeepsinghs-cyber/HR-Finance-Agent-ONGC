-- Answer Key Follow-up SQL: T2__compare_or_so_what
-- Question: How does transferring these executives balance vacancy deficits in North-East assets while controlling transfer allowance expenses?
-- Type: chain
-- Semantic audit 2026-10-20: Old SQL just counted active executives per work centre (no vacancies, no cost).
-- Semantic audit 2026-10-20: Now: North-East executive vacancies by discipline matched one-for-one with movable Delhi 5yr+ executives, residual gap, and transfer cost at the FY26 average cost per transfer from posting_history.

WITH movable AS (
    SELECT v.discipline_id, COUNT(DISTINCT v.emp_id) AS movable
    FROM `ongc-hr-finance-agent.hrfin_gold.v_continuous_stay` v
WHERE v.is_current_stay AND v.wc_id = 'WC-DEL' AND v.grade_id LIKE 'E%' AND v.continuous_stay_months >= 60
      AND DATE_DIFF(v.retirement_date, DATE '2026-10-19', DAY) > 3 * 365.25
    GROUP BY v.discipline_id
),
ne AS (
    SELECT s.discipline_id, SUM(s.vacancy_count) AS ne_vac
    FROM sanctioned_posts s
    JOIN dim_work_centre w ON w.wc_id = s.wc_id
    WHERE s.fiscal_year = 'FY26' AND LOWER(w.sector) = 'ne' AND LOWER(s.grade_band) != 'non_executive'
    GROUP BY s.discipline_id
    HAVING ne_vac > 0
),
cost AS (
    SELECT AVG(total_transfer_cost_inr) AS avg_cost
    FROM posting_history
    WHERE fiscal_year = 'FY26' AND LOWER(posting_type) IN ('rotation', 'hard_station')
)
SELECT
    ne.discipline_id,
    d.name AS discipline_name,
    ne.ne_vac AS ne_exec_vacancies,
    COALESCE(m.movable, 0) AS delhi_5yr_movable,
    LEAST(ne.ne_vac, COALESCE(m.movable, 0)) AS transferable,
    ne.ne_vac - LEAST(ne.ne_vac, COALESCE(m.movable, 0)) AS residual_vacancies,
    ROUND(LEAST(ne.ne_vac, COALESCE(m.movable, 0)) * cost.avg_cost / 1e7, 2) AS est_transfer_cost_inr_cr,
    ROUND(cost.avg_cost, 0) AS avg_cost_per_transfer_inr
FROM ne
LEFT JOIN movable m ON m.discipline_id = ne.discipline_id
JOIN dim_discipline d ON d.discipline_id = ne.discipline_id
CROSS JOIN cost
ORDER BY transferable DESC, ne_exec_vacancies DESC;
