-- Probe ID: P10.why
-- Parent ID: P10
-- Answer Type: rag
-- Question: What role do qualification enhancement, mandatory training completion, and vigilance clearance play in the promotion order?
-- Personas: CMD, Director (HR), Director (Finance), E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: R&P/Promotion Clause 9.0
SELECT
    'P10.why' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'R&P/Promotion Clause 9.0' AS expected_documents;
