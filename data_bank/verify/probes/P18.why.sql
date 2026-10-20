-- Probe ID: P18.why
-- Parent ID: P18
-- Answer Type: rag
-- Question: Why is the draft transfer proposal strictly confidential prior to official approval by Director (HR) and CMD?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: JRTP Clause 11.0
SELECT
    'P18.why' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'JRTP Clause 11.0' AS expected_documents;
