-- Probe ID: F5.compare_or_so_what
-- Parent ID: F5
-- Answer Type: sql
-- Question: How does actual contract expenditure compare against the initial purchase order commitment and engineer's estimate?
-- Personas: Director (Finance)
-- Tables: purchase_orders
-- Drill Dims: purchase_orders.po_number
-- Story IDs: S22
-- Expected Output: table
-- Handcrafted: false

SELECT
    purchase_orders.po_number,
    SUM(purchase_orders.actual_paid_amount_inr) - SUM(purchase_orders.engineers_estimate_inr) AS metric_1
FROM purchase_orders
WHERE purchase_orders.cost_overrun_inr > 0
GROUP BY purchase_orders.po_number
ORDER BY purchase_orders.po_number
LIMIT 100;
