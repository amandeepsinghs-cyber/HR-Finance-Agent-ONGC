-- Probe ID: P3.drill_down
-- Parent ID: P3
-- Answer Type: rag
-- Question: What is the exact superannuation exemption cut-off window (e.g. 2 years vs 3 years) under the JRTP?
-- Personas: CMD, Director (HR), Director (Finance), E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: JRTP Clause 7.0
SELECT
    'P3.drill_down' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'JRTP Clause 7.0' AS expected_documents;
