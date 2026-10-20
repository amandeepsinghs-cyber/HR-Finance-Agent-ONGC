-- Probe ID: F5.why
-- Parent ID: F5
-- Answer Type: sql
-- Question: What contract variations, scope changes, or standby day rates caused cost overruns on major turnkey contracts?
-- Personas: Director (Finance)
-- Tables: purchase_orders
-- Drill Dims: purchase_orders.overrun_reason
-- Story IDs: S22
-- Expected Output: table
-- Handcrafted: false

SELECT
    purchase_orders.overrun_reason,
    SUM(purchase_orders.scope_variation_value_inr) AS metric_1,
    SUM(purchase_orders.standby_charges_inr) AS metric_2
FROM purchase_orders
WHERE purchase_orders.cost_overrun_inr > 0
GROUP BY purchase_orders.overrun_reason
ORDER BY purchase_orders.overrun_reason
LIMIT 100;
