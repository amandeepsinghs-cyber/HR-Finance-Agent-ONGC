-- Probe ID: P8.compare_or_so_what
-- Parent ID: P8
-- Answer Type: rag
-- Question: How does a formal Whistle Blower disclosure differ procedurally from an ordinary employee grievance petition?
-- Personas: CMD, Director (HR), Director (Finance), E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: P2-01, HR Manual Clause 1.0
SELECT
    'P8.compare_or_so_what' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'P2-01, HR Manual Clause 1.0' AS expected_documents;
