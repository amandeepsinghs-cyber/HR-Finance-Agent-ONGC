-- Probe ID: M1.why
-- Parent ID: M1
-- Answer Type: rag
-- Question: Why is aggregate asset-level headcount accessible to HR officers but restricted from general Finance officers?
-- Personas: E1–E4 Officer (HR)
-- Tables: 
-- Drill Dims: 
-- Story IDs: S3
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: G-08, P1-01 Clause 5.0
SELECT
    'M1.why' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'G-08, P1-01 Clause 5.0' AS expected_documents;
