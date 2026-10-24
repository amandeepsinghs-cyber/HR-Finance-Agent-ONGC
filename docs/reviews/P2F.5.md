# Gate G4 Independent Review — P2F.5 (Grounded "Why" Answers: Variance Rows + AR Chunks, Non-Circular Grounding)

**Verdict:** **APPROVE** (Round 2 — `03e3d1a` on `v3/P2F-fin-diag`)

**BLUF:** Commits `c0b0e56` and `03e3d1a` on `v3/P2F-fin-diag` resolve all 4 Round 1 blockers (`P2F5-B1`..`P2F5-B4`). All 26 tests across `tests/test_grounding_v3.py` (`5/5`) and `tests/test_why.py` (`21/21`, including `test_why_agent_revenue_fy23` and the 20-question parametrized grounding suite `test_why_agent_20_questions`) pass in 8.04s, and `grep` confirms 0 runtime references to `financial_notes_corpus.jsonl`, `ssot_financial_line_context.json`, or `FY_DIRECTOR_ACTIONS` (`SPEC-08 AC-05, AC-06, AC-08` ✅).

---

## Round 2 Verification Summary (`03e3d1a`)

### 1. `P2F5-B1` — Why-Intent Routing & `AC-06` Standalone Revenue (`RESOLVED`)
- [pipeline.py](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2F/yukti/backend/app/brain/pipeline.py#L137-L153) removes the inner `import re` shadow, checks `CORP_METRIC_TO_SSOT` + `("revenue_cr", "pbt_cr", "pat_cr", "ebitda_cr", "pnl_statement")` (when no field/asset filter is present), and remaps `"revenue_cr"` to `"corporate_revenue_cr"` (`PL.REV_OPS`, standalone) before calling `run_why_turn`.
- `test_why_agent_revenue_fy23` verifies `"Why did revenue fall in FY23?"` executes `run_why_turn` with 0 `"Mumbai High"` / `"Bassein"` content and 0 references to `ssot_field_economics_360` (`SPEC-08 AC-06`).

### 2. `P2F5-B2` — SSOT Parquet Loading, Offline `ARRetriever` Fallback, `coverage='partial'` Remainder & Contract Schema (`RESOLVED`)
- [why.py](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2F/yukti/backend/app/agents/fin_diagnostics/why.py#L16-L207) loads `fact_snapshot.parquet` directly, maps `CORP_METRIC_TO_SSOT` + query keywords (`royalty`, `saed`, `statutory`, `opex`, `dd&a`, `finance cost`, `exchange`, `provision`, `crude`, `gas`, `vap`, `other income`, `exploration`) and `resolve_fy(query)`, wraps `ARRetriever().retrieve(...)` in `try/except` with an injectable `retriever` parameter, includes `₹{abs(partial_rows[0].impact_inr_cr):.1f} crore` when `coverage == "partial"`, sets `spoken_summary = text`, populates `sources[]` with SSOT `doc`/`page` + AR `citation`, and formats `visual.chart.data` as a list of row dicts with `x_key`/`y_keys`.

### 3. `P2F5-B3` — Citation-Gated Quote Exemption & `grounding_drop` Logging (`RESOLVED`)
- [grounding.py](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2F/yukti/backend/app/brain/grounding.py#L5-L79) requires `[AR FYxx p.YY]` on quoted strings (`_QUOTE = re.compile(r'"([^"]*)"\s*\[AR\s*FY\d{2}(?:\s+PDF)?\s*p\.[^\]]+\]')`), masks cited quotes before sentence splitting so `p.XX` never splits a sentence mid-citation, and logs `grounding_drop: <sent>` whenever an ungrounded sentence is dropped (`SPEC-08 §6.3`).

### 4. `P2F5-B4` — 20-Question Grounding Suite & `P2F.5 §6` Drop Test (`RESOLVED`)
- [test_grounding_v3.py](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2F/yukti/backend/tests/test_grounding_v3.py#L1-L41) and [test_why.py](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2F/yukti/backend/tests/test_why.py#L58-L118) pass `26/26` tests (`test_grounding_royalty_drop`, `test_why_agent_revenue_fy23`, and all 20 parametrized why-questions in `test_why_agent_20_questions`).
