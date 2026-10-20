-- Probe ID: P1
-- Parent ID: None
-- Answer Type: rag
-- Question: What is the minimum tenure at a station, and the maximum cumulative stay in one city?
-- Personas: CMD, Director (HR), Director (Finance), E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: JRTP Clause 3.0, JRTP Clause 4.0, J-03
SELECT
    'P1' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'JRTP Clause 3.0, JRTP Clause 4.0, J-03' AS expected_documents;
