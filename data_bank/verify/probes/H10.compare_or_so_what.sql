-- Probe ID: H10.compare_or_so_what
-- Parent ID: H10
-- Answer Type: sql
-- Question: How does the proposed transfer list balance regional deficit clearance against the approved annual transfer budget?
-- Personas: Director (HR)
-- Tables: posting_history
-- Drill Dims: 
-- Story IDs: S20
-- Expected Output: table
-- Handcrafted: false

SELECT
    SUM(posting_history.total_transfer_cost_inr) AS metric_1
FROM posting_history
ORDER BY 1
LIMIT 100;
