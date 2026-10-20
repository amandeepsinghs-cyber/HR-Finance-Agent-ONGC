-- Proposed Materialized Summary Table 02
-- Table: ongc-hr-finance-agent.hrfin_gold.agg_field_pnl_summary
-- Purpose: Pre-aggregate field-level economics to accelerate P&L and What-If scenario queries from ~1.8s to ~120ms.
-- Target Cluster: (field_id, onshore_offshore)

CREATE OR REPLACE TABLE `ongc-hr-finance-agent.hrfin_gold.agg_field_pnl_summary`
CLUSTER BY field_id, onshore_offshore
OPTIONS(
    description="Pre-aggregated physical field P&L components for rapid executive review and what-if pricing models."
) AS
SELECT
    pnl_id,
    fiscal_year,
    field_id,
    field_name,
    basin,
    onshore_offshore,
    asset_wc_id,
    asset_name,
    oil_revenue_inr_cr,
    gas_revenue_inr_cr,
    recomputed_gross_revenue_inr_cr,
    statutory_royalty_inr_cr,
    statutory_cess_inr_cr,
    statutory_windfall_tax_saed_inr_cr,
    recomputed_net_revenue_inr_cr,
    allocated_manpower_cost_inr_cr,
    total_opex_inr_cr,
    recomputed_ebitda_inr_cr,
    recomputed_ebitda_margin_pct,
    dda_depreciation_inr_cr,
    recomputed_pbt_inr_cr,
    total_production_boe,
    lifting_cost_per_boe_usd,
    manpower_cost_per_boe_usd,
    boe_per_employee,
    is_loss_making_3yr_consecutive,
    is_divestment_candidate,
    pec_monetisation_potential_flag,
    root_cause_loss_code
FROM `ongc-hr-finance-agent.hrfin_gold.v_field_pnl`
WHERE field_id IS NOT NULL;
