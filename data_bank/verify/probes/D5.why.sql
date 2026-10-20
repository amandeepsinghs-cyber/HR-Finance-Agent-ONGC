-- Probe ID: D5.why
-- Parent ID: D5
-- Answer Type: rag
-- Question: Why is bulk employee roster extraction with tenure restricted for junior officers?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: G-08, JRTP Clause 11.0
SELECT
    'D5.why' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'G-08, JRTP Clause 11.0' AS expected_documents;
