-- Probe ID: P2.drill_down
-- Parent ID: P2
-- Answer Type: rag
-- Question: Do Delhi and Dehradun form separate clusters, and how are Mumbai, Uran, and Panvel treated?
-- Personas: CMD, Director (HR), Director (Finance), E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: JRTP Clause 5.0
SELECT
    'P2.drill_down' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'JRTP Clause 5.0' AS expected_documents;
