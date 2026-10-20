-- Probe ID: F5
-- Parent ID: None
-- Answer Type: sql
-- Question: Which contracts or vendors make up the top 80% of spend, and where were the cost overruns?
-- Personas: Director (Finance)
-- Tables: purchase_orders, dim_vendor
-- Drill Dims: dim_vendor.name
-- Story IDs: S22
-- Expected Output: table
-- Handcrafted: false
-- Story Target: 35878.0 (total_procurement_spend_cr)
-- Expected Range: 32290.2 - 39465.8 (tolerance: ±10.0%)

SELECT
    dim_vendor.name,
    SUM(purchase_orders.revised_po_value_inr) AS metric_1,
    SUM(purchase_orders.cost_overrun_inr) AS metric_2
FROM purchase_orders
LEFT JOIN dim_vendor ON purchase_orders.vendor_id = dim_vendor.vendor_id
WHERE purchase_orders.fiscal_year IN ('FY26', '2026')
GROUP BY dim_vendor.name
ORDER BY dim_vendor.name
LIMIT 100;
