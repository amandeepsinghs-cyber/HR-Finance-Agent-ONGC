-- Probe ID: P4.drill_down
-- Parent ID: P4
-- Answer Type: rag
-- Question: What is the maximum limit on earned leave accumulation (e.g. 300 days) and half pay leave encashment at superannuation?
-- Personas: CMD, Director (HR), Director (Finance), E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: Leave Rules Clause 3.0, Leave Rules Clause 5.0
SELECT
    'P4.drill_down' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'Leave Rules Clause 3.0, Leave Rules Clause 5.0' AS expected_documents;
