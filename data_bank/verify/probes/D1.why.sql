-- Probe ID: D1.why
-- Parent ID: D1
-- Answer Type: rag
-- Question: Why is individual officer salary confidential under ONGC policy and CDA rules?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: P1-01 Clause 5.0, G-08
SELECT
    'D1.why' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'P1-01 Clause 5.0, G-08' AS expected_documents;
