-- Probe ID: F9.why
-- Parent ID: F9
-- Answer Type: rag
-- Question: What treasury risk parameters and Board-approved hedging guidelines govern our forward derivative coverage?
-- Personas: Director (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: S25
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: BDP summary Clause 5.0
SELECT
    'F9.why' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'BDP summary Clause 5.0' AS expected_documents;
