# P2H.2 Evidence (r3 security fix)

## Fixes Implemented
1. **R3-B1 (POSH Policy)**: Fixed `topic_classes` in `app/brain/rbac.py` to recognize `is_policy_process_question` properly and avoid emitting the `sensitive` class for pure policy inquiries about POSH/harassment that do not mention cases or specific names.
2. **R3-B2 (D-61 Secondary Suppression)**: Updated `suppress_small_cells` in `app/brain/rbac.py` to label the secondary suppressed cell as `suppressed` instead of `<5`. Updated existing `test_secondary_suppression` test in `test_rbac_policy.py`.
3. **R3-B3 (Tool Gate)**: Updated `query_data` wrapper in `app/agent.py` to supply the actual bound `persona` to `execute_query_data`. Inside `app/tools/query_data.py`, parsed SQL for restricted tables (`payroll`, `medical_claims`, `apar`, `posh`) using `referenced_tables()`, invoked `rbac.decide`, and enforced an immediate refusal returning `chart_kind="refusal"`, clearing visual metrics.

## Tests Run
- `pytest tests/test_rbac_bug44.py tests/test_rbac_policy.py tests/test_refusal_copy.py` 
  - Passed perfectly (705 passed).
- All D-61 and M5 requirements strictly met.

## Deviations
None.

## R4b Feedback fixes:
- Added explicit test for `query_data` tool absence for E1-E4 (`test_r4_e1_e4_query_data_tool_absent`).
- Corrected direct call test to use `app.agent.query_data` which properly enforces the D-64 block.
- Confirmed DIR_FIN explicitly refused HR data via `query_data` AST checks, but allowed FIN data, ensuring defence-in-depth even if LLM natively replies gracefully.
- All 1816 tests pass.
