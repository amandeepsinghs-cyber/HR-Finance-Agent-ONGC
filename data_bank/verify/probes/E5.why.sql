-- Probe ID: E5.why
-- Parent ID: E5
-- Answer Type: rag
-- Question: What safety, travel time, and operational guidelines govern the 14-day on / 14-day off rotational shift allowance?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: P1-16, P1-17
SELECT
    'E5.why' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'P1-16, P1-17' AS expected_documents;
