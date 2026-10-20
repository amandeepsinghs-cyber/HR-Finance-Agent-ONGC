-- Probe ID: P7
-- Parent ID: None
-- Answer Type: rag
-- Question: What is my travel class and lodging allowance for official travel to Mumbai as an E2?
-- Personas: CMD, Director (HR), Director (Finance), E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: P1-16, P1-17
SELECT
    'P7' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'P1-16, P1-17' AS expected_documents;
