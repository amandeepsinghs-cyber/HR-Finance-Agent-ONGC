-- Probe ID: P1.why
-- Parent ID: P1
-- Answer Type: rag
-- Question: Why does the JRTP establish a 10-year cumulative city tenure cap for executives?
-- Personas: CMD, Director (HR), Director (Finance), E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: JRTP Clause 4.0
SELECT
    'P1.why' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'JRTP Clause 4.0' AS expected_documents;
