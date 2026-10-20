-- Probe ID: D6.drill_down
-- Parent ID: D6
-- Answer Type: rag
-- Question: What is the standard procedure for reporting a vigilance concern or submitting a complaint in ONGC?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: P2-01, P1-01 Clause 5.0
SELECT
    'D6.drill_down' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'P2-01, P1-01 Clause 5.0' AS expected_documents;
