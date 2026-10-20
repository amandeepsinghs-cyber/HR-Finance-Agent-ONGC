-- Answer Key Follow-up SQL: X2__compare_or_so_what
-- Question: How does core contract labour dependency compare between offshore production platforms and corporate office complexes?
-- Type: data
-- Semantic audit 2026-10-20: Offshore production assets vs corporate offices at Sep-2026: contract workers, regular employees,
-- ratio and core-activity flag, by work-centre segment. Old SQL filtered is_core_activity = TRUE, which removed every
-- corporate office (none is core) so the comparison was impossible, and summed 66 monthly stocks.
WITH cw AS (
    SELECT wc_id, SUM(contractor_headcount) AS contract_workers, LOGICAL_OR(is_core_activity) AS is_core
    FROM contract_workforce WHERE month = '2026-09' GROUP BY wc_id
),
hs AS (
    SELECT wc_id, SUM(headcount) AS regular_employees
    FROM headcount_snapshot WHERE month = '2026-09' GROUP BY wc_id
)
SELECT
    CASE
        WHEN LOWER(w.type) = 'asset' AND LOWER(w.onshore_offshore) = 'offshore' THEN 'Offshore production assets'
        WHEN LOWER(w.type) = 'office' THEN 'Corporate offices (HQ + regional)'
        WHEN LOWER(w.type) = 'asset' THEN 'Onshore production assets'
        WHEN LOWER(w.type) = 'plant' THEN 'Processing plants'
        ELSE 'Basins, services and institutes'
    END AS segment,
    COUNT(*) AS work_centres,
    COUNTIF(cw.is_core) AS core_activity_work_centres,
    SUM(cw.contract_workers) AS contract_workers_sep26,
    SUM(hs.regular_employees) AS regular_employees_sep26,
    ROUND(SUM(cw.contract_workers) / SUM(hs.regular_employees), 2) AS contract_to_regular_ratio,
    SUM(IF(cw.is_core, cw.contract_workers, 0)) AS core_activity_contract_workers_sep26
FROM cw JOIN hs USING (wc_id) JOIN dim_work_centre w USING (wc_id)
GROUP BY segment
ORDER BY contract_to_regular_ratio DESC;
