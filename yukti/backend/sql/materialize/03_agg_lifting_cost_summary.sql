-- Proposed Materialized Summary Table 03
-- Table: ongc-hr-finance-agent.hrfin_gold.agg_lifting_cost_summary
-- Purpose: Pre-aggregate asset lifting cost and manpower cost per BOE across ONGC assets.
-- Target Cluster: (asset_wc_id, fiscal_year)

CREATE OR REPLACE TABLE `ongc-hr-finance-agent.hrfin_gold.agg_lifting_cost_summary`
CLUSTER BY asset_wc_id, fiscal_year
OPTIONS(
    description="Physical aggregation of lifting cost and manpower cost per BOE across ONGC assets."
) AS
SELECT
    fiscal_year,
    asset_wc_id,
    asset_name,
    onshore_offshore,
    ROUND(SUM(total_opex_inr_cr), 2) AS total_opex_inr_cr,
    ROUND(SUM(allocated_manpower_cost_inr_cr), 2) AS allocated_manpower_cost_inr_cr,
    ROUND(SUM(total_production_boe), 2) AS total_production_boe,
    SUM(regular_employee_headcount) AS total_regular_headcount,
    SUM(contractor_headcount) AS total_contractor_headcount,
    ROUND(SUM(total_opex_inr_cr * 10000000.0) / NULLIF(SUM(total_production_boe), 0), 2) AS lifting_cost_per_boe_inr,
    ROUND(SUM(total_opex_inr_cr * 10000000.0 / 88.33) / NULLIF(SUM(total_production_boe), 0), 2) AS lifting_cost_per_boe_usd,
    ROUND(SUM(allocated_manpower_cost_inr_cr * 10000000.0 / 88.33) / NULLIF(SUM(total_production_boe), 0), 2) AS manpower_cost_per_boe_usd
FROM `ongc-hr-finance-agent.hrfin_gold.v_lifting_cost`
GROUP BY
    fiscal_year,
    asset_wc_id,
    asset_name,
    onshore_offshore;
