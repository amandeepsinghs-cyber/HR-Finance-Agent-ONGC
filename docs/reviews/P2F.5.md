# Gate G4 Independent Review — P2F.5 (Grounded "Why" Answers: Variance Rows + AR Chunks, Non-Circular Grounding)

**Verdict:** **CHANGES REQUESTED** (Round 1 — `3089fe2`)

**BLUF:** Commit `3089fe2` on `v3/P2F-fin-diag` deletes the legacy `financial_notes_corpus.jsonl`, `ssot_financial_line_context.json`, and `FY_DIRECTOR_ACTIONS` runtime reads (`SPEC-08 AC-08` ✅) and introduces `app/brain/grounding.py` and `app/agents/fin_diagnostics/why.py`, but **cannot pass Gate G4 yet** due to 4 blocking defects (`P2F5-B1`..`P2F5-B4`):
1. `pipeline.py:141, 296` raises `UnboundLocalError: cannot access local variable 're'` whenever why-intent detection executes, and `"Why did revenue fall in FY23?"` (`SPEC-08 AC-06`) misses `run_why_turn` completely (`plan.spec.metric = "revenue_cr"`) and queries `hrfin_gold.ssot_field_economics_360` instead of standalone revenue.
2. `why.py:54` calls `compiler._latest_df()`, raising `AttributeError: 'Compiler' object has no attribute '_latest_df'` on every invocation of `run_why_turn`.
3. `grounding.py:5` makes the `[AR FYxx p.YY]` page citation optional (`?`) on quotes, allowing any quoted string without a page citation to bypass numeric grounding (`SPEC-08 §6.3`).
4. `test_grounding_v3.py` and `test_why.py` do not include the required 20-question grounding test (`P2F.5 §7`, `SPEC-08 AC-05`) or verify `AC-06`.

---

## Must-Fix Blockers (`P2F5-B1`..`P2F5-B4`)

