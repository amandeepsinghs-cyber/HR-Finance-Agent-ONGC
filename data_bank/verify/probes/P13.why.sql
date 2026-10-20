-- Probe ID: P13.why
-- Parent ID: P13
-- Answer Type: rag
-- Question: Why does the DPE guidelines prohibit employer contribution towards superannuation benefits exceeding 30%?
-- Personas: Director (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: S26
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: PRBS Clause 1.0
SELECT
    'P13.why' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'PRBS Clause 1.0' AS expected_documents;
