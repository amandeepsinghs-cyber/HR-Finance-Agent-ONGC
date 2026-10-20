-- Answer Key Follow-up SQL: X1__drill_down
-- Question: What is the ratio of contract workforce to regular employees at Hazira Plant, Uran Plant, and Mumbai High?
-- Type: data
-- Semantic audit 2026-10-20: Ratio at 31-Mar-2026 (same period as parent X1) from contractor and regular headcount; old SQL
-- averaged the stored monthly ratio over FY22-FY27 with no period filter. Adds an all-ONGC benchmark row.
WITH cw AS (
    SELECT wc_id, SUM(contractor_headcount) AS contract_workers_mar26
    FROM contract_workforce WHERE month = '2026-03' GROUP BY wc_id
),
hs AS (
    SELECT wc_id, SUM(headcount) AS regular_employees_mar26
    FROM headcount_snapshot WHERE month = '2026-03' GROUP BY wc_id
),
by_wc AS (
    SELECT w.short_name, w.type AS wc_type, cw.contract_workers_mar26, hs.regular_employees_mar26
    FROM cw JOIN hs USING (wc_id) JOIN dim_work_centre w USING (wc_id)
    WHERE w.wc_id IN ('WC-HAZ', 'WC-URN', 'WC-MUM')
    UNION ALL
    SELECT 'All ONGC (46 work centres)', 'company', SUM(cw.contract_workers_mar26), SUM(hs.regular_employees_mar26)
    FROM cw JOIN hs USING (wc_id)
)
SELECT short_name, wc_type, contract_workers_mar26, regular_employees_mar26,
    ROUND(contract_workers_mar26 / regular_employees_mar26, 2) AS contract_to_regular_ratio
FROM by_wc
ORDER BY contract_to_regular_ratio DESC;
