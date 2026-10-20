-- Probe ID: P10
-- Parent ID: None
-- Answer Type: rag
-- Question: What are the criteria for promotion from E3 to E4?
-- Personas: CMD, Director (HR), Director (Finance), E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: R&P/Promotion Clause 9.0, P1-14
SELECT
    'P10' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'R&P/Promotion Clause 9.0, P1-14' AS expected_documents;
