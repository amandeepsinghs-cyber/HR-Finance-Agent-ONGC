-- Probe ID: X10.why
-- Parent ID: X10
-- Answer Type: sql
-- Question: What specific maintenance or compressor downtime event caused the 12% lifting cost spike in Field X this week?
-- Personas: CMD
-- Tables: production_monthly, dim_field
-- Drill Dims: 
-- Story IDs: S36
-- Expected Output: table
-- Handcrafted: true

SELECT
    p.month,
    SUM(p.well_downtime_hours) AS downtime_hours
FROM production_monthly p
WHERE p.field_id = 'FLD-CAM'
  AND p.fiscal_year IN ('FY26', '2026')
GROUP BY p.month
ORDER BY p.month DESC;
