-- Probe ID: P6.why
-- Parent ID: P6
-- Answer Type: rag
-- Question: Why do CVC regulations require prompt reporting and surrender of commercial vendor gifts exceeding nominal value?
-- Personas: CMD, Director (HR), Director (Finance), E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: P1-01 Clause 13.0
SELECT
    'P6.why' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'P1-01 Clause 13.0' AS expected_documents;
