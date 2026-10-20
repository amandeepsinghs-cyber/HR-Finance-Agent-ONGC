-- Answer Key Follow-up SQL: M4__drill_down
-- Question: What is the company-wide crude oil and gas production volume published in the public quarterly report?
-- Type: refusal
-- Semantic audit 2026-10-20: Old SQL returned FY26 annual oil (in tonnes) and gas (MMSCM) as unlabelled metric_1/metric_2 and omitted condensate; question asks for the quarterly published figure.
-- Semantic audit 2026-10-20: Now: quarterly company-wide production FY26-FY27 YTD - oil, condensate (MMT), gas (BCM) and total MMboe in separate columns (no unit mixing).

SELECT
    fiscal_year,
    CONCAT('Q', CAST(DIV(MOD(CAST(SUBSTR(month, 6, 2) AS INT64) + 8, 12), 3) + 1 AS STRING)) AS fy_quarter,
    MIN(month) AS first_month,
    MAX(month) AS last_month,
    COUNT(DISTINCT month) AS months,
    ROUND(SUM(oil_production_mt) / 1e6, 3) AS oil_mmt,
    ROUND(SUM(condensate_production_mt) / 1e6, 3) AS condensate_mmt,
    ROUND(SUM(gas_production_mmscm) / 1e3, 3) AS gas_bcm,
    ROUND(SUM(total_production_boe) / 1e6, 2) AS total_mmboe
FROM production_monthly
WHERE fiscal_year IN ('FY26', 'FY27')
GROUP BY fiscal_year, fy_quarter
ORDER BY fiscal_year DESC, fy_quarter DESC;
