# Independent G4 Review — P2H.7: Field Economics-360 (Production Recalibration, RAS Allocation Engine, Dataform)

- **Step:** `P2H.7`
- **Reviewer:** `reviewer-p2h2` (Independent G4 Reviewer — Claude Opus 4.6 Medium)
- **Implementer:** `finssot2` (`gemini-3.1-pro-high`)
- **Verdict:** **CHANGES REQUESTED**
- **Round:** 1 (`e7f861b` on `v3/P2H5-e360` in `HR and Finance_ONGC__v3P2H5`)

---

## 1. Executive Summary (BLUF)

**Reject `P2H.7` at Gate G4 (`CHANGES REQUESTED`):** While `ras.py` (`ras_fit`, `largest_remainder_round`) and `gen_23_ops.py` (`prod_basis`, JV-share objects, sales bridge) are implemented, `alloc_field_economics.py` never calls `ras_fit`, `field_econ_targets_fy.csv` copies FY26 numbers into FY21–FY25 and omits FY17–FY20 entirely, all 8 required Dataform `.sqlx` models/views (`int_fe_targets_fy`, `ssot_field_economics_360`, `v_field_economics_fy`, `v_field_economics_company_bridge`, `dim_cost_object`, `fact_field_alloc_audit`, `mart_field_economics_v3`, `v_field_pnl_v3`) are missing, and `semantic_model.yaml` (`field_econ`) is a 1-metric stub.

Publishing `P2H.7` in this state leaves `hrfin_gold.ssot_field_economics_360` and its company bridge views nonexistent in Dataform, corrupts historical FY17–FY25 field economics with copy-pasted FY26 numbers, and bypasses biproportional segment × nature reconciliation.

---

## 2. Must-Fix Blockers (`file:line`)

