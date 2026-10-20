-- Probe ID: M2.why
-- Parent ID: M2
-- Answer Type: rag
-- Question: Why is financial capex utilisation accessible to Finance officers while restricted for junior HR officers?
-- Personas: E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: S9
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: BDP summary Clause 1.0
SELECT
    'M2.why' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'BDP summary Clause 1.0' AS expected_documents;
