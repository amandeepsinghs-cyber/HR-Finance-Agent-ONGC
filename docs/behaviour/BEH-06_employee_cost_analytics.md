# BEH-06: Employee Cost & Field Economics Analytics (conversation scripts)

**Features:** FEAT-021 (Employee-360), FEAT-022 (Field Economics-360), FEAT-017 (11 personas, `self`), FEAT-032 (provenance labels) · **Specs:** SPEC-04, SPEC-05, SPEC-06 · **Verbatims:** V14, V17, V23 · **Status:** Draft v3 (23-Oct-2026)

> **BLUF.** 40 Given/When/Then scenarios define what Yukti must answer from `ssot_employee_360` and `ssot_field_economics_360`. Each one fixes the numbers, the visual type, the provenance label and the RBAC outcome for the 11 personas.
> **Company-level numbers are real and exact** (AR FY26: employee cost ₹10,210.71 cr, 23,117 employees, revenue/employee ₹5.581 cr = revenue from operations ÷ average of opening and closing headcount, 1,32,508 ÷ avg(24,368, 23,117), labelled "Derived from AR"). Below company level, numbers are **synthetic/modelled** and say so.
> **Juniors** get pay aggregates (k ≥ 5) and their **own** payslip. They are refused other people's pay with a useful alternative.
> These scenarios are the G3 golden set for P2H.6–P2H.8 and the G5 demo script.

## Conventions
- **Persona names:** CMD "Arun"; E2_HR = EMP-102451 "Pooja Verma"; E3_FIN = the seeded "Rajesh Kulkarni" row (SPEC-06 §4.1). Other ids are seeded per SPEC-06.
- **RBAC outcomes** (SPEC-06 §4.3): **A** allow · **AGG** aggregate (grade/WC; cells < 5 → "<5"; no names) · **SELF** own rows · **R** refuse + alternative.
- **Labels** (BUILD.md §3 principle 2): `Real · AR FY26 p.N`, `Modelled`, `Synthetic`, `Illustrative`, `Scenario`. A wrong label fails the scenario.
- **Golden values:** "≈" means ± 0.5 % unless stated. Synthetic values are asserted as *formula-consistent* (recomputed from the SSOT in the test), not as fixed numbers.
- **Visual types** are from the SPEC-09 catalogue: `kpi_card`, `table`, `payslip` (table preset), `column`, `bar`, `line`, `combo`, `stacked_column`, `stacked_100`, `waterfall`, `donut`, `box`, `roster`, `recon_table` (table preset with a status column).
- **Real FY26 anchors (₹ cr):**
  - Note 35.1 employee cost: Salaries 7,605.51; PF & other funds 1,033.66; Gratuity 259.26; Leave 155.04; PRMB & terminal 874.12; Staff welfare 283.12; **Total 10,210.71**.
  - Note 35 Staff Expenditure 2,652.12.
  - Segment revenue: Offshore 92,406.31, Onshore 40,101.83. Segment result: Offshore 34,384.65, Onshore 6,245.70.
  - Unallocated −2,543.83; Finance cost −4,529.26; Interest/dividend income +8,857.63; **PBT 42,414.89**.

---

## A. Pay structure & entry pay

### BEH-06.01 Entry pay of an E1 officer joining now (CMD)
- **Given** persona CMD; SSOT published; current IDA row = 56.3 % (`status=illustrative`); Delhi = X class (HRA 30 % at IDA ≥ 50 %).
- **When** "What will be the salary breakdown of an E1 officer joining now in Delhi?"
- **Then** the answer is built from the rule (SPEC-04 §6.4), **not** the incumbent average:
  - Monthly: Basic ₹60,000; IDA ₹33,780; HRA ₹18,000; Cafeteria ₹21,000; Gross ₹1,32,780.
  - Annual run-rate CTC ≈ ₹21–23 L, adding PRP (40 % ceiling × kitty), employer CPF 12 %, PRBS, gratuity, PRMB and medical.
  - Notes: "E1 scale ₹60,000–1,80,000 (ONGC recruitment advert); ONGC quotes CTC ≈ ₹24–25 L"; "IDA rate is illustrative pending DPE OM".
- **Visual** `waterfall` (Basic → +IDA → +HRA → +Cafeteria = Gross → +employer benefits = CTC) + `table` · **Label** Rule-based (Real scale), IDA Illustrative · **RBAC** A · **Refs** FEAT-021, SPEC-04 §5.1, §6.4, BUG-26

