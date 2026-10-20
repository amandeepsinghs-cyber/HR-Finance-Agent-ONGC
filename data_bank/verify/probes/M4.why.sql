-- Probe ID: M4.why
-- Parent ID: M4
-- Answer Type: rag
-- Question: Why is field-level profitability confidential and restricted from junior functional officers?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: BDP summary Clause 8.0
SELECT
    'M4.why' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'BDP summary Clause 8.0' AS expected_documents;
