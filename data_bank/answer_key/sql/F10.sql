-- Answer Key SQL: F10
-- Question: Generate a quarterly asset-wise P&L sheet.
-- Type: document
-- Semantic audit 2026-10-20: was an ANNUAL FY26 sheet (not quarterly) that mixed corporate/plant/reconciliation lines
-- Semantic audit 2026-10-20: into 19 'work centres'. No quarterly P&L table exists (GAP), so FY26 (last full FY) field-line
-- Semantic audit 2026-10-20: P&L per producing asset is phased into quarters: oil revenue by monthly (oil+condensate) x
-- Semantic audit 2026-10-20: ONGC crude realisation, gas revenue by monthly gas volume x APM price x FX, royalty/SAED by
-- Semantic audit 2026-10-20: gross-revenue share, cess by oil share, opex by the cost_ledger quarterly profile of the asset
-- Semantic audit 2026-10-20: (even if absent), DD&A evenly. Quarters sum exactly to the annual field P&L.

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
)
SELECT
    wc.short_name AS asset_name,
    CONCAT('FY26-', q2.quarter) AS quarter,
    ROUND(q2.boe / 1e6, 2) AS production_mmboe,
    ROUND(q2.oil_q, 1) AS crude_revenue_cr,
    ROUND(q2.gas_q, 1) AS gas_revenue_cr,
    ROUND(q2.gross_q, 1) AS gross_revenue_cr,
    ROUND(q2.royalty_saed_q + q2.cess_q, 1) AS statutory_levies_cr,
    ROUND(q2.gross_q - q2.royalty_saed_q - q2.cess_q, 1) AS net_revenue_cr,
    ROUND(q2.opex_q, 1) AS opex_cr,
    ROUND(q2.gross_q - q2.royalty_saed_q - q2.cess_q - q2.opex_q, 1) AS ebitda_cr,
    ROUND((q2.gross_q - q2.royalty_saed_q - q2.cess_q - q2.opex_q) * 100 / NULLIF(q2.gross_q, 0), 1) AS ebitda_margin_pct,
    ROUND(q2.dda_q, 1) AS dda_cr,
    ROUND(q2.gross_q - q2.royalty_saed_q - q2.cess_q - q2.opex_q - q2.dda_q, 1) AS pbt_cr,
    ROUND(q2.ebitda_fy, 1) AS ebitda_fy26_annual_cr
FROM q2
JOIN dim_work_centre wc ON wc.wc_id = q2.asset_wc_id
ORDER BY q2.ebitda_fy DESC, q2.quarter;
