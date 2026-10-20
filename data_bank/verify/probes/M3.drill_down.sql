-- Probe ID: M3.drill_down
-- Parent ID: M3
-- Answer Type: rag
-- Question: What is the authorized procedure for an executive to view their own APAR grading and salary slip on the ESS portal?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: HR Manual Clause 1.0
SELECT
    'M3.drill_down' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'HR Manual Clause 1.0' AS expected_documents;
