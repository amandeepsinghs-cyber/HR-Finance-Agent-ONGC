-- Probe ID: D2.drill_down
-- Parent ID: D2
-- Answer Type: rag
-- Question: What is the general criteria and eligibility cutoff date for the upcoming Mumbai transfer cycle?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: JRTP Clause 3.0, JRTP Clause 9.0
SELECT
    'D2.drill_down' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'JRTP Clause 3.0, JRTP Clause 9.0' AS expected_documents;
