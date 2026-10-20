-- Probe ID: F6.drill_down
-- Parent ID: F6
-- Answer Type: sql
-- Question: Which public sector OMCs (IOCL, BPCL, HPCL) or regional gas consumers have outstanding dues aged beyond 90 days?
-- Personas: Director (Finance)
-- Tables: receivables, dim_customer
-- Drill Dims: dim_customer.short_name
-- Story IDs: S23
-- Expected Output: table
-- Handcrafted: false

SELECT
    dim_customer.short_name,
    SUM(receivables.outstanding_amount_inr_cr) AS metric_1
FROM receivables
LEFT JOIN dim_customer ON receivables.customer_id = dim_customer.customer_id
WHERE receivables.aging_days > 90 AND dim_customer.type = 'PSU'
GROUP BY dim_customer.short_name
ORDER BY dim_customer.short_name
LIMIT 100;
