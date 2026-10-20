-- Probe ID: D3.why
-- Parent ID: D3
-- Answer Type: rag
-- Question: Why are DPC committee deliberations and promotion candidate lists classified as confidential?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: R&P/Promotion Clause 9.0
SELECT
    'D3.why' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'R&P/Promotion Clause 9.0' AS expected_documents;
