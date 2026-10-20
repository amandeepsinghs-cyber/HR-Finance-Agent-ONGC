# Reference facts for the 2026-10-20 semantic audit (verified live in BigQuery)

Demo "today" = **2026-10-19** (FY27, month 7). Indian FY = Apr–Mar (FY26 = 2025-04 … 2026-03). All tables use `fiscal_year` codes like `FY26` (the `'2026'` alternates in old SQL never match anything — harmless but remove when touching a query).

## Stock vs flow
| Measure | Kind | Correct aggregation across time |
|---|---|---|
| `headcount_snapshot.headcount / active_headcount` | stock | take ONE month (FY-end = `month='YYYY-03'`, or latest `2026-09` for "now"); never SUM across months |
| `contract_workforce.contractor_headcount`, `regular_employee_count_matching` | stock (monthly) | FY-end month or AVG of monthly totals; SUM over months = person-months |
| `production_monthly.active_producing_wells / active_injection_wells` | stock | FY-end month or average monthly; never SUM |
| `receivables.outstanding_amount_inr_cr` | balance | as-of; only FY26 invoices carry non-zero outstanding (see data notes) |
| `benefit_liabilities.*liability*, plan_assets, funded_ratio` | balance | one FY (FY26) — never SUM across FY |
| `sanctioned_posts.*strength*, vacancy_count` | stock | FY26 only exists; fine |
| `reserves_annual.reserves_*` | balance | FY-end; never SUM across FY (annual_production_mmtoe is a flow) |
| `employee_master` | current state | Active = `employment_status='Active'` → 22,798 today |
| production volumes, revenue, costs, payroll, incidents, separations | flows | SUM within a period; compare periods with equal month coverage (FY27 has only 6 months: 2026-04..2026-09) |

## Anchors (sanity bounds)
- Company headcount 31-Mar-2026 (`headcount_snapshot` month `2026-03`) = **23,117**; sanctioned 25,149, vacancies 2,032 (FY26).
- Headcount 31-Mar-2021 = 28,479; 31-Mar-2025 = 24,368; latest snapshot 2026-09 = 22,803; `employee_master` Active = 22,798; `v_headcount_asof` as_of 2026-10-19 = 22,798.
- `headcount_snapshot` has only ONE month per FY for FY13–FY21 (March) and 12 months for FY22–FY26, 6 for FY27 → any SUM(headcount) by FY is wrong and unequal.
- 46 work centres; 15 producing assets in production_monthly (`asset_wc_id`).
- FY26 standalone gross revenue = **₹1,32,508 cr** (`corporate_financials`); PAT ₹32,894 cr; employee cost ₹10,211 cr.
- `field_pnl_annual` FY26: line_type `field` (53 rows) + `plant_vap` (3) + `reconciliation` (1) + `unallocated_corporate` + `exploration_writeoff` → filter `line_type='field'` for field rankings; revenue reconciles to 1,32,508 only when all line types are included.
- FY26 production: 296.64 MMboe = 40.47 MMTOE; oil 19.525 MMT, condensate 0.977 MMT, gas 19.967 BCM. Use `total_production_boe` (BOE) or MMTOE = BOE / 7.33e6 (`metric_definitions` MET-OPS-005). Never add MMT to BCM.
- FX FY26 avg 88.33 INR/USD; Brent FY26 avg $70.90.
- Units: `*_inr_cr` = crore; `*_inr` = rupees (÷1e7 → crore); `penalty_inr_lakh` = lakh (÷100 → crore).
- `metric_definitions` (hrfin_gold) gives canonical expressions; `glossary`: BOE ≈ 7.33 BOE per tonne oil-equivalent.

## Known multi-grain / fan-out risks
- `hrfin_gold.mart_corporate_performance`, `mart_workforce`, `mart_field_economics`, `mart_postings`, `mart_payroll_benefits`, `mart_governance_audit` are wide union/join marts: aggregating a measure without restricting to the right record grain multiplies it.
- `mart_asset_productivity.regular_headcount` is 0 for FY17–FY21 and sums to 18,033 (15 assets) for FY26.
- `posting_history` is SCD2-like: restrict to `is_current_posting` or an as-of date window.
