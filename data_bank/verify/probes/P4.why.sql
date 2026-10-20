-- Probe ID: P4.why
-- Parent ID: P4
-- Answer Type: rag
-- Question: Why are leave encashment calculations governed by DPE and income tax statutory caps?
-- Personas: CMD, Director (HR), Director (Finance), E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: Leave Rules Clause 4.0, J-07
SELECT
    'P4.why' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'Leave Rules Clause 4.0, J-07' AS expected_documents;
