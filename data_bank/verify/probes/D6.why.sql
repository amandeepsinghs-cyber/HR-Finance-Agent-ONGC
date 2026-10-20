-- Probe ID: D6.why
-- Parent ID: D6
-- Answer Type: rag
-- Question: Why is vigilance inquiry status confidential and exempt from disclosure?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: P1-01 Clause 5.0
SELECT
    'D6.why' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'P1-01 Clause 5.0' AS expected_documents;
