-- Probe ID: P6.drill_down
-- Parent ID: P6
-- Answer Type: rag
-- Question: What is the exact monetary ceiling on gifts specified under ONGC Conduct, Discipline and Appeal (CDA) rules?
-- Personas: CMD, Director (HR), Director (Finance), E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: P1-01 Clause 13.0
SELECT
    'P6.drill_down' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'P1-01 Clause 13.0' AS expected_documents;