### BEH-06.02 Same question from a junior (E2_HR)
- **Given** persona E2_HR. **When** the same utterance as .01. **Then** an identical answer (a public scale is `pay_aggregate`, not refused; fixes BUG-28).
- **Visual** as .01 · **RBAC** A · **Refs** SPEC-06 §4.3 (`pay_aggregate`)

### BEH-06.03 Average CTC by grade (CMD)
- **When** "Show average CTC by grade."
- **Then** average `ctc_annualised_inr` of month-end active employees by grade, ordered by `grade_level_order` (GRP-D … GRP-B, E0 … E9, DIR, CMD). Values in ₹ lakh with n per bar.
- **Visual** `column` (ordered axis; BUG-34) · **Label** Synthetic · **RBAC** A · **Refs** SPEC-04 §8 `ctc_per_grade_avg_lakh`

### BEH-06.04 Average CTC by grade (E3_FIN)
- **When** as .03. **Then** the same chart, but bars with n < 5 (CMD = 1, DIR = 2) show "<5" and no value. Narration says "small groups hidden for privacy".
- **Visual** `column` · **RBAC** A (k ≥ 5) · **Refs** SPEC-06 §4.3

### BEH-06.05 Component mix by grade (DIR_HR)
- **When** "Divide E1 to E4 pay into basic, DA, HRA, perks and allowances."
- **Then** per-employee **monthly averages** (never pool totals unless asked; feedback1) by component for E1–E4, from `v_employee_pay_component_long`. Gross per grade = Σ components exactly (no rescaling; BUG-26).
- **Visual** `stacked_column` + `table` · **Label** Synthetic · **RBAC** A · **Refs** SPEC-04 §4 F

### BEH-06.06 "Do the math" follow-up (DIR_HR)
- **Given** .05 answered. **When** "Now show the annual figure per person."
- **Then** the same components × months on roll in FY26 (from `v_employee_360_fy`). It explains partial-year employees ("annual = Σ actual months, not 12 × monthly"). No crore totals.
- **Visual** `table` · **RBAC** A · **Refs** SPEC-04 §9

## B. Company-level cost & productivity (real)

### BEH-06.07 Revenue per employee, 10 years (CMD)
- **When** "Show revenue per employee trend for the last 10 years."
- **Then** revenue from operations / avg headcount (AR basis), in ₹ cr: FY17 2.305 · FY18 2.579 · FY19 3.463 · FY20 3.146 · FY21 2.326 · FY22 3.966 · FY23 5.851 · FY24 5.340 · FY25 5.490 · FY26 **5.581**. Insight: "2.4× in 10 years: revenue up 70 %, headcount down 31 %".
- **Visual** `line` · **Label** Derived from AR (formula over real AR lines) · AR FY26 10-yr p.23–24 (FY16 headcount from AR FY22) · **RBAC** A (all 11) · **Refs** SPEC-04 §8

### BEH-06.08 Employee cost as % of revenue (DIR_FIN)
- **When** "Employee cost as a percentage of revenue over 10 years."
- **Then** bars = employee cost ₹ cr (FY17 11,550.8 … FY26 10,210.7); line = %: FY17 14.83 · FY21 14.86 · FY22 10.04 · FY23 6.83 · FY24 7.61 · FY25 7.78 · FY26 **7.71**.
- **Visual** `combo` · **Label** Derived from AR · **RBAC** A · **Refs** SPEC-04 §8

### BEH-06.09 Cost per employee (CMD)
- **When** "What is our cost per employee and how has it moved?"
- **Then** FY26 **₹43.01 L** (10,210.71 cr / 23,742.5 avg) vs FY17 ₹34.18 L. CAGR 2.6 %. Notes that IDA moved in the meantime.
- **Visual** `kpi_card` + `line` · **Label** Derived from AR · **RBAC** A · **Refs** SPEC-04 §8

### BEH-06.10 FY26 employee cost breakdown (DIR_HR)
- **When** "Break up FY26 employee cost."
- **Then** the six Note 35.1 lines (anchors above), total ₹10,210.71 cr, with page cite.
- **Visual** `waterfall` (or `donut` on "as a pie") · **Label** Real · AR FY26 Note 35.1 p.354 · **RBAC** A · **Refs** SPEC-04 §7.4 EMP-R01..R07

### BEH-06.11 Does Employee-360 add up? (DIR_FIN)
- **When** "Does the employee table add up to the annual report?"
- **Then** a recon table for FY21–FY26: Σ employee rows, Σ each pool (`POOL_RETIREE_PRMB`, `POOL_NON_REGULAR`, …, `POOL_RESIDUAL_*`), AR reference, delta 0.00, residual share (≤ 3 %), status PASS. FY17–FY20 rows say "total only".
- **Visual** `recon_table` · **Label** Real vs Synthetic · **RBAC** A · **Refs** SPEC-04 §7.2–7.4

