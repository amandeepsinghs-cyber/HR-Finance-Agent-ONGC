-- Probe ID: E4.drill_down
-- Parent ID: E4
-- Answer Type: rag
-- Question: What is the mandatory residency period (years of service) and minimum APAR benchmark score required for E2 to E3 promotion?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: R&P/Promotion Clause 4.0
SELECT
    'E4.drill_down' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'R&P/Promotion Clause 4.0' AS expected_documents;
