-- Probe ID: P16.why
-- Parent ID: P16
-- Answer Type: rag
-- Question: Why does the Book of Delegated Powers (BDP) require tender committee recommendations prior to Director sanction?
-- Personas: CMD, Director (HR), Director (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: S29
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: BDP summary Clause 7.0
SELECT
    'P16.why' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'BDP summary Clause 7.0' AS expected_documents;