### BEH-06.12 Older year with no nature split (CMD)
- **When** "FY19 employee cost by component."
- **Then** total ₹12,113.0 cr (Real, AR FY26 10-yr). Components are shown with the label "line split modelled (FY21 mix), AR FY2018-19 not yet ingested".
- **Visual** `donut` · **Label** Real total / Modelled split · **RBAC** A · **Refs** SPEC-04 §7.1 note

### BEH-06.13 Capitalised vs expensed employee cost (CMD)
- **When** "How much of employee cost is capitalised?"
- **Then** expensed in production = ₹2,652.12 cr (Real, Note 35 Staff Expenditure). GAE / exploration / capitalised split of the remaining ₹7,558.59 cr is Modelled. Caveat: "AR does not disclose the employee share of the ₹16,290.75 cr allocated to capital jobs".
- **Visual** `donut` · **Label** Real + Modelled · **RBAC** A · **Refs** SPEC-04 §7.1 step 7

### BEH-06.14 Headcount & retirements (CMD)
- **When** "Headcount trend and how many retire in the next 5 years?"
- **Then** FY-end headcount FY17 33,660 → FY26 23,117 (Real) + retirements in the next 1/3/5 yrs from `retiring_within_*` (Synthetic).
- **Visual** `column` + `kpi_card` ×3 · **Label** Real / Synthetic · **RBAC** A · **Refs** SPEC-04 §8

### BEH-06.15 Median pay vs BRSR (CMD)
- **When** "What's the median pay for executives, men vs women?"
- **Then** SSOT medians vs BRSR FY26: exec M ₹43.30 L / F ₹37.55 L; workers M ₹21.97 L / F ₹19.02 L. Delta % and EMP-R16 status.
- **Visual** `table` · **Label** Real (BRSR p.181) vs Synthetic · **RBAC** A · **Refs** SPEC-04 EMP-R16

## C. Field economics (modelled, reconciled)

### BEH-06.16 Employee cost per field — does it add up? (CMD)
- **When** "Employee cost per field, and does it add up to the company total?"
- **Then** `bar` of `employee_cost_total` by object (top 15 + "other fields" + plants + exploration + HQ). Footer bridge: Σ objects = ₹10,210.71 cr (= AR). Production-expensed Σ = ₹2,652.12 cr = Note 35 Staff Expenditure. FLD-R05 PASS.
- **Visual** `bar` + `recon_table` footer · **Label** Modelled (totals Real) · **RBAC** A · **Refs** SPEC-05 FLD-R05

### BEH-06.17 Same, junior HR (E2_HR)
- **When** as .16. **Then** the same field totals (`fin_internal` → AGG = field/company totals allowed). No cost-centre or ledger lines; drill-to-ledger chip hidden.
- **RBAC** AGG · **Refs** SPEC-06 §4.3

### BEH-06.18 Highest opex per boe (CMD)
- **When** "Which fields have the highest opex per boe?"
- **Then** top 10 by `opex_per_boe_usd` (FY26) with the company-average reference line and the definition tooltip (operating natures excl. levies, freight, corporate).
- **Visual** `bar` (sorted desc) · **Label** Modelled · **RBAC** A · **Refs** SPEC-05 §8

### BEH-06.19 Same, E3_FIN
- **When** as .18. **Then** identical (`fin_internal` = A for Finance juniors).
- **RBAC** A · **Refs** SPEC-06 §4.3

### BEH-06.20 Offshore vs onshore (DIR_FIN)
- **When** "Compare offshore and onshore for FY26."
- **Then** revenue 92,406.31 vs 40,101.83 cr; segment result 34,384.65 vs 6,245.70 cr; margin 37.2 % vs 15.6 %; DD&A 18,829.61 vs 6,367.43 cr.
- **Visual** `column` (grouped) + `table` · **Label** Real · AR FY26 Note 44 p.368–369 · **RBAC** A · **Refs** SPEC-05 FLD-R03, R07, R08

### BEH-06.21 Field-to-PBT bridge (CMD)
- **When** "Bridge field profits to company PBT for FY26."
- **Then** waterfall: Offshore fields 34,384.65 + Onshore fields 6,245.70 → HQ −2,543.83 → Finance cost −4,529.26 → Interest/dividend +8,857.63 → **PBT 42,414.89 cr**. Ends exactly at the reported PBT.
- **Visual** `waterfall` (signed bridge; BUG-08 rule) · **Label** Real (segment level), Modelled (field breakdown on drill) · **RBAC** A · **Refs** SPEC-05 FLD-R08, R09

