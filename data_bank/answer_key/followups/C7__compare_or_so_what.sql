-- Answer Key Follow-up SQL: C7__compare_or_so_what
-- Question: How does the reserve replacement ratio (RRR) and capital intensity ($/BOE added) compare between KG-98/2 and Mumbai High Redevelopment?
-- Type: data
-- Semantic audit 2026-10-20: old SQL averaged RRR and development cost by basin (unweighted, 7 basins) - not the
-- two named developments. Now: KG-DWN-98/2 Cluster-II (FLD-KG982) vs Mumbai High North + South (FLD-MHN,
-- FLD-MHS, the MH Redevelopment fields): FY26 RRR, 5-year RRR FY22-FY26 (sum of 2P accretion / sum of
-- production, ratio of sums), FY26 development and finding cost per BOE, 2P reserves, and capital intensity
-- = development project revised cost (PRJ-0001 vs PRJ-0003 + PRJ-0004, INR -> USD at FY26 avg) per BOE of 2P
-- accretion FY22-FY26 (1 MMTOE = 7.33 MMboe, glossary / MET-OPS-005).

WITH r AS (
    SELECT
        CASE WHEN field_id = 'FLD-KG982' THEN 'KG-DWN-98/2 Cluster-II' ELSE 'Mumbai High Redevelopment (MHN + MHS)' END AS development,
        fiscal_year, reserves_2p_total_mmtoe, gross_reserves_accretion_mmtoe, annual_production_mmtoe,
        reserve_replacement_ratio_rrr_2p, development_cost_usd_per_boe, finding_cost_usd_per_boe
    FROM reserves_annual
    WHERE field_id IN ('FLD-KG982', 'FLD-MHN', 'FLD-MHS')
      AND fiscal_year IN ('FY22', 'FY23', 'FY24', 'FY25', 'FY26')
),
agg AS (
    SELECT development,
           SUM(IF(fiscal_year = 'FY26', reserves_2p_total_mmtoe, 0)) AS reserves_2p_mmtoe_fy26,
           SUM(IF(fiscal_year = 'FY26', gross_reserves_accretion_mmtoe, 0)) / NULLIF(SUM(IF(fiscal_year = 'FY26', annual_production_mmtoe, 0)), 0) AS rrr_fy26,
           SUM(gross_reserves_accretion_mmtoe) / NULLIF(SUM(annual_production_mmtoe), 0) AS rrr_fy22_fy26,
           SUM(gross_reserves_accretion_mmtoe) AS accretion_5yr_mmtoe,
           SUM(IF(fiscal_year = 'FY26', development_cost_usd_per_boe * reserves_2p_total_mmtoe, 0))
               / NULLIF(SUM(IF(fiscal_year = 'FY26', reserves_2p_total_mmtoe, 0)), 0) AS dev_cost_usd_boe_fy26,
           SUM(IF(fiscal_year = 'FY26', finding_cost_usd_per_boe * reserves_2p_total_mmtoe, 0))
               / NULLIF(SUM(IF(fiscal_year = 'FY26', reserves_2p_total_mmtoe, 0)), 0) AS finding_cost_usd_boe_fy26
    FROM r GROUP BY development
),
prj AS (
    SELECT CASE WHEN prj_id = 'PRJ-0001' THEN 'KG-DWN-98/2 Cluster-II' ELSE 'Mumbai High Redevelopment (MHN + MHS)' END AS development,
           SUM(revised_cost) AS project_cost_cr
    FROM (SELECT prj_id, ANY_VALUE(revised_cost_inr_cr) AS revised_cost FROM project_progress
          WHERE prj_id IN ('PRJ-0001', 'PRJ-0003', 'PRJ-0004') GROUP BY prj_id)
    GROUP BY 1
),
fx AS (SELECT AVG(inr_usd_fx_rate) AS fx FROM dim_price_fx WHERE fiscal_year = 'FY26')
SELECT
    a.development,
    ROUND(a.reserves_2p_mmtoe_fy26, 1) AS reserves_2p_mmtoe_fy26,
    ROUND(a.rrr_fy26, 2) AS rrr_2p_fy26,
    ROUND(a.rrr_fy22_fy26, 2) AS rrr_2p_fy22_fy26,
    ROUND(a.accretion_5yr_mmtoe, 2) AS accretion_fy22_fy26_mmtoe,
    ROUND(a.dev_cost_usd_boe_fy26, 2) AS dev_cost_usd_boe_fy26,
    ROUND(a.finding_cost_usd_boe_fy26, 2) AS finding_cost_usd_boe_fy26,
    ROUND(p.project_cost_cr, 0) AS project_revised_cost_cr,
    ROUND(p.project_cost_cr * 1e7 / fx.fx / NULLIF(a.accretion_5yr_mmtoe * 7.33e6, 0), 2) AS project_capex_usd_per_boe_added
FROM agg a
LEFT JOIN prj p ON p.development = a.development
CROSS JOIN fx
ORDER BY a.development;
