-- Probe ID: E2.compare_or_so_what
-- Parent ID: E2
-- Answer Type: rag
-- Question: How does the standard tenure duration for my grade (E2) compare with senior executive tenures (E5+)?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: S38
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: JRTP Clause 3.0
SELECT
    'E2.compare_or_so_what' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'JRTP Clause 3.0' AS expected_documents;
