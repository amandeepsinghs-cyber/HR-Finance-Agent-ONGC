-- Probe ID: P8.drill_down
-- Parent ID: P8
-- Answer Type: rag
-- Question: Who is the designated Chief Vigilance Officer (CVO) / Nodal Officer for receiving Whistle Blower disclosures?
-- Personas: CMD, Director (HR), Director (Finance), E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: P2-01
SELECT
    'P8.drill_down' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'P2-01' AS expected_documents;
