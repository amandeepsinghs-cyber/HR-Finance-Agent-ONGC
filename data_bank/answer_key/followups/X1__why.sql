-- Answer Key Follow-up SQL: X1__why
-- Question: Why do processing plants and field installations maintain higher contract labour ratios for support operations?
-- Type: data
-- Semantic audit 2026-10-20: Old SQL cited HR Manual Clause 1.0 (executive designations), which does not address contract labour.
-- Replaced with the data evidence: Mar-2026 contract-to-regular ratio by work-centre type, with core-activity flag counts.
-- GAP: service_category in contract_workforce rotates month to month for every work centre, so a support vs core
-- role split cannot be derived; the policy rationale is not in the document corpus.
WITH cw AS (
    SELECT wc_id, SUM(contractor_headcount) AS contract_workers, LOGICAL_OR(is_core_activity) AS is_core
    FROM contract_workforce WHERE month = '2026-03' GROUP BY wc_id
),
hs AS (
    SELECT wc_id, SUM(headcount) AS regular_employees
    FROM headcount_snapshot WHERE month = '2026-03' GROUP BY wc_id
)
SELECT
    CONCAT(w.type, ' / ', w.onshore_offshore) AS work_centre_segment,
    COUNT(*) AS work_centres,
    COUNTIF(cw.is_core) AS core_activity_work_centres,
    SUM(cw.contract_workers) AS contract_workers_mar26,
    SUM(hs.regular_employees) AS regular_employees_mar26,
    ROUND(SUM(cw.contract_workers) / SUM(hs.regular_employees), 2) AS contract_to_regular_ratio
FROM cw JOIN hs USING (wc_id) JOIN dim_work_centre w USING (wc_id)
GROUP BY work_centre_segment
ORDER BY contract_to_regular_ratio DESC;
