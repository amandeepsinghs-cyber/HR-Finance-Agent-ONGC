-- Probe ID: P19.compare_or_so_what
-- Parent ID: P19
-- Answer Type: rag
-- Question: How can an employee verify whether an expenditure approval has been sanctioned by a competent authority?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: BDP summary Clause 7.0
SELECT
    'P19.compare_or_so_what' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'BDP summary Clause 7.0' AS expected_documents;
