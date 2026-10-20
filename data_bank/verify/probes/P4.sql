-- Probe ID: P4
-- Parent ID: None
-- Answer Type: rag
-- Question: How many earned leave days can I accumulate and encash at retirement?
-- Personas: CMD, Director (HR), Director (Finance), E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: Leave Rules Clause 3.0, Leave Rules Clause 4.0, J-01
SELECT
    'P4' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'Leave Rules Clause 3.0, Leave Rules Clause 4.0, J-01' AS expected_documents;
