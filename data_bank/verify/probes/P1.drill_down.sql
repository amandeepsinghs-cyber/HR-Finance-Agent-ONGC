-- Probe ID: P1.drill_down
-- Parent ID: P1
-- Answer Type: rag
-- Question: What are the specific tenure limits for hard stations (Assam, Tripura, Silchar) versus normal stations?
-- Personas: CMD, Director (HR), Director (Finance), E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: JRTP Clause 3.0, JRTP Clause 6.0
SELECT
    'P1.drill_down' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'JRTP Clause 3.0, JRTP Clause 6.0' AS expected_documents;
