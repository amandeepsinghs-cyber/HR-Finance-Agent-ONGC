-- Answer Key Follow-up SQL: F10__why
-- Question: What specific asset-level operating expense variations accounted for the quarterly EBITDA fluctuations?
-- Type: document
-- Semantic audit 2026-10-20: was FY26 average water cut by field (not opex, not quarterly). Now, per asset from the
-- Semantic audit 2026-10-20: parent's FY26 quarterly phasing: highest vs lowest quarter EBITDA, and how much of that swing
-- Semantic audit 2026-10-20: came from net revenue vs opex (opex quarterly profile = cost_ledger). Caveat: opex is phased
-- Semantic audit 2026-10-20: from an annual figure, so quarter-to-quarter opex variation is only the ledger profile.

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
    ROUND(MAX(q3.ebitda_q), 1) AS max_quarter_ebitda_cr,
    ARRAY_AGG(q3.quarter ORDER BY q3.ebitda_q DESC LIMIT 1)[OFFSET(0)] AS best_quarter,
    ROUND(MIN(q3.ebitda_q), 1) AS min_quarter_ebitda_cr,
    ARRAY_AGG(q3.quarter ORDER BY q3.ebitda_q ASC LIMIT 1)[OFFSET(0)] AS worst_quarter,
    ROUND(MAX(q3.ebitda_q) - MIN(q3.ebitda_q), 1) AS ebitda_swing_cr,
    ROUND(MAX(q3.gross_q - q3.royalty_saed_q - q3.cess_q) - MIN(q3.gross_q - q3.royalty_saed_q - q3.cess_q), 1) AS net_revenue_swing_cr,
    ROUND(MAX(q3.opex_q) - MIN(q3.opex_q), 1) AS opex_swing_cr,
    ROUND((MAX(q3.opex_q) - MIN(q3.opex_q)) * 100 / NULLIF(SUM(q3.opex_q) / 4, 0), 2) AS opex_swing_pct_of_avg_quarter,
    ROUND(SUM(q3.opex_q), 1) AS opex_fy26_cr
FROM q3
JOIN dim_work_centre wc ON wc.wc_id = q3.asset_wc_id
GROUP BY wc.short_name
ORDER BY ebitda_swing_cr DESC;
