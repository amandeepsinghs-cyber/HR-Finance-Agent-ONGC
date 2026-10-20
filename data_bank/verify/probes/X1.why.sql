-- Probe ID: X1.why
-- Parent ID: X1
-- Answer Type: rag
-- Question: Why do processing plants and field installations maintain higher contract labour ratios for support operations?
-- Personas: CMD, Director (HR)
-- Tables: 
-- Drill Dims: 
-- Story IDs: S13
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: HR Manual Clause 1.0
SELECT
    'X1.why' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'HR Manual Clause 1.0' AS expected_documents;
