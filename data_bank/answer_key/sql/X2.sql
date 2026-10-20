-- Answer Key SQL: X2
-- Question: Which assets rely most on contract labour for core operations?
-- Type: data
-- Semantic audit 2026-10-20: Core-activity work centres ranked by contract dependency at the latest month (Sep-2026): contractor
-- headcount / regular headcount. Old SQL summed 66 monthly stocks (FY22-FY27, e.g. Bassein 182,761 'contractors')
-- and sorted alphabetically instead of by reliance.
WITH cw AS (
    SELECT wc_id, SUM(contractor_headcount) AS contract_workers, LOGICAL_OR(is_core_activity) AS is_core
    FROM contract_workforce WHERE month = '2026-09' GROUP BY wc_id
),
hs AS (
    SELECT wc_id, SUM(headcount) AS regular_employees
    FROM headcount_snapshot WHERE month = '2026-09' GROUP BY wc_id
)
SELECT
    w.short_name,
    w.type AS wc_type,
    w.onshore_offshore,
    cw.contract_workers AS contract_workers_sep26,
    hs.regular_employees AS regular_employees_sep26,
    ROUND(cw.contract_workers / hs.regular_employees, 2) AS contract_to_regular_ratio,
    ROUND(cw.contract_workers * 100 / (cw.contract_workers + hs.regular_employees), 1) AS contract_share_of_workforce_pct
FROM cw JOIN hs USING (wc_id) JOIN dim_work_centre w USING (wc_id)
WHERE cw.is_core
ORDER BY contract_to_regular_ratio DESC, contract_workers_sep26 DESC;
