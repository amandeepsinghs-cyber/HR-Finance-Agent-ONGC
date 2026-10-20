-- Probe ID: P16
-- Parent ID: None
-- Answer Type: sql_plus_rag
-- Question: Who has the authority to approve a ₹50 crore drilling contract under the delegated powers?
-- Personas: CMD, Director (HR), Director (Finance)
-- Tables: purchase_orders
-- Drill Dims: 
-- Story IDs: S29
-- Expected Output: table
-- Handcrafted: true
-- Story Target: 50.0 (drilling_contract_value_cr)
-- Expected Range: 45.0 - 55.0 (tolerance: ±10.0%)

SELECT
    po_number,
    service_contract_category,
    SUM(revised_po_value_inr) / 10000000.0 AS po_value_cr
FROM purchase_orders
WHERE service_contract_category LIKE '%Drilling%'
GROUP BY po_number, service_contract_category
ORDER BY po_value_cr DESC
LIMIT 50;
