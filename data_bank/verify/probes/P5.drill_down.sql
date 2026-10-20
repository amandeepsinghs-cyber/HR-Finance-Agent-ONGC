-- Probe ID: P5.drill_down
-- Parent ID: P5
-- Answer Type: rag
-- Question: What are the qualifying service criteria and approved postgraduate degree specializations for executive study leave?
-- Personas: CMD, Director (HR), Director (Finance), E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: Leave Rules Clause 6.0
SELECT
    'P5.drill_down' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'Leave Rules Clause 6.0' AS expected_documents;