### BEH-06.22 Revenue per employee by field (E1_FIN)
- **When** "Revenue per employee by field."
- **Then** `revenue_per_employee_field_cr` for fields with ≥ 5 direct + allocated FTE. Plants/HQ excluded with a note.
- **Visual** `bar` · **Label** Modelled · **RBAC** A · **Refs** SPEC-05 §8

### BEH-06.23 Production adds up (DIR_FIN)
- **When** "Does field production add up to the reported total?"
- **Then** FY26 crude ONGC 19.332 + JV 1.170 = 20.501 MMT; gas 19.533 + 0.434 = 19.966 BCM (AR p.55). Σ fields by basis = same; FLD-R11 PASS.
- **Visual** `recon_table` · **Label** Real vs Modelled · **RBAC** A · **Refs** SPEC-05 §6.1

### BEH-06.24 Lifting cost trend for Mumbai High (CMD)
- **When** "Lifting cost trend for Mumbai High."
- **Then** MHN + MHS combined `lifting_cost_per_boe_usd` FY17–FY26 (sums before ratio), with the definition shown.
- **Visual** `line` · **Label** Modelled · **RBAC** A · **Refs** SPEC-05 §8

## D. Cost optimisation & what-if

### BEH-06.25 Cap overtime (CMD)
- **Given** a scenario parameter cap = 30 h/month.
- **When** "How much would capping overtime at 30 hours a month save?"
- **Then** annual saving = Σ max(0, OT_h − 30) × OT rate over FY26 rows, by WC (top 10), plus the total. Chips: 20 h / 40 h. Caveat: "assumes the work is absorbed without new hiring".
- **Visual** `kpi_card` + `bar` · **Label** Scenario (on Synthetic) · **RBAC** A · **Refs** SPEC-04 §8 `what_if_ot_cap`

### BEH-06.26 Overtime share by work centre (DIR_HR)
- **When** "Overtime as a percentage of pay by work centre."
- **Then** `overtime_pct_of_pay` (workmen), sorted, with the company average.
- **Visual** `bar` · **Label** Synthetic · **RBAC** A · **Refs** SPEC-04 §8

### BEH-06.27 Medical cost per employee (CMD)
- **When** "Medical cost per employee trend."
- **Then** FY22–FY26 (claims history start) per employee and per covered life (`dependants_count + 1`). Split self vs dependants.
- **Visual** `line` (2 series) · **Label** Synthetic · **RBAC** A (aggregate) · **Refs** SPEC-04 §8

### BEH-06.28 Cost of the Delhi > 5-year cohort (CMD)
- **When** "What does the Delhi cohort with more than 5 years cost us?"
- **Then** count and Σ `ctc_annualised_inr` where `delhi_overdue_flag`, by grade. Shows both definitions (all staff vs executives only) with counts from the table. Policy label "JRTP Rev 4 cl. 3.2 (Illustrative); real anchor Delhi HC 2018".
- **Visual** `kpi_card` ×2 + `column` by grade · **Label** Synthetic + Illustrative policy · **RBAC** A · **Refs** SPEC-04 §4 N, §8

### BEH-06.29 Rotate the Delhi cohort (DIR_HR)
- **When** "If we rotate them to Y or Z class stations, what changes?"
- **Then** Δ HRA per month (X 30 % → Y 20 % / Z 10 % of basic at the current IDA band) minus one-time transfer cost (TA Regulations 2016 composite transfer grant + transport). Net annual effect, with a payback line.
- **Visual** `waterfall` · **Label** Scenario · **RBAC** A · **Refs** SPEC-04 §5.3, §8 `what_if_delhi_rotation`

### BEH-06.30 Allowance mix offshore vs onshore (CMD)
- **When** "Allowance mix for offshore versus onshore staff."
- **Then** share of basic / DA / HRA / cafeteria / hardship / location / shift / OT / PRP in gross, by `location_type`. Hardship ≤ 12 % BP is visible only offshore.
- **Visual** `stacked_100` · **Label** Synthetic · **RBAC** A · **Refs** SPEC-04 §5.4

### BEH-06.31 Pay compression (CMD)
- **When** "Is there pay compression between E1 and E9?"
- **Then** a box plot of `ctc_annualised` by grade + `pay_compression_ratio` (median E9 / median E1) + adjacent-grade ratios; flags adjacent ratios < 1.10.
- **Visual** `box` + `kpi_card` · **Label** Synthetic · **RBAC** A · **Refs** SPEC-04 §8

