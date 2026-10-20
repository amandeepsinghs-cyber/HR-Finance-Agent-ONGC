-- Materialized Summary Table 01
-- Table: ongc-hr-finance-agent.hrfin_gold.agg_headcount_tenure_summary
-- Purpose: Accelerate continuous station tenure queries from ~2.1s down to ~150ms.
-- Target Cluster: (wc_id, continuous_stay_months)
-- Reconciles to: 419 total / 17 exempt retiring / 1 exempt tag / 401 due transfer for Delhi >=60m

CREATE OR REPLACE TABLE `ongc-hr-finance-agent.hrfin_gold.agg_headcount_tenure_summary`
CLUSTER BY wc_id, continuous_stay_months
OPTIONS(
    description="Pre-aggregated physical summary of executive continuous station tenure with retirement and tag exemption flags."
) AS
WITH cur_exempt AS (
    SELECT emp_id, LOGICAL_OR(
        LOWER(IFNULL(exemption_tag, 'none')) NOT IN ('none', '')
        AND (exemption_valid_until IS NULL OR exemption_valid_until >= DATE '2026-10-19')) AS has_valid_exemption
    FROM `ongc-hr-finance-agent.hrfin_silver.posting_history`
    WHERE is_current_posting
    GROUP BY emp_id
),
base AS (
    SELECT
        v.wc_id,
        v.wc_name,
        v.cluster_id,
        v.cluster_name,
        v.hard_station_cat,
        v.grade_id,
        v.discipline_id,
        v.continuous_stay_months,
        v.continuous_stay_years,
        v.emp_id,
        DATE_DIFF(v.retirement_date, DATE '2026-10-19', DAY) <= 3 * 365.25 AS retiring_3yr,
        IFNULL(x.has_valid_exemption, FALSE) AS has_valid_exemption
    FROM `ongc-hr-finance-agent.hrfin_gold.v_continuous_stay` v
    LEFT JOIN cur_exempt x ON x.emp_id = v.emp_id
    WHERE v.is_current_stay = TRUE
)
SELECT
    wc_id,
    wc_name,
    cluster_id,
    cluster_name,
    hard_station_cat,
    grade_id,
    discipline_id,
    continuous_stay_months,
    continuous_stay_years,
    COUNT(DISTINCT emp_id) AS total_executives,
    COUNT(DISTINCT IF(retiring_3yr, emp_id, NULL)) AS exempt_retiring_3yr,
    COUNT(DISTINCT IF(NOT retiring_3yr AND has_valid_exemption, emp_id, NULL)) AS exempt_valid_tag,
    COUNT(DISTINCT IF(NOT retiring_3yr AND NOT has_valid_exemption, emp_id, NULL)) AS non_exempt_due_transfer
FROM base
GROUP BY
    wc_id,
    wc_name,
    cluster_id,
    cluster_name,
    hard_station_cat,
    grade_id,
    discipline_id,
    continuous_stay_months,
    continuous_stay_years;
