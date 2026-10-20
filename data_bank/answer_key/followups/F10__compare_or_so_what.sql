-- Answer Key Follow-up SQL: F10__compare_or_so_what
-- Question: How does each asset's quarterly operating profit compare with the sanctioned annual operating plan (BE)?
-- Type: document
-- Semantic audit 2026-10-20: listed FY26 field EBITDA only. GAP: no asset-level operating plan / BE for operating profit
-- Semantic audit 2026-10-20: exists (capex_budget BE is capital spend; mou_targets is company-level). Closest honest view:
-- Semantic audit 2026-10-20: each asset's FY26 quarterly EBITDA (parent phasing) against an even quarterly run-rate of its
-- Semantic audit 2026-10-20: own FY26 total and against FY25 actual EBITDA as the prior-year baseline.

WITH m AS (
    SELECT
        p.asset_wc_id,
        CASE WHEN SUBSTR(p.month, 6, 2) IN ('04', '05', '06') THEN 'Q1'
             WHEN SUBSTR(p.month, 6, 2) IN ('07', '08', '09') THEN 'Q2'
             WHEN SUBSTR(p.month, 6, 2) IN ('10', '11', '12') THEN 'Q3'
             ELSE 'Q4' END AS quarter,
        SUM((p.oil_production_mt + p.condensate_production_mt) * 7.33 * x.ongc_crude_net_realisation_inr_bbl) AS oil_val,
        SUM(p.gas_production_mmscm * x.apm_gas_price_usd_mmbtu * x.inr_usd_fx_rate) AS gas_val,
        SUM(p.total_production_boe) AS boe
    FROM production_monthly p
    JOIN price_fx_monthly x ON x.month = p.month
    WHERE p.fiscal_year = 'FY26'
    GROUP BY p.asset_wc_id, quarter
),
ms AS (
    SELECT *,
        IFNULL(SAFE_DIVIDE(oil_val, SUM(oil_val) OVER (PARTITION BY asset_wc_id)), 0.25) AS oil_share,
        IFNULL(SAFE_DIVIDE(gas_val, SUM(gas_val) OVER (PARTITION BY asset_wc_id)), 0.25) AS gas_share
    FROM m
),
cl AS (
    SELECT wc_id AS asset_wc_id,
        CASE WHEN SUBSTR(month, 6, 2) IN ('04', '05', '06') THEN 'Q1'
             WHEN SUBSTR(month, 6, 2) IN ('07', '08', '09') THEN 'Q2'
             WHEN SUBSTR(month, 6, 2) IN ('10', '11', '12') THEN 'Q3'
             ELSE 'Q4' END AS quarter,
        SUM(amount_inr) AS amt
    FROM cost_ledger
    WHERE fiscal_year = 'FY26'
    GROUP BY asset_wc_id, quarter
),
cls AS (
    SELECT asset_wc_id, quarter, SAFE_DIVIDE(amt, SUM(amt) OVER (PARTITION BY asset_wc_id)) AS opex_share FROM cl
),
a AS (
    SELECT asset_wc_id,
        SUM(oil_revenue_inr_cr) AS oil_rev, SUM(gas_revenue_inr_cr) AS gas_rev, SUM(gross_revenue_inr_cr) AS gross,
        SUM(statutory_royalty_inr_cr) AS royalty, SUM(statutory_cess_inr_cr) AS cess,
        SUM(statutory_windfall_tax_saed_inr_cr) AS saed, SUM(total_opex_inr_cr) AS opex,
        SUM(dda_depreciation_inr_cr) AS dda, SUM(ebitda_inr_cr) AS ebitda_fy
    FROM field_pnl_annual
    WHERE fiscal_year = 'FY26' AND LOWER(line_type) = 'field'
    GROUP BY asset_wc_id
),
q AS (
    SELECT
        a.asset_wc_id, ms.quarter, a.ebitda_fy, ms.boe,
        a.oil_rev * ms.oil_share AS oil_q,
        a.gas_rev * ms.gas_share AS gas_q,
        a.cess * ms.oil_share AS cess_q,
        a.opex * IFNULL(cls.opex_share, 0.25) AS opex_q,
        a.dda * 0.25 AS dda_q,
        a.royalty, a.saed, a.gross
    FROM a
    JOIN ms ON ms.asset_wc_id = a.asset_wc_id
    LEFT JOIN cls ON cls.asset_wc_id = a.asset_wc_id AND cls.quarter = ms.quarter
),
q2 AS (
    SELECT *,
        oil_q + gas_q AS gross_q,
        (royalty + saed) * SAFE_DIVIDE(oil_q + gas_q, gross) AS royalty_saed_q
    FROM q
),
q3 AS (
    SELECT *,
        gross_q - royalty_saed_q - cess_q - opex_q AS ebitda_q,
        royalty_saed_q * SAFE_DIVIDE(oil_q, gross_q) AS roy_oil_q,
        royalty_saed_q * SAFE_DIVIDE(gas_q, gross_q) AS roy_gas_q
    FROM q2
)
SELECT
    wc.short_name AS asset_name,
    ROUND(SUM(IF(q3.quarter = 'Q1', q3.ebitda_q, 0)), 1) AS ebitda_q1_cr,
    ROUND(SUM(IF(q3.quarter = 'Q2', q3.ebitda_q, 0)), 1) AS ebitda_q2_cr,
    ROUND(SUM(IF(q3.quarter = 'Q3', q3.ebitda_q, 0)), 1) AS ebitda_q3_cr,
    ROUND(SUM(IF(q3.quarter = 'Q4', q3.ebitda_q, 0)), 1) AS ebitda_q4_cr,
    ROUND(SUM(q3.ebitda_q), 1) AS ebitda_fy26_cr,
    ROUND(ANY_VALUE(p.ebitda_fy25), 1) AS ebitda_fy25_cr,
    ROUND((SUM(q3.ebitda_q) - ANY_VALUE(p.ebitda_fy25)) * 100 / NULLIF(ANY_VALUE(p.ebitda_fy25), 0), 1) AS change_vs_fy25_pct,
    'not available' AS operating_plan_be
FROM q3
JOIN dim_work_centre wc ON wc.wc_id = q3.asset_wc_id
LEFT JOIN (
    SELECT asset_wc_id, SUM(ebitda_inr_cr) AS ebitda_fy25
    FROM field_pnl_annual
    WHERE fiscal_year = 'FY25' AND LOWER(line_type) = 'field'
    GROUP BY asset_wc_id
) p ON p.asset_wc_id = q3.asset_wc_id
GROUP BY wc.short_name
ORDER BY ebitda_fy26_cr DESC;
