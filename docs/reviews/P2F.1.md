# Independent G4 Review — P2F.1: Year Clarification for Statement Requests

**Verdict: CHANGES REQUESTED (Round 2 — 1-line `UnboundLocalError` in `pipeline.py`)**  
**Reviewer:** `reviewer-p16` (Independent G4 Reviewer, Role R)  
**Commit Reviewed:** `3089fe2` on branch `v3/P2F-fin-diag` (`HR and Finance_ONGC__v3P2F`)  
**Specs & Packet Referenced:** `SPEC-08` (§3.1–§3.4, §10 `AC-01`, `AC-02`), `SPEC-06` (§2.5), `docs/delegation/packets/v3/P2F.1_year_clarification.md`

---

## 1. Executive Summary (BLUF)

**All 3 Round 1 functional blockers (`P2F1-B1` through `P2F1-B3`) are fixed in `turn_runner.py`, `normalize.py`, `config.py`, and `tests/test_year_clarify.py` (`tests/test_normalize.py` passes `44/44`), but a 1-line Python scoping bug (`import re` at `pipeline.py:296` after `re.search` at `pipeline.py:141`) raises `UnboundLocalError: cannot access local variable 're' where it is not associated with a value` on every call to `run_planner_turn`.**

---

## 2. Must-Fix Blocker (`P2F1-R2-B1`)

### `P2F1-R2-B1` (BLOCKER) — `import re` inside `run_planner_turn` (`pipeline.py:296`) shadows `re` at `pipeline.py:141`, raising `UnboundLocalError`

- **File & Lines:** `yukti/backend/app/brain/pipeline.py:141, 296`
- **What is wrong:**
  - Commit `3089fe2` added `if re.search(r"\b(why|what drove|reason\w*|cause\w*|attribut\w*|how come)\b", query, re.I):` at `pipeline.py:141` and `import re` at `pipeline.py:296` inside the same function `run_planner_turn`.
  - Because `import re` appears inside `run_planner_turn` at line `296`, Python treats `re` as a local variable throughout `run_planner_turn`, so reaching line `141` raises `UnboundLocalError: cannot access local variable 're' where it is not associated with a value` and fails `tests/test_year_clarify.py`.
- **Required Fix:**
  1. Move `import re` to the top of `yukti/backend/app/brain/pipeline.py` (e.g., line 12) and delete `import re` at line `296`.
  2. Delete the 3 untracked scratch scripts in the worktree root (`fix_p2f1.py`, `fix_p2f2_compiler.py`, `fix_p2f2_presenter.py`).
  3. *(Recommended for test speed/determinism)* In `yukti/backend/tests/test_year_clarify.py`, monkeypatch `get_planner().plan` in `setup_config` so the 19 parametrized turns in `test_year_clarify_resolution` do not make 19 live Gemini network calls.

---

## 3. Round 1 Blocker Resolution Verification

| Round 1 Item | Status in `3089fe2` | Evidence |
|---|---|---|
| `P2F1-B1`: Guard `spec_override` in `pipeline.py:160`, check clarify table before `resolve_fy` in `turn_runner.py:364-379`, dynamic `v3_field_enabled` in `config.py:73-74` | **RESOLVED** | Verified all 19 phrases in `test_year_clarify_resolution` pass once `import re` is moved to top of `pipeline.py` |
| `P2F1-B2`: Context carry-over notice (`Showing FY24, as before. Say 'latest' for FY26.`) and bare-year disambiguation (`FY2024-25 (year ended 31-Mar-2025)`) in `spoken_summary` | **RESOLVED** | `pipeline.py:287-300`, verified in `test_year_clarify_context_carryover` and `test_year_clarify_resolution["2025"]` |
| `P2F1-B3`: `normalize.py` anchor-relative vs `available` resolution + 19-phrase parametrized test in `test_year_clarify.py` | **RESOLVED** | `tests/test_normalize.py` passes `44/44` |
| `P2F1-R2-B1`: `UnboundLocalError` on `re` at `pipeline.py:141, 296` | **FAIL (1-line fix)** | Move `import re` to module top-level in `pipeline.py` |
