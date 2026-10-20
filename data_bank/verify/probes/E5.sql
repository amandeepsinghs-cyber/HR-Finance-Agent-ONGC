-- Probe ID: E5
-- Parent ID: None
-- Answer Type: rag
-- Question: What is the TA/DA entitlement for an offshore posting?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: P1-16, P1-17
SELECT
    'E5' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'P1-16, P1-17' AS expected_documents;
