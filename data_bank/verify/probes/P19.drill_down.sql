-- Probe ID: P19.drill_down
-- Parent ID: P19
-- Answer Type: rag
-- Question: What are the general financial authorities delegated to Key Executives / Level-1 managers for day-to-day operations?
-- Personas: E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: list
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: BDP summary Clause 2.0
SELECT
    'P19.drill_down' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'BDP summary Clause 2.0' AS expected_documents;
