-- Probe ID: P2
-- Parent ID: None
-- Answer Type: rag
-- Question: Which stations count as one cluster for tenure purposes?
-- Personas: CMD, Director (HR), Director (Finance), E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: JRTP Clause 5.0, P1-16
SELECT
    'P2' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'JRTP Clause 5.0, P1-16' AS expected_documents;
