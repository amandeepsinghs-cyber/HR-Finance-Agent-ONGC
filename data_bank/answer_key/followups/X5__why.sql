-- Answer Key Follow-up SQL: X5__why
-- Question: What refining margins at MRPL/HPCL and international production volumes at OVL drove their financial performance?
-- Type: data
-- Semantic audit 2026-10-20: FY22-FY26 drivers for all three entities: GRM and throughput for HPCL/MRPL, international production for OVL,
-- next to PAT. Old SQL showed FY26 refining only and omitted OVL.
SELECT
    entity_code,
    fiscal_year,
    pat_inr_cr AS pat_cr,
    gross_refining_margin_usd_bbl,
    refining_throughput_mmt,
    international_production_mmtoe
FROM subsidiary_financials
WHERE fiscal_year IN ('FY22', 'FY23', 'FY24', 'FY25', 'FY26') AND entity_code IN ('OVL', 'MRPL', 'HPCL')
ORDER BY entity_code, fiscal_year;
