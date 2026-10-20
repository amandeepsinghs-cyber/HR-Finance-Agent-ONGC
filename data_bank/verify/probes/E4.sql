-- Probe ID: E4
-- Parent ID: None
-- Answer Type: rag
-- Question: What are the eligibility criteria for promotion from E2 to E3?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: R&P/Promotion Clause 4.0, J-15
SELECT
    'E4' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'R&P/Promotion Clause 4.0, J-15' AS expected_documents;
