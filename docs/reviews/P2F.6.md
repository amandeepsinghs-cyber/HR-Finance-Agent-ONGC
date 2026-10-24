# P2F.6 Independent G4 Review — Top-5 Action Generator, Safe AST (`expr.py`), and Delegation Table

- **Reviewer:** `reviewer-p2h2` (independent G4 reviewer; fresh context)
- **Commits Under Review:** `1d0fffa` (`levers.yaml`) + `6d645f2` (`expr.py`, `actions.py`, `levers_fixture.yaml`, `test_actions.py`) on branch `v3/P2F-fin-diag`
- **Worktree:** `/usr/local/google/home/amandeepsinghs/o&g agentic transformation/Oil & Gas Agent Portfolio/cloud_run_apps/HR and Finance_ONGC__v3P2F`
- **Reference Specs:** `docs/delegation/packets/v3/P2F.6_top5_action_generator.md`, `docs/specs/SPEC-08_v20_finance_diagnostics.md` §7
- **Verdict:** **CHANGES REQUESTED** (3 blocking items: `P2F6-B1`..`P2F6-B3`)

---

## 1. Executive Summary (BLUF)

**Request changes on `P2F.6` (`6d645f2`): while all 12 unit tests in `test_actions.py` pass against the synthetic fixture, `generate_actions()` fails to evaluate key levers (`L02`, `L03`, `L05`) against the real `financial_ssot/out/fact_snapshot.parquet` (including the flagship `L02` Debtor Days lever), omits `yoy`/`avg5`/`median5` multi-year inputs from `evidence[]`, and is missing keyword/arity guards in `expr.py` plus package exports in `fin_diagnostics/__init__.py`.**

Resolving the 3 blocking items below (`P2F6-B1`..`P2F6-B3`) is required before `P2F.6` can pass Gate G4 and integrate cleanly with `P2F.7` (`fin_diagnostics` agent).

---

## 2. Blocking Findings (Must Fix for G4 Approval)

### `P2F6-B1` (Blocking — `actions.py:52-98`): `_lookup_cell` fails on real `fact_snapshot.parquet` for `L02` (`RATIO.DEBTOR_DAYS`), `L03` (`PROD.TOTAL_BOE`), and `L05` (`BS.CWIP_TOTAL`), and lacks `period_type == "annual"` filtering

