-- Probe ID: P19.why
-- Parent ID: P19
-- Answer Type: rag
-- Question: Why are detailed Director and Board financial authorities restricted from full disclosure to general staff?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: BDP summary Clause 8.0
SELECT
    'P19.why' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'BDP summary Clause 8.0' AS expected_documents;
