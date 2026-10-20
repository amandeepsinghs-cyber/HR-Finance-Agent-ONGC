-- Probe ID: E1.why
-- Parent ID: E1
-- Answer Type: rag
-- Question: Why is there a ceiling on maximum earned leave accumulation and encashment during active service versus retirement?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: S38
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: Leave Rules Clause 3.0, Leave Rules Clause 4.0
SELECT
    'E1.why' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'Leave Rules Clause 3.0, Leave Rules Clause 4.0' AS expected_documents;
