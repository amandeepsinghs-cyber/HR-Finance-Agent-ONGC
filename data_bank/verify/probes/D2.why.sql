-- Probe ID: D2.why
-- Parent ID: D2
-- Answer Type: rag
-- Question: Why are draft transfer orders restricted from disclosure before official notification by HR?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: JRTP Clause 11.0
SELECT
    'D2.why' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'JRTP Clause 11.0' AS expected_documents;
