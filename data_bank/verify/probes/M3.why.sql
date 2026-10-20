-- Probe ID: M3.why
-- Parent ID: M3
-- Answer Type: rag
-- Question: Why are individual salary and APAR appraisals classified as strictly confidential personal data?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: P1-01 Clause 5.0, G-08
SELECT
    'M3.why' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'P1-01 Clause 5.0, G-08' AS expected_documents;
