-- Probe ID: E2.why
-- Parent ID: E2
-- Answer Type: rag
-- Question: What specific criteria under the Job Rotation and Transfer Policy (JRTP) determine my priority for transfer in the upcoming cycle?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: S38
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: JRTP Clause 3.0, JRTP Clause 9.0
SELECT
    'E2.why' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'JRTP Clause 3.0, JRTP Clause 9.0' AS expected_documents;
