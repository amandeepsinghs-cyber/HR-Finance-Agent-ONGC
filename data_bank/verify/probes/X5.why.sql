-- Probe ID: X5.why
-- Parent ID: X5
-- Answer Type: sql
-- Question: What were the refining margins and crude throughput achieved by HPCL and MRPL?
-- Personas: Director (Finance)
-- Tables: subsidiary_financials
-- Drill Dims: subsidiary_financials.entity_name
-- Story IDs: S33
-- Expected Output: table
-- Handcrafted: true

SELECT
    entity_name,
    refining_throughput_mmt,
    gross_refining_margin_usd_bbl
FROM subsidiary_financials
WHERE fiscal_year IN ('FY26', '2026') AND refining_throughput_mmt IS NOT NULL
ORDER BY refining_throughput_mmt DESC;
