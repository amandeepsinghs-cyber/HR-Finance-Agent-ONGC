-- Answer Key Follow-up SQL: D4__drill_down
-- Question: What is the company-wide crude oil and natural gas production volume published in the latest annual report?
-- Type: refusal
-- Semantic audit 2026-10-20: Old SQL returned raw tonnes and MMSCM under metric_1/metric_2 and omitted condensate.
-- Semantic audit 2026-10-20: Now FY26 (12 months) crude MMT, condensate MMT, gas BCM kept separate, plus BOE/MMTOE totals (MET-OPS-005).

SELECT
    fiscal_year,
    ROUND(SUM(oil_production_mt) / 1e6, 3) AS crude_oil_mmt,
    ROUND(SUM(condensate_production_mt) / 1e6, 3) AS condensate_mmt,
    ROUND(SUM(gas_production_mmscm) / 1000.0, 3) AS natural_gas_bcm,
    ROUND(SUM(total_production_boe) / 1e6, 2) AS total_mmboe,
    ROUND(SUM(total_production_boe) / 7.33e6, 2) AS total_mmtoe,
    COUNT(DISTINCT month) AS months_covered
FROM production_monthly
WHERE fiscal_year = 'FY26'
GROUP BY fiscal_year;
