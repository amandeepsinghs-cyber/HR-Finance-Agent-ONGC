-- Proposed Materialized Summary Table 04
-- Table: ongc-hr-finance-agent.hrfin_gold.agg_vacancies_summary
-- Purpose: Pre-aggregate executive vacancies vs sanctioned posts across hard/remote stations and corporate centres.
-- Target Cluster: (wc_id, fiscal_year)

CREATE OR REPLACE TABLE `ongc-hr-finance-agent.hrfin_gold.agg_vacancies_summary`
CLUSTER BY wc_id, fiscal_year
OPTIONS(
    description="Pre-aggregated physical summary of sanctioned strength, in-position counts, and vacancies by work centre."
) AS
SELECT
    sp.fiscal_year,
    sp.wc_id,
    wc.short_name AS work_centre_name,
    wc.hard_station_cat,
    wc.onshore_offshore,
    sp.discipline_id,
    COALESCE(SUM(sp.sanctioned_strength), 0) AS total_sanctioned,
    COALESCE(SUM(sp.in_position_strength), 0) AS total_in_position,
    COALESCE(SUM(sp.vacancy_count), 0) AS total_vacancies,
    ROUND(SAFE_DIVIDE(SUM(sp.vacancy_count), SUM(sp.sanctioned_strength)) * 100, 2) AS vacancy_rate_pct
FROM `ongc-hr-finance-agent.hrfin_silver.sanctioned_posts` sp
JOIN `ongc-hr-finance-agent.hrfin_silver.dim_work_centre` wc ON sp.wc_id = wc.wc_id
GROUP BY
    sp.fiscal_year,
    sp.wc_id,
    wc.short_name,
    wc.hard_station_cat,
    wc.onshore_offshore,
    sp.discipline_id;
