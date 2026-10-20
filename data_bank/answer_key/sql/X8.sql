-- Answer Key SQL: X8
-- Question: How many audit (CAG) objections and right-to-information (RTI) applications are pending, and how old are they?
-- Type: data
-- Semantic audit 2026-10-20: Adds the ageing the question asks for (old SQL returned two counts only). Open CAG paras (status <> closed)
-- by age band from notification date and pending RTI applications by days since receipt, both as of 2026-10-19.
WITH cag AS (
    SELECT DATE_DIFF(DATE '2026-10-19', notification_date, DAY) AS age_days, financial_implication_inr_cr
    FROM cag_paras
    WHERE LOWER(current_status) != 'closed'
),
rti AS (
    SELECT DATE_DIFF(DATE '2026-10-19', received_date, DAY) AS age_days
    FROM rti_applications
    WHERE LOWER(status) LIKE 'pending%'
)
SELECT 'CAG audit paras (open)' AS item,
    CASE WHEN age_days < 365 THEN '1: under 1 year' WHEN age_days < 3 * 365 THEN '2: 1-3 years'
         WHEN age_days < 5 * 365 THEN '3: 3-5 years' ELSE '4: over 5 years' END AS age_band,
    COUNT(*) AS pending_count,
    ROUND(AVG(age_days) / 365.25, 1) AS avg_age_years,
    MAX(age_days) AS oldest_days,
    ROUND(SUM(financial_implication_inr_cr), 1) AS financial_implication_cr
FROM cag GROUP BY age_band
UNION ALL
SELECT 'RTI applications (pending)',
    CASE WHEN age_days <= 30 THEN '1: within 30 days' WHEN age_days <= 90 THEN '2: 31-90 days'
         WHEN age_days <= 365 THEN '3: 91-365 days' ELSE '4: over 1 year' END,
    COUNT(*), ROUND(AVG(age_days) / 365.25, 1), MAX(age_days), NULL
FROM rti GROUP BY 2
ORDER BY item, age_band;