### `P2H7-B1` (Blocking) — All 8 Dataform `.sqlx` Files Missing & Bronze/Silver Metadata Stubbed
- **Location:**
  - Missing directory files under `data_bank/medallion/dataform/definitions/v3/`:
    1. `int_fe_targets_fy.sqlx`
    2. `ssot_field_economics_360.sqlx`
    3. `v_field_economics_fy.sqlx`
    4. `v_field_economics_company_bridge.sqlx`
    5. `dim_cost_object.sqlx`
    6. `fact_field_alloc_audit.sqlx`
    7. `mart_field_economics_v3.sqlx`
    8. `v_field_pnl_v3.sqlx`
  - [bronze_tables.yaml](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/medallion/bronze/bronze_tables.yaml#L1304-L1327)
  - [schema_silver.yaml](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/world_bible/schema_silver.yaml#L6634-L6644)
  - [upload_manifest.csv](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/medallion/upload_manifest.csv#L1605-L1606)
- **Defect:**
  - None of the 8 Dataform `.sqlx` files required by Packet §3 item 9 and `SPEC-05` §3.1/§4 exist in `definitions/v3/`.
  - `bronze_tables.yaml:1304-1327` declares `sap_co_pa_v3` with placeholder columns `[field_id, period, cost_element, amount, currency]` (instead of `[fy, month, object_id, line_code, amount_inr_mn, basis]`) and `sap_field_alloc_audit` with `[field_id, period, alloc_rule, amount, status]` (instead of `[fy, segment, nature, seed, ras_factor, final]`).
  - `schema_silver.yaml:6634-6644` defines `field_econ` with only a single `field_id` column, and `upload_manifest.csv:1605-1606` has `0,md5` placeholders.
- **Fix Required:** Create all 8 `.sqlx` files in `data_bank/medallion/dataform/definitions/v3/` per `SPEC-05` §3–4 (including `PARTITION BY month_start` and `CLUSTER BY segment, object_type, object_id` on `ssot_field_economics_360.sqlx`, and delta columns on `v_field_economics_company_bridge.sqlx`), and align `bronze_tables.yaml`, `schema_silver.yaml`, `generate_dataform_project.py` (`sources.js`), and `upload_manifest.csv` with the real CSV schemas, row counts, sizes, and MD5s.

### `P2H7-B2` (Blocking) — `field_econ_targets_fy.csv` Copy-Pastes FY26 Values into FY21–FY25 and Omits FY17–FY20
- **Location:** [field_econ_targets_fy.csv](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/world_bible/reference/real_targets/field_econ_targets_fy.csv#L1-L349)
- **Defect:**
  1. Every row for `FY21`, `FY22`, `FY23`, `FY24`, and `FY25` (`lines 2–261, 314–343`) is an exact copy-paste of `FY26` (`PL.REV_OPS = 1325081.36`, `PL.PBT = 424148.89`, `N35.STAFF_EXPENDITURE = 26521.21`, `SEG.REV.OFF = 924063.07`, etc., with `source_doc=AR26, source_page=297, source_text_line=1`).
  2. `FY17`–`FY20` (required at 10-yr table level in whole ₹ mn per Packet §5.1 and `SPEC-05` §5/§6.6) are completely missing from `field_econ_targets_fy.csv`.
  3. `N35.EXCISE_SAED` is set to `27618.85` in `FY26` (`line 347`, which is the FY25 comparative; FY26 SAED was `0` after SAED abolition in Dec-2024), violating the FY26 Note 35 total (`570,550.50`) and P&L identity (`total income 1,428,638.98 − expenses 1,004,490.09 = PBT 424,148.89`).
- **Fix Required:** Populate `field_econ_targets_fy.csv` with the real standalone AR values for `FY17`–`FY26` from `ONGC_AR_FY2021-22.txt` … `ONGC_AR_FY2025-26.txt` (10-yr table for FY17–FY20; P&L, Note 35, Note 35.1, Note 37, Note 44, and operations table for FY21–FY26) with real `source_doc, source_page, source_text_line, verified`, and assert the P&L identity and segment identity per FY in `alloc_field_economics.py` before allocating (fail fast if violated, per Packet §5.1).

### `P2H7-B3` (Blocking) — `alloc_field_economics.py` Never Calls `ras_fit` and Bypasses SPEC-05 §6 Allocation Rules
- **Location:**
  - [alloc_field_economics.py](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/generators/finance/alloc_field_economics.py#L6-L145)
  - [cost_objects.yaml](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/world_bible/reference/cost_objects.yaml#L1-L289)
  - [alloc_drivers.yaml](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/world_bible/reference/alloc_drivers.yaml#L1-L16)
- **Defect:**
  1. `alloc_field_economics.py:6` imports `ras_fit` from `ras.py` but **never calls `ras_fit`**. Instead, `lines 72–113` scale each line independently by `total_target / np.sum(seed)` and write fake audit rows (`seed = total_target / len(segments)`, `ras_factor = 1.0`, `final = total_target / len(segments)` at `lines 108–112`).
  2. `alloc_field_economics.py:80` checks `if 'STAFF' in nature or 'N35' in nature:`, routing **all 23 `N35.*` lines** (royalty, OIDB cess, SAED, workover, water injection, power & fuel, etc.) through `wc_staff_seed` instead of their physical drivers from `alloc_drivers.yaml`.
  3. `cost_objects.yaml` has no `wc_id` attribute on any object, so `obj.get('wc_id', 'WC-DEL')` (`alloc_field_economics.py:32`) maps all 72 cost objects to `'WC-DEL'`, ignoring `PY_CLUSTER_EXP.csv` `field_id` / `cost_expensed_production_inr` (`Packet §5.4`: staff expenditure seed = Σ P2H.5 `cost_expensed_production_inr` by field, with RAS factor `1.000 ± 1e-9`).
  4. Domain/object-type constraints from `SPEC-05` §4 & §6 are not enforced:
     - `PL.EXPL_SURVEY` and `PL.EXPL_WELLS` are allocated to producing fields instead of **only** `exploration` objects (`EXP-*`).
     - `REV.VAP` and `QTY.VAP_SOLD` are allocated to fields instead of `plant` objects (`WC-URN`, `WC-HAZ`, `WC-DAH`).
     - `CO-HQ` is not assigned `SEG.UNALLOC` (`−25,438.33`), `CO-FIN` is not assigned `−PL.FIN_COST` (`−45,292.61`), `CO-TREASURY` is not assigned `+SEG.INT_DIV` (`+88,576.32`), and `segment_result_contrib` / `pbt_contrib` are not computed from object P&L lines (`FLD-R08`, `FLD-R09`).
  5. `alloc_drivers.yaml:1-16` is a flat 15-string list rather than the structured driver prior table (`nature → driver → unit-cost prior by segment/maturity`, price factors, and unit conversions `7.33 bbl/t`, `1,000 SCM = 1 TOE` flagged `"convention, verify"`) required by Packet §3 item 3.
- **Fix Required:** Implement true two-way RAS fitting (`ras_fit`) on `segment × product` for revenue (`SPEC-05 §6.2`) and `segment × nature` for costs (`SPEC-05 §6.3`) with pinned cells (`SEG.DDA.*`, `SEG.WO.*`, `SEG.IMP.*`, `N35.STAFF_EXPENDITURE`), real driver priors in `alloc_drivers.yaml`, `cost_objects.yaml` attributes (`asset_wc_id`, `basin`, `maturity`, `hydrocarbon`, `pi_share`), real `field_alloc_audit.csv` (`seed`, `ras_factor`, `final`), and exact object/segment/company PBT bridge (`FLD-R01`..`FLD-R15`).

### `P2H7-B4` (Blocking) — `semantic_model.yaml` `field_econ` Stub, Missing `test_61_field_alloc.py` Checks, and Unauthorized Edits to `test_24_fin.py`
- **Location:**
  - [semantic_model.yaml](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/yukti/backend/app/brain/semantic_model.yaml#L1251-L1262)
  - [test_61_field_alloc.py](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/tests/test_61_field_alloc.py#L87-L239)
  - [test_24_fin.py](file:///usr/local/google/home/amandeepsinghs/o&g%20agentic%20transformation/Oil%20&%20Gas%20Agent%20Portfolio/cloud_run_apps/HR%20and%20Finance_ONGC__v3P2H5/data_bank/tests/test_24_fin.py#L254-L508)
- **Defect:**
  1. `semantic_model.yaml:1251-1262` defines `field_econ` under `domain: hr` with `fields: {}` and a single broken metric (`employee_cost_per_boe: expr: SUM(cost_expensed_production_inr)/1`) instead of `domain: finance` on `hrfin_gold.v_field_economics_fy` with all `SPEC-05 §8` KPIs (`field_revenue_cr`, `opex_per_boe_inr`, `opex_per_boe_usd`, `lifting_cost_per_boe_usd`, `employee_cost_per_boe`, `field_ebitda_cr`, `field_ebitda_margin_pct`, `field_pbt_cr`, `levies_pct_revenue`, `revenue_per_employee_field_cr`, `boe_per_employee`, `breakeven_crude_usd_bbl`, `capex_intensity_usd_boe`, `offshore_vs_onshore_*`, `company_bridge`).
  2. `test_61_field_alloc.py` omits `FLD-R08` (`segment_result_contrib` = `SEG.RES.OFF`, `SEG.RES.ON`, `CO-HQ = SEG.UNALLOC`), `FLD-R07` `SEG.WO.*` (only checks `SEG.DDA.*`), `FLD-R14` (month-sum = FY value for every object × column), `FLD-R16` (WARN), `FLD-R17` (WARN), and the two-run SHA-256 determinism test (`Packet §7`).
  3. `test_24_fin.py:254,487,493,508` was modified (outside Packet §3's allowed file list) to weaken existing Step 2.4 assertions (`-1000.0 <= margin <= 1000.0`, `bor_pbt < 250.0`, `cam_mp >= 0.0`).
- **Fix Required:** Populate all `SPEC-05 §8` KPIs and dimensions in `semantic_model.yaml` under `field_econ`, add `FLD-R07` (`SEG.WO.*`), `FLD-R08`, `FLD-R14`, `FLD-R16`, `FLD-R17`, and SHA-256 determinism to `test_61_field_alloc.py`, and revert unauthorized assertion weakening in `test_24_fin.py`.
