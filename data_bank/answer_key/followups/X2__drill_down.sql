-- Answer Key Follow-up SQL: X2__drill_down
-- Question: Which production installations in Gujarat and Assam employ contract personnel in drilling or hydrocarbon processing roles?
-- Type: data
-- Semantic audit 2026-10-20: Installation-level (not state x discipline) view for Gujarat and Assam assets/plants: FY26 contract
-- person-months deployed under drilling_operations / hydrocarbon_processing service contracts, and the average monthly
-- headcount this implies. Old SQL summed all core contract headcount over 66 months by state and dim_discipline.
-- Caveat: service_category rotates month to month per work centre (data defect), so these are contract-month allocations.
SELECT
    w.state,
    w.short_name,
    w.type AS wc_type,
    LOGICAL_OR(c.is_core_activity) AS is_core_activity,
    COUNTIF(LOWER(c.service_category) = 'drilling_operations') AS drilling_contract_months_fy26,
    COUNTIF(LOWER(c.service_category) = 'hydrocarbon_processing') AS processing_contract_months_fy26,
    SUM(IF(LOWER(c.service_category) = 'drilling_operations', c.contractor_headcount, 0)) AS drilling_person_months_fy26,
    SUM(IF(LOWER(c.service_category) = 'hydrocarbon_processing', c.contractor_headcount, 0)) AS processing_person_months_fy26,
    ROUND(SUM(IF(LOWER(c.service_category) IN ('drilling_operations', 'hydrocarbon_processing'), c.contractor_headcount, 0)) / 12, 0)
        AS avg_monthly_drilling_processing_contract_workers
FROM contract_workforce c
JOIN dim_work_centre w ON w.wc_id = c.wc_id
WHERE c.fiscal_year = 'FY26' AND w.state IN ('Gujarat', 'Assam') AND LOWER(w.type) IN ('asset', 'plant')
GROUP BY w.state, w.short_name, w.type
ORDER BY avg_monthly_drilling_processing_contract_workers DESC, w.short_name;