- **Location:** [actions.py](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2F/yukti/backend/app/agents/fin_diagnostics/actions.py#L36-L98)
- **What breaks & why:**
  When `generate_actions(df, fy="FY26", prior_fy="FY25", persona="CMD")` is executed against the actual `financial_ssot/out/fact_snapshot.parquet`:
  1. **`val_col` selection bug (`actions.py:83-85`) drops all ratio, count, and physical-production rows (`L02`, `L03`):**
     ```python
     val_col = "value_inr_cr" if "value_inr_cr" in row else ("value" if "value" in row else None)
     val = float(row[val_col]) if val_col and pd.notna(row[val_col]) else None
     ```
     In `fact_snapshot.parquet`, `"value_inr_cr"` is a column on every row (`"value_inr_cr" in row` is always `True`), and is `NaN` for all non-monetary rows (`RATIO.DEBTORS_TURNOVER_DAYS`, `PROD.*`, `OTH.EMPLOYEES`), which store their numeric values (`32.0`, `29.0`, `19.332`, `23117.0`) in `row["value"]`. Consequently, `_lookup_cell(df, "RATIO.DEBTOR_DAYS", "FY26")` returns `(None, None)` and **even the #1 flagship example in `Packet P2F.6 §6` and `SPEC-08 §7.3` (`L02`: *"Bring debtor days from 32 back to 29"*) fails to trigger on `fact_snapshot.parquet`**.
  2. **Missing `period_type == "annual"` filter (`actions.py:63-70`):**
     `_lookup_cell` filters only by `fiscal_year == fy` and `scope == "standalone"`, without filtering `period_type == "annual"` when the `period_type` column is present.
  3. **Missing composite SSOT synthesis for `BS.CWIP_TOTAL` (`L05`) and `PROD.TOTAL_BOE` (`L03`):**
     - In `fact_snapshot.parquet`, CWIP is stored as three component lines (`BS.CWIP_DEV_WELLS`, `BS.CWIP_OG_FACILITIES`, `BS.CWIP_OTHER` — e.g. FY26: `16667.8 + 15743.9 + 1419.5 = 33831.2` cr; FY25: `13380.6 + 21520.9 + 1705.2 = 36606.7` cr), with no single `BS.CWIP_TOTAL` or `BS.CWIP` row.
     - Similarly, production is stored as `PROD.CRUDE_ONGC` (`MMT`), `PROD.CRUDE_JV` (`MMT`), `PROD.GAS_ONGC` (`BCM`), and `PROD.GAS_JV` (`BCM`), with no single `PROD.TOTAL_BOE` row.
- **Required Fix:**
  1. In `_lookup_cell` (`actions.py:83-85`), select the first non-null numeric column across `("value_inr_cr", "value", "value_native")`:
     ```python
     val = None
     for col in ("value_inr_cr", "value", "value_native"):
         if col in row and pd.notna(row[col]):
             val = float(row[col])
             break
     ```
  2. Filter `if "period_type" in sub.columns: sub = sub[sub["period_type"] == "annual"]` when non-empty.
  3. Add composite fallback synthesis in `_lookup_cell` when direct alias lookup returns `(None, None)`:
     - If `var_name == "BS.CWIP_TOTAL"`: sum `("BS.CWIP_DEV_WELLS", "BS.CWIP_OG_FACILITIES", "BS.CWIP_OTHER")` for `fy` when present.
     - If `var_name == "PROD.TOTAL_BOE"`: synthesize from `PROD.CRUDE_ONGC`, `PROD.CRUDE_JV`, `PROD.GAS_ONGC`, `PROD.GAS_JV` (or `PROD.CRUDE_ONGC + PROD.GAS_ONGC`) when present so `L03` evaluates cleanly on `fact_snapshot.parquet`.

---

### `P2F6-B2` (Blocking — `actions.py:245-261`): `evidence[]` omits `yoy(...)`, `avg5(...)`, and `median5(...)` historical data citations

- **Location:** [actions.py](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2F/yukti/backend/app/agents/fin_diagnostics/actions.py#L245-L261)
- **What breaks & why:**
  `Packet P2F.6 §5.4` requires:
  > *"`what_to_do` is filled from the template with numbers formatted Indian-style (₹ cr, 1 dp); every number used is added to `evidence` as `{type:'data', ref:'<line_code> <FY> = <value> (<source_doc> p.<page>)'}`."*
  Look at `actions.py:252-254`:
  ```python
  used_years = [fy]
  if prior_y and ("prior" in trigger_expr or "prior" in mid_expr or "prior" in lever.get("what_to_do_template", "")):
      used_years.append(prior_y)
  ```
  - Levers `L04`, `L07`, and `L09` use `yoy(...)` in `trigger_expr`, and `L04` does not contain the substring `"prior"` anywhere in `trigger_expr`, `mid_expr`, or `what_to_do_template` — so `prior_y` (`FY25`) is **omitted** from `evidence` for `L04` even though `yoy(PL.EXPL_WRITEOFF)` depends on `FY25`!
  - Levers `L01`, `L05`, and `L06` use `avg5(...)` or `median5(...)` across `window_fys` (`FY22..FY26`), and their `what_to_do` templates print the 5-yr average/median number, yet none of the prior window years (`FY22..FY25`) are included in `used_years`!
  - Furthermore, if a lever uses `avg5(...)` or `median5(...)` and one of the 5 window years (`FY22..FY25`) is missing from `df`, `_eval_ast` raises `ExprError("Unknown name in expression")` unless all 5 years are present or `avg5`/`median5` checks/requires the window years cleanly.
- **Required Fix:**
  In `actions.py:251-256`:
  1. Combine all expression texts for the lever (`all_expr_text = " ".join([trigger_expr, low_expr, mid_expr, high_expr, lever.get("what_to_do_template", ""), lever.get("ask_template", "")])`).
  2. Append `prior_y` to `used_years` when `prior_y` is present and (`"prior"` in `all_expr_text` or `"yoy"` in `all_expr_text`).
  3. Append `[y for y in window_fys if y not in used_years]` when `"avg5"` in `all_expr_text` or `"median5"` in `all_expr_text`.

---

### `P2F6-B3` (Blocking — `expr.py:186-240` & `fin_diagnostics/__init__.py`): Missing keyword-arg / arity validation in `expr.py` AST evaluator and missing public exports in `fin_diagnostics/__init__.py`

- **Location:**
  - [expr.py](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2F/yukti/backend/app/agents/fin_diagnostics/expr.py#L186-L240)
  - [`__init__.py`](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2F/yukti/backend/app/agents/fin_diagnostics/__init__.py#L1-L4)
- **What breaks & why:**
  1. In `expr.py:186-240` (`isinstance(node, ast.Call)`):
     - `node.keywords` is never checked (`if node.keywords: raise ExprError("Keyword arguments are not allowed in expressions")`).
     - In `expr.py:218`, `arg_node = node.args[0]` is indexed without checking `if len(node.args) != 1: raise ExprError(f"{func_name}() takes exactly 1 argument")`, causing a raw `IndexError` instead of `ExprError` on `prior()` or `yoy()` with 0 args, and silently ignoring extra positional args on `prior(a, b)`.
     - Similarly, `abs(x)` at `expr.py:209` requires `len(node.args) == 1`, and `min`/`max` at `expr.py:211-214` require `len(node.args) >= 1`.
     - If an input expression literally contains `_VAR_` before substitution (`expr.py:85`), reject it with `ExprError` so callers cannot forge internal placeholder identifiers.
  2. In `yukti/backend/app/agents/fin_diagnostics/__init__.py`, only `attribute` and `pbt_bridge` are exported (`__all__ = ["attribute", "pbt_bridge"]`). Export `generate_actions`, `evaluate`, and `ExprError` so `P2F.7` can import from `app.agents.fin_diagnostics`.

---

## 3. Checklist Verification Summary (`Packet P2F.6 §6`)

| Requirement | Status | Notes |
| :--- | :---: | :--- |
| Safe AST evaluator (`expr.py`): no `eval()`/`exec()`, rejects `Attribute`, non-whitelisted `Call`, `Subscript`, `Lambda`, `Import` | **PARTIAL (`P2F6-B3`)** | Rejects forbidden AST nodes; needs keyword-arg/arity checks and `_VAR_` literal guard |
| `levers.yaml`: 10 levers (`L01`..`L10`), valid YAML, only whitelisted `expr.py` syntax | **PASS** | All 10 levers match `SPEC-08 §7.2` and parse cleanly through `expr.py` |
| Triggered levers sorted by `impact_inr_cr.mid` desc, tie-broken by lever ID asc | **PASS** | Verified in `actions.py:276` and `test_actions.py` |
| Owner diversity rule (`<= 3` actions from same `owner.role`) | **PASS** | Verified in `actions.py:282-304` and `test_owner_diversity_max_3` |
| `DIR_HR` persona forces inclusion of `L07` if triggered | **PASS** | Verified in `actions.py:285-294` and `test_dir_hr_includes_l07` |
| `E1..E4` personas receive `"for discussion"` owner role (`BEH-01`) | **PASS** | Verified in `actions.py:309-316` and `test_e1_e4_owner_for_discussion` |
| `ar_evidence_fn` injected as deterministic mock in tests; no network/LLM call | **PASS** | Verified in `actions.py:263-267` and `test_ar_evidence_fn_injected` |
| `< 5` triggered levers emits explicit note (never pads with untriggered levers) | **PASS** | Verified in `actions.py:332-338` and `test_fewer_than_5_triggers_adds_note` |
| Output validates against `docs/contracts/action_card.schema.json` | **PASS** | Verified in `test_all_outputs_validate_against_schema` |
| Works against real `financial_ssot/out/fact_snapshot.parquet` & full `evidence[]` | **FAIL (`P2F6-B1`, `P2F6-B2`)** | Fails on `L02`/`L03`/`L05` on real parquet; omits `yoy`/`avg5`/`median5` window refs from `evidence[]` |
