-- Probe ID: P3.compare_or_so_what
-- Parent ID: P3
-- Answer Type: rag
-- Question: How does the transfer exemption policy apply to medical hardship or spouse-ground cases compared to retirement?
-- Personas: CMD, Director (HR), Director (Finance), E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: JRTP Clause 7.0, JRTP Clause 8.0
SELECT
    'P3.compare_or_so_what' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'JRTP Clause 7.0, JRTP Clause 8.0' AS expected_documents;
