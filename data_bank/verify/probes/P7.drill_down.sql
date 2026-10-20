-- Probe ID: P7.drill_down
-- Parent ID: P7
-- Answer Type: rag
-- Question: What is the approved daily hotel reimbursement entitlement and local conveyance ceiling for Mumbai (Class-A city) for E2?
-- Personas: CMD, Director (HR), Director (Finance), E1–E4 Officer (HR), E1–E4 Officer (Finance)
-- Tables: 
-- Drill Dims: 
-- Story IDs: 
-- Expected Output: table
-- Handcrafted: false

-- STUB: Pure RAG entry (verified in Phase 3 unstructured document audit)
-- Document Expectation: P1-16
SELECT
    'P7.drill_down' AS probe_id,
    'STUB_RAG' AS status,
    'Verified in Phase 3 via unstructured docs' AS notes,
    'P1-16' AS expected_documents;
