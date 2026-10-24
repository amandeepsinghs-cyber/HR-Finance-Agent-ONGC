# Yukti v3 Golden Evaluation Suite (`golden_v3`)

This directory houses the numeric golden evaluation dataset and multi-turn scenario chains defined in **SPEC-11 §8** and **BEH-03**. It replaces the legacy shape-only stress tests (`run_30x4_stress_test.py`) with strict numeric, provenance, citation, and multi-turn semantic verification.

---

## 1. Absolute Truth Rule

All numbers in this test suite are copied **verbatim** from official primary sources:
1. **Integrated Annual Reports (Standalone)**: FY17 through FY26 (`ONGC_AR_FYxxxx-xx.pdf`).
2. **Ten-Year Excellence Summary**: AR FY2025-26 printed pages 21–22 (PDF pp. 23–24).
3. **Verified SSOT Database Tables & Views**:
   - `ongc-hr-finance-agent.hrfin_gold.fact_financial_statement_line`
   - `ongc-hr-finance-agent.hrfin_gold.fact_wacc_annual`
   - `ongc-hr-finance-agent.hrfin_gold.fact_wacc_shapley`

> [!IMPORTANT]
> **No Synthetic Guessing / Rounding**: Never compute, round, or extrapolate an expected value unless explicitly mandated by the specification (e.g. `derived_ar` ratios). If an official number is absent in the spec, mark `expect_value: TODO_SPEC_GAP`.

### Tolerance Policy
- **2-decimal AR values**: `±0.05` crore.
- **10-year summary table figures**: `±0.1` crore.
- **Ratios & Percentages**: `±0.05%` (or `±0.01` for Debt-Equity).
- **Production Volumes (MMT / BCM)**: `±0.01`.
- **Headcounts**: `0` (exact integer matching).

---

## 2. Directory Contents

- **`cases_finance.yaml`**:
  - **P1 Gate (39 cases)**: Single-turn core financial questions (`F01–F11`, `F13–F31`, `F37`, `F39–F46`) covering revenue, PAT, PBT, balance sheet totals, cash flows, ROCE, statutory levies, capex, dividends, and production.
  - **P2F Gate (22 cases)**: Financial diagnostics, clarify intents, coverage checks, root-cause waterfalls, WACC series, and top-5 management action levers (`F12`, `F32–F36`, `F47–F48`, `F51–F52`, and `BEH-03.01–BEH-03.12`).
  - **3 Phrasings Per Case**: Canonical English, Colloquial English, and Hindi/Hinglish.
  - **Metadata**: Provenance badge (`verified_ar`, `derived_ar`, `modelled`, `local_snapshot`), and exact printed page citation (`cite.page_label`).

- **`chains.yaml`**:
  - Multi-turn conversational workflows evaluated in a single session with carry-over context.
  - **`V20` Chain (P2F Gate)**: Encodes the 6-step diagnostic flow from BEH-03:
    1. `BEH-03.01` (Clarify on unspecific period)
    2. `BEH-03.03` (5-year comparative statement)
    3. `BEH-03.05` (10-year WACC trend)
    4. `BEH-03.06` (FY23 WACC spike Shapley attribution)
    5. `BEH-03.07` (FY26 PBT decline waterfall bridge)
    6. `BEH-03.09` (Top 5 management action levers)

---

## 3. Self-Checks & Validation

### Python YAML Syntax & Count Verification
Verify that both YAML files parse cleanly without syntax or indentation errors:

```bash
python3 -c "import yaml; d=yaml.safe_load(open('yukti/backend/eval/golden_v3/cases_finance.yaml')); print(f'cases_finance count: {len(d)}')"
python3 -c "import yaml; d=yaml.safe_load(open('yukti/backend/eval/golden_v3/chains.yaml')); print(f'chains count: {len(d)}')"
```

### Reviewer Diff Check
Run the standalone verification script located at `/tmp/verify_golden_diff.py` to assert that every literal value in `cases_finance.yaml` matches the reference table in `SPEC-11 §8.2` and `BEH-03`.

---

## 4. Evaluation Execution (FL Executor)

To run the golden evaluation suite against a live backend instance (port 8095):

```bash
cd "<app root>/yukti/backend"
.venv/bin/python eval/golden_v3/run_golden.py \
  --cases eval/golden_v3/cases_finance.yaml \
  --chains eval/golden_v3/chains.yaml \
  --base-url http://127.0.0.1:8095 \
  --no-cache \
  --report eval/golden_v3/report_P1.md
```

### Release Gate Thresholds (SPEC-11 §9)
| Metric | Threshold | Blocking? |
|---|---|---|
| Wrong number on any KPI line (F-cases, any phrasing) | **0** | Yes |
| Finance case pass rate (all phrasings × both APIs) | ≥ 98% | Yes |
| Chains V20 | 100% of steps | Yes |
| Provenance label correct | 100% | Yes |
| Coverage contradictions | 0 | Yes |
