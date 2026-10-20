-- Probe ID: F5.drill_down
-- Parent ID: F5
-- Answer Type: sql
-- Question: What are the major service contract categories (rig charter, OSV hire, subsea EPC, directional drilling) dominating the top spend?
-- Personas: Director (Finance)
-- Tables: purchase_orders
-- Drill Dims: purchase_orders.service_contract_category
-- Story IDs: S22
-- Expected Output: chart
-- Handcrafted: false

SELECT
    purchase_orders.service_contract_category,
    SUM(purchase_orders.revised_po_value_inr) AS metric_1
FROM purchase_orders
WHERE purchase_orders.fiscal_year IN ('FY26', '2026')
GROUP BY purchase_orders.service_contract_category
ORDER BY purchase_orders.service_contract_category
LIMIT 100;
