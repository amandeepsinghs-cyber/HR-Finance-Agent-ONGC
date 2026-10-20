-- Probe ID: F6.why
-- Parent ID: F6
-- Answer Type: sql
-- Question: What billing disputes, price reconciliation delays, or subsidy settlement issues delayed clearance of aged trade receivables?
-- Personas: Director (Finance)
-- Tables: receivables, dim_customer
-- Drill Dims: receivables.dispute_reason
-- Story IDs: S23
-- Expected Output: table
-- Handcrafted: false

SELECT
    receivables.dispute_reason,
    SUM(receivables.outstanding_amount_inr_cr) AS metric_1
FROM receivables
LEFT JOIN dim_customer ON receivables.customer_id = dim_customer.customer_id
WHERE receivables.is_disputed = TRUE
GROUP BY receivables.dispute_reason
ORDER BY receivables.dispute_reason
LIMIT 100;
