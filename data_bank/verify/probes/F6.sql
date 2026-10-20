-- Probe ID: F6
-- Parent ID: None
-- Answer Type: sql
-- Question: How old are receivables from oil marketing companies and gas buyers, by customer?
-- Personas: Director (Finance)
-- Tables: receivables, dim_customer
-- Drill Dims: dim_customer.name, receivables.aging_bucket
-- Story IDs: S23
-- Expected Output: table
-- Handcrafted: false
-- Story Target: 13168.0 (total_trade_receivables_cr)
-- Expected Range: 11851.2 - 14484.8 (tolerance: ±10.0%)

SELECT
    dim_customer.name,
    receivables.aging_bucket,
    SUM(receivables.outstanding_amount_inr_cr) AS metric_1
FROM receivables
LEFT JOIN dim_customer ON receivables.customer_id = dim_customer.customer_id
WHERE receivables.outstanding_amount_inr_cr > 0
GROUP BY dim_customer.name, receivables.aging_bucket
ORDER BY dim_customer.name
LIMIT 100;