### BEH-06.32 Attrition vs BRSR (DIR_HR)
- **When** "Attrition by grade for the last 3 years, and how it compares with BRSR."
- **Then** `attrition_pct` by grade FY24–FY26 + company `turnover_pct_brsr` vs BRSR FY26 (employees 7.4 %, workers 3.1 %; methodology change noted).
- **Visual** `column` (grouped) + reference lines · **Label** Synthetic (calibrated) / Real BRSR · **RBAC** A · **Refs** SPEC-04 EMP-R17

## E. RBAC & self-service

### BEH-06.33 "My pay slip" (E2_HR)
- **When** "Show my pay slip."
- **Then** the latest closed month for **EMP-102451 Pooja Verma** only: earnings, deductions, net pay, employer contributions, YTD. Download chip.
- **Visual** `payslip` · **Label** Synthetic (illustrative identity) · **RBAC** SELF (`@self_emp_id`) · **Refs** SPEC-06 §4.2, BUG-07

### BEH-06.34 "What is my salary?" (E3_FIN)
- **When** "What is my salary?"
- **Then** the **E3_FIN seeded employee's** own gross/net and CTC run-rate. Never Pooja's (BUG-07 regression test: the response must not contain "EMP-102451").
- **Visual** `kpi_card` + `payslip` · **RBAC** SELF · **Refs** SPEC-06 §4.1

### BEH-06.35 Salary of a named colleague (E3_FIN)
- **When** "What is the salary of Rajesh Kumar?"
- **Then** a refusal without revealing whether the person exists or how many namesakes there are: "I can't share another employee's pay. I can show the average pay for a grade, the E-grade pay scale, or your own payslip." Chips offer those three.
- **Visual** none (refusal card with chips) · **RBAC** R (`pay_individual`) · **Refs** SPEC-06 §4.3

### BEH-06.36 Named high earners (E1_HR)
- **When** "List employees in Delhi earning more than ₹3 lakh a month."
- **Then** aggregated: count by grade where `gross_earnings_inr > 300000` at WC-DEL; cells < 5 → "<5"; no names. Note: "names are visible to CMD/Directors only".
- **Visual** `column` · **RBAC** AGG (`named` + `pay_individual` → aggregate) · **Refs** SPEC-06 §4.3

### BEH-06.37 Director Finance asks for HR officers' pay & APAR (DIR_FIN)
- **When** "Show salary and APAR of HR officers in Delhi."
- **Then** under proposed OD-7 (pending): refusal for individual pay/APAR outside `DISC-FIN`, offering aggregate pay by grade for HR officers in Delhi. If the sponsor rejects OD-7: allow a roster with CTC + APAR.
- **Visual** refusal card / `roster` · **RBAC** R (pending decision) · **Refs** SPEC-06 §4.3 note, Q1

### BEH-06.38 Director HR roster with CTC (DIR_HR)
- **When** "Give me names, grade, Delhi tenure and CTC of the overdue cohort, and export it."
- **Then** a roster (`emp_id`, `full_name`, `functional_designation`, `grade_id`, `station_tenure_continuous_years` labelled "Tenure in Delhi", `ctc_annualised_inr`), full cohort (cap 2,000). Export → formatted xlsx with the provenance row "Synthetic employee records".
- **Visual** `roster` + export · **RBAC** A · **Refs** SPEC-04 §4, SPEC-10

### BEH-06.39 FIN junior asks HR headcount (E4_FIN)
- **When** "Headcount by grade in Delhi."
- **Then** grade counts (already aggregate), cells < 5 → "<5" (CMD 1, DIR 2, E9 4 hidden).
- **Visual** `column` (ordered) · **RBAC** AGG (`general_hr` for FIN juniors) · **Refs** SPEC-06 §4.3

### BEH-06.40 Sensitive medical microdata (E3_HR)
- **When** "Show medical claims of employees in Mumbai."
- **Then** refusal (`sensitive`), offering medical-entitlement policy text and the company medical-cost-per-employee trend at company level only.
- **Visual** refusal card + chips · **RBAC** R · **Refs** SPEC-06 §4.3

## Test mapping
| Scenario ids | Test |
|---|---|
| .01–.02, .05–.06 | `yukti/backend/tests/test_salary_breakdown.py` (new): entry-pay rule; no fudge factor; per-employee averages |
| .07–.15, .20–.21, .23 | `eval/golden_employee360.yaml`, `eval/golden_field_econ.yaml`: exact real values (± 0.01 cr) |
| .16–.19, .22, .24–.32 | Formula-consistency tests: recompute from the SSOT in the test, compare to the answer contract (± 0.5 %) |
| .33–.40 | `tests/test_rbac_policy.py` 11 × data-class matrix + `self` (SPEC-06) |
