-- Probe ID: E4.why
-- Parent ID: E4
-- Answer Type: rag
-- Question: Why is promotion up to E4 time-bound subject to fitness, whereas E5 and above are merit-cum-seniority selections?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: R&P/Promotion Clause 4.0, R&P/Promotion Clause 9.0
SELECT
    'E4.why' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'R&P/Promotion Clause 4.0, R&P/Promotion Clause 9.0' AS expected_documents;
