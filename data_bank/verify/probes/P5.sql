-- Probe ID: P5
-- Parent ID: None
-- Answer Type: rag
-- Question: Am I eligible for study leave, and what bond applies?
-- Personas: CMD, Director (HR), Director (Finance), E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: Leave Rules Clause 6.0, Leave Rules Clause 7.0, J-08
SELECT
    'P5' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'Leave Rules Clause 6.0, Leave Rules Clause 7.0, J-08' AS expected_documents;
