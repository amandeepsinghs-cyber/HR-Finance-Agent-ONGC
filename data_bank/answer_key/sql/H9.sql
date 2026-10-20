-- Answer Key SQL: H9
-- Question: How many grievances and service litigations are pending, and how old are they?
-- Type: data
-- Semantic audit 2026-10-20: old SQL counted only status 'pending' (68 'stayed' cases are also undisposed/sub judice) and gave
-- no age profile or case-type split. Now: open = pending + stayed, by case type, with ageing computed from filing_date as of
-- 2026-10-19; 11 cases carry filing dates AFTER 2026-10-19 (data defect) and are counted separately, excluded from ages.
WITH open_cases AS (
    SELECT case_type, LOWER(status) AS status, filing_date,
           DATE_DIFF(DATE '2026-10-19', filing_date, DAY) AS age_days_asof
    FROM grievances_litigation
    WHERE LOWER(status) IN ('pending', 'stayed')
)
SELECT
    case_type,
    COUNT(*) AS open_cases,
    COUNTIF(status = 'stayed') AS of_which_stayed,
    COUNTIF(age_days_asof BETWEEN 0 AND 364) AS aged_under_1y,
    COUNTIF(age_days_asof BETWEEN 365 AND 1095) AS aged_1_to_3y,
    COUNTIF(age_days_asof > 1095) AS aged_over_3y,
    COUNTIF(age_days_asof < 0) AS future_dated_filings,
    ROUND(AVG(IF(age_days_asof >= 0, age_days_asof, NULL)) / 365.25, 1) AS avg_age_years,
    SUM(COUNT(*)) OVER () AS total_open,
    SUM(COUNTIF(age_days_asof > 1095)) OVER () AS total_over_3y
FROM open_cases
GROUP BY case_type
ORDER BY open_cases DESC;
