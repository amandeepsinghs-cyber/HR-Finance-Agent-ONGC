-- Probe ID: X2.why
-- Parent ID: X2
-- Answer Type: rag
-- Question: What statutory compliance guidelines (Contract Labour Regulation & Abolition Act) govern deployment in core operational activities?
-- Personas: Director (HR)
-- Tables: 
-- Drill Dims: 
-- Story IDs: S13
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: HR Manual Clause 1.0
SELECT
    'X2.why' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'HR Manual Clause 1.0' AS expected_documents;