### 1. `P2F5-B1` (Blocking — `yukti/backend/app/brain/pipeline.py:137-146, 296`): `UnboundLocalError` on `re` & Missing Metric Mapping on `"Why"` Routing (`SPEC-08 AC-05, AC-06`)
- **What is wrong:**
  1. [pipeline.py:296](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2F/yukti/backend/app/brain/pipeline.py#L296) has a local `import re` inside `run_planner_turn`, which shadows the module-level `import re` (line 14) and causes [pipeline.py:141](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2F/yukti/backend/app/brain/pipeline.py#L141) (`if re.search(...)`) to crash with `UnboundLocalError: cannot access local variable 're' where it is not associated with a value`.
  2. When asked `"Why did revenue fall in FY23?"` (`SPEC-08 AC-06`), the planner produces `plan.spec.metric = "revenue_cr"`, which is not in the tuple at [pipeline.py:140](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2F/yukti/backend/app/brain/pipeline.py#L140). As a result, `"Why did revenue fall in FY23?"` bypasses `run_why_turn` and executes `SELECT ... FROM hrfin_gold.ssot_field_economics_360` (field economics), violating `SPEC-08 AC-06`.
- **Required fix:**
  - Delete `import re` at `pipeline.py:296`.
  - In `pipeline.py:137-146`, route to `run_why_turn` whenever `re.search(r"\b(why|what drove|what caused|reason\w*|cause\w*|attribut\w*|how come)\b", query or "", re.I)` matches and `plan.spec` targets corporate financials (`plan.spec.metric in CORP_METRIC_TO_SSOT` or `plan.spec.metric in ("revenue_cr", "pbt_cr", "pat_cr", "ebitda_cr", "pnl_statement")` without a field/asset filter). Remap `"revenue_cr"` (when no field/asset filter is present) to `"corporate_revenue_cr"` (`PL.REV_OPS`, standalone).

### 2. `P2F5-B2` (Blocking — `yukti/backend/app/agents/fin_diagnostics/why.py:27-165`): `AttributeError: 'Compiler' object has no attribute '_latest_df'`, Offline `ARRetriever` Fallback, `coverage='partial'` Sentence & `visual` Contract Schema (`SPEC-08 §6.2`)
- **What is wrong:**
  1. [why.py:54](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2F/yukti/backend/app/agents/fin_diagnostics/why.py#L54) calls `df = compiler._latest_df()`, which raises `AttributeError: 'Compiler' object has no attribute '_latest_df'`.
  2. [why.py:30-43](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2F/yukti/backend/app/agents/fin_diagnostics/why.py#L30-L43) only maps `corporate_revenue_cr` and `corporate_pat_cr`, defaulting all other metrics (e.g. `royalty_cr`, `statutory_levies_cr`, `saed_windfall_tax_cr`, `operating_expenses_cr`, `dda_cr`, `finance_costs_cr`, `other_income_cr`, `exploration_costs_written_off_cr`, `crude_oil_revenue_cr`, `natural_gas_revenue_cr`, `vap_revenue_cr`) to `PL.PBT`. Also `fy_to` should check `resolve_fy(query)` when `spec.period` is absent or defaulted.
  3. [why.py:89-96](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2F/yukti/backend/app/agents/fin_diagnostics/why.py#L89-L96) calls `ARRetriever().retrieve(...)` without catching BigQuery/Vertex network errors when running offline in tests, and does not allow injecting a retriever/chunks for deterministic testing.
  4. [why.py:112-115](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2F/yukti/backend/app/agents/fin_diagnostics/why.py#L112-L115): When `coverage == 'partial'`, `SPEC-08 §6.2 item 3` requires `"₹X crore of the change is not explained by disclosed volume/price data."` (where `X` is the `other_unexplained` row's `impact_inr_cr`).
  5. [why.py:121-155](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2F/yukti/backend/app/agents/fin_diagnostics/why.py#L121-L155): Set `spoken_summary = text` (grounded narrative, not `"Here is the variance analysis."`), include SSOT row lineage (`doc` + `page` from `r.inputs`) in `sources[]` (`SPEC-08 §6.2 item 5`), and format `visual.chart.data` as a `List[Dict[str, Any]]` (with `x_key="line_code"`, `y_keys=["impact"]`) so `validate_and_repair_contract` does not reject `visual.chart.data`.
- **Required fix:**
  - Load `df` from `financial_ssot/out/fact_snapshot.parquet` (via `YUKTI_FIN_SNAPSHOT_PATH` or `Path(__file__).resolve().parents[4] / "financial_ssot" / "out" / "fact_snapshot.parquet"`).
  - Map `spec.metric` via `CORP_METRIC_TO_SSOT` (plus query keyword fallback for specific lines like royalty, SAED, opex, DD&A, finance costs, exchange loss, provisions, crude, gas, VAP) and use `resolve_fy(query)` when present.
  - Wrap `retriever.retrieve(...)` in `try ... except Exception:` with an optional `retriever` parameter on `run_why_turn`.
  - Include the unexplained remainder `₹{abs(r.impact_inr_cr):.1f} crore` when `coverage == "partial"`, set `spoken_summary = text`, populate `sources[]` with SSOT `doc`/`page` + AR `citation`, and use a list of row dicts for `visual.chart.data`.

### 3. `P2F5-B3` (Blocking — `yukti/backend/app/brain/grounding.py:5, 22-74`): Require `[AR FYxx p.N]` Page Citation on Quoted Excerpts & Log `grounding_drop` (`SPEC-08 §6.3`)
- **What is wrong:**
  - [grounding.py:5](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2F/yukti/backend/app/brain/grounding.py#L5) defines `_QUOTE = re.compile(r'"([^"]*)"(?:\s*\[AR\s*FY\d{2}\s*p\.\d+\])?')` with a trailing `?`, which strips **all** double-quoted strings even when they have no `[AR FYxx p.N]` citation. `SPEC-08 §6.3` states: *"A number that appears only inside a verbatim quoted AR excerpt (in quotation marks, with a page cite) is allowed"*.
  - Dropped sentences are not logged with `grounding_drop` (`SPEC-08 §6.3`).
- **Required fix:**
  - Remove the trailing `?` on the citation group in `_QUOTE` (e.g. `_QUOTE = re.compile(r'"([^"]*)"\s*\[AR\s*FY\d{2}(?:\s+PDF)?\s*p\.[^\]]+\]')`) so only quoted AR excerpts accompanied by an `[AR FYxx p.N]` citation are exempted from numeric checks.
  - Log `logger.info("grounding_drop: %s", sent)` whenever a sentence is dropped.

### 4. `P2F5-B4` (Blocking — `yukti/backend/tests/test_grounding_v3.py`, `yukti/backend/tests/agents/test_why.py`): Add 20-Question Grounding Suite & `AC-05` / `AC-06` Assertions (`P2F.5 §7`, `SPEC-08 AC-05, AC-06`)
- **What is wrong:**
  - `test_why.py` only runs 1 question (`"Why did revenue fall in FY23?"`), which did not even enter `run_why_turn`, and does not test the required 20 why-questions (`P2F.5 §7`, `SPEC-08 AC-05`).
- **Required fix:**
  - In `tests/test_grounding_v3.py`, add tests verifying:
    1. Injected `"Royalty rose to ₹15,280 crore."` (not in allowed set) is dropped and logged (`P2F.5 §6`).
    2. A quote without `[AR FYxx p.N]` cite containing an unallowed number is dropped, whereas `"..." [AR FY26 p.98]` is kept.
  - In `tests/agents/test_why.py`, add:
    1. Explicit `AC-06` test on `"Why did revenue fall in FY23?"` asserting that `run_why_turn` runs against standalone `PL.REV_OPS`, `hrfin_gold.ssot_field_economics_360` is NOT in `sources`, and `"Mumbai High"` / `"Bassein"` do not appear in the contract.
    2. A 20-question parametrized grounding test across 20 why-questions (covering FY18–FY26 and lines: PBT, PAT, revenue, crude revenue, gas revenue, VAP revenue, statutory levies, royalty, SAED, opex, DD&A, finance costs, exchange loss, provisions, other income, exploration write-offs) asserting that **0 numbers outside the turn's allowed set** appear in `display_text` or `spoken_summary`, and when AR chunks are returned, at least 1 `[AR FY... p....]` citation appears (`SPEC-08 AC-05`).
