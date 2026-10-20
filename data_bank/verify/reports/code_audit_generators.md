# Independent Code Audit Report: Entity-Forcing and Plug Detection in Data Generators

**Audit Date:** 2026-10-19  
**Auditor:** Independent Code Auditor (Jetski Subagent)  
**Scope:**  
1. `data_bank/generators/hr/gen_21_hr_core.py` (Core HR Generator)  
2. `data_bank/generators/hr/gen_22_hr_sat.py` (HR Satellite & Governance Generator)  
3. `data_bank/generators/ops/gen_23_ops.py` (Operations & Reserves Generator)  
**Governing Policies:** Rule 5a in `data_bank/DATA_GENERATION_CHECKLIST.md` and the NO PLUGS rule in `data_bank/DELEGATION_PLAYBOOK.md`.

---

## 1. Executive Summary & BLUF

**BLUF: All three audited generators (`gen_21_hr_core.py`, `gen_22_hr_sat.py`, and `gen_23_ops.py`) contain widespread, systemic violations of Rule 5a and the NO PLUGS policy, identical in character to the entity-forcing pattern discovered in Generator 2.4.**

Across the three generators, the audit identified **54 distinct findings**:
- **35 Violations** (Hardcoded entity-level outcome forcing, literal story count assignment, and post-hoc record manipulation).
- **8 Borderline Cases** (Establishment sizing quotas, discipline-level averages, and deterministic index slicing).
- **11 Allowed Instances** (Legitimate company-wide calibration to public totals, physical terrain mappings, and canonical demo persona profiles).

### Impact & Assessment
Rather than allowing plantable stories to organically emerge from stochastic record-level simulation driven by general attributes and global parameters, the generators routinely:
1. Hard-code exact story numbers (e.g. 412, 138, 107, 31, 260, 47, 186, 182, 191, 142, 188, 48.6, 18.2, 0.042, 0.018, 91.0) into discrete loops, conditions, or dictionary lookups keyed by specific entity IDs (`WC-DEL`, `WC-NEH`, `WC-TRI`, `FLD-BOR`, `FLD-ADI`, `FLD-KAT`, `FLD-MHN`, `FLD-GEL`).
2. Employ explicit plug-balancing lines (e.g., assigning residual 2P and 1P reserves rounding deltas directly to `FLD-MHN` and `FLD-PAN`).
3. Post-hoc select specific subsets of records (e.g., `[:260]`, `[:18]`, `[:42]`, `[:112]`) and overwrite their tenure, retirement dates, or status flags to guarantee exact verification pass rates.

These generators must be refactored to replace entity-level forcing with attribute-driven probability functions and continuous stochastic processes.

---

## 2. Summary Audit Matrix by File

| Generator File | Domain / Scope | Allowed | Borderline | Violation | Total Findings |
|---|---|:---:|:---:|:---:|:---:|
| `data_bank/generators/hr/gen_21_hr_core.py` | Core HR, Postings, Demographics, Resignations | 4 | 3 | **14** | 21 |
| `data_bank/generators/hr/gen_22_hr_sat.py` | Sanctioned Posts, Payroll, Succession, HSE, Claims, Audit | 5 | 1 | **11** | 17 |
| `data_bank/generators/ops/gen_23_ops.py` | Production, Wells Drilled, Reserves, F&D Costs | 2 | 4 | **10** | 16 |
| **Total Across All Files** | | **11** | **8** | **35** | **54** |

---

## 3. Top Critical Violations

1. **`gen_23_ops.py` (L424–443, L489–492) — Fixed Production Forcing Dictionaries:**  
   Bypasses simulation by assigning fixed production volumes directly to specific fields (`FLD-BOR: 42000.0`, `FLD-ADI: 18000.0`, `FLD-KAT: 80000.0`, `FLD-CAM: 140.0`, `FLD-MHN: 4095000.0`) to hit Stories S6, S7, and S8 exactly.
2. **`gen_23_ops.py` (L1031–1050) — Balancing Plug Injection on Mumbai High & Panna:**  
   Direct breach of NO PLUGS: calculates rounding differences to company calibration totals and dumps the residual onto `FLD-MHN` (operated) and `FLD-PAN` (JV).
3. **`gen_23_ops.py` (L325–331, L378–385) — Hardcoded Geleki Outage & Water-Cut Jump:**  
   Forces `FLD-GEL` water cut to jump from 86.5% to exactly 91.0% (+4.5%) in September 2026, and pins downtime to 1,450 hours for Story S36.
4. **`gen_21_hr_core.py` (L286–357) — Story S1 Corporate HQ Delhi Tenure Manufacture:**  
   Synthesizes exact employee cohorts using `range(31)`, `range(107)`, `range(273)` with hardcoded cumulative years (12.0y, 11.0y, 6.5y) to hit 412 (>=5y), 138 (>=10y), 31 (exempt), and 107 (overdue).
5. **`gen_21_hr_core.py` (L711–720) — Story S2 Hard Station Avoidance Counter:**  
   Directly loops through E3–E5 executives and sets `if idx < 260: s["force_never_hard_station"] = True` to guarantee the Story S2 count of 260.
6. **`gen_21_hr_core.py` (L1626–1675) — Story S11 Delayed DPC Fabrication:**  
   Synthetically generates dummy delayed DPC cases via `range(112)` for Drilling and `range(74)` for Production, attached to `WC-DEL`.
7. **`gen_22_hr_sat.py` (L1225–1240) — Story S13 Contractor Workforce Inversion Dict:**  
   Directly hardcodes contractor headcount, regular headcount, and monthly cost for `WC-HAZ` (2,450 vs 1,120; ₹412 cr spend) and `WC-URN` (1,890 vs 940; ₹318 cr spend).
8. **`gen_22_hr_sat.py` (L278–297) — Stories S2 & S35 Vacancy Allocation Overrides:**  
   Artificially dumps 191 executive vacancies into `WC-TRI`, and forces 24 Group C and 6 Group D vacancies into Assam work centres (`WC-ASM`, `WC-JOR`, `WC-SIL`).
9. **`gen_22_hr_sat.py` (L591–605, L649–656) — Story S4 Succession Planning Zero Ready-Now Deficit:**  
   Hardcodes `canonical_11` leadership positions and gates `if idx < 11: s1_ready = "Ready 1-2 Years"` to force exactly 11 roles with zero ready successors.
10. **`gen_22_hr_sat.py` (L413–421, L1378–1420) — Story S14 Overtime & Fatigue LTI Assignment:**  
    Hardcodes 48.6 hours overtime for `WC-NEH` and 18.2 hours for `WC-MUM`, then generates exactly 4 LTIs at Neelam-Heera with fatigue flags.

---

## 4. Detailed File-by-File Audit Findings

### 4.1. File: `data_bank/generators/hr/gen_21_hr_core.py`

| ID | Line(s) | Category | Code Snippet | Classification | Description & Recommended Fix |
|---|---|:---:|---|:---:|---|
| **21-01** | L286–357 | (b), (c) | `for i in range(31): ... cum_delhi_years: 12.0`<br>`for i in range(107): ... cum_delhi_years: 11.0`<br>`for i in range(273): ... cum_delhi_years: 6.5` | **VIOLATION** | **Story S1 Outcome Forcing:** Synthesizes exact cohort sizes to force 412 (>=5y), 138 (>=10y), 31 (exempt), and 107 (overdue) at `WC-DEL`.<br>*Fix:* Simulate tenure dynamically from historical transfer probabilities with a Delhi stickiness factor; let the >=5y count emerge within target range (380–450). |
| **21-02** | L389–436 | (a), (b) | `assam_alloc = [("WC-ASM", 650, 80, 850, 120), ("WC-JOR", 420, 50, 550, 80), ...]` | **BORDERLINE** | **Assam Establishment Quotas:** Hardcodes exact cadre breakdowns per Assam work centre.<br>*Fix:* Store baseline establishment capacities in `world_bible/reference/work_centres.yaml` and sample headcounts using Poisson/multinomial allocation. |
| **21-03** | L440–458 | (a), (b) | `for i in range(677): ... "wc_id": "WC-TRI"`<br>`for i in range(173): ... "wc_id": "WC-TRI"` | **BORDERLINE** | **Tripura Establishment Quotas:** Hardcodes 677 executives and 173 non-executives for Tripura.<br>*Fix:* Parameterize asset establishment sizing based on operational scale (rigs, wells, production). |
| **21-04** | L462–481 | (a), (b) | `for i in range(1500): ... "gender": "Female" if i < 310 else "Male"`<br>`for i in range(750): ... "gender": "Female" if i < 108 else "Male"` | **VIOLATION** | **Story S17 Dehradun Female Headcount Forcing:** Hardcodes 310 + 108 = 418 female employees at `WC-DDN`.<br>*Fix:* Use an asset-level female participation probability parameter (~18.5% for institutes/HQ) and let the exact count emerge. |
| **21-05** | L484–516 | (a), (b) | `offshore_alloc = [("WC-MUM", 3199, 40), ("WC-BAS", 1800, 23), ("WC-NEH", 1500, 15)]` | **VIOLATION** | **Story S17 Offshore Female Representation Forcing:** Hardcodes exact female counts (40 + 23 + 15 = 78) across offshore assets.<br>*Fix:* Model offshore gender selection using an offshore deployment probability parameter (~1.2%). |
| **21-06** | L519–576 | (a), (b) | `asset_alloc = [("WC-EAS", 830, "AP", True, 560), ("WC-RAJ", 1025, "AP", False, 760), ("WC-MEH", 2050, "GJ", False, 1850), ...]` | **VIOLATION** | **Stories S3 & S7 Specific Asset Headcount Forcing:** Hardcodes exact FY26 headcounts (830, 1025, 2050, 1035, 587) and historical FY21 cohorts (560, 760, 1850, 900, 470).<br>*Fix:* Drive headcount evolution using asset lifecycle growth rates (e.g. +5% for deepwater, -2.5% for mature basins). |
| **21-07** | L622–645 | (a), (c) | `protected_locations_idx = set(... if get_spec_wc(...) in ["WC-DEL", "WC-DDN", "WC-MUM", "WC-BAS", "WC-NEH"])` | **VIOLATION** | **Protected Entities in Global Calibration:** Excludes specific entities from company-wide gender calibration to protect hardcoded Story S17 values.<br>*Fix:* Perform global calibration across all records using propensity weighting without entity exclusions. |
| **21-08** | L665–672 | (b), (c) | `for idx in exec_indices[:313]: active_specs[idx]["pwd_flag"] = True`<br>`for idx in nonexec_indices[:210]: ...` | **ALLOWED** | **Statutory PwD Calibration:** Calibrates company-wide PwD representation to match statutory target CAL-HR-PWD-TOTAL-FY26 (523 total: 313 exec, 210 non-exec).<br>*Allowed:* Targets a company-wide public total without entity-level forcing. |
| **21-09** | L682–697 | (b) | `categories = ["SC"] * 3472 + ["ST"] * 2624 + ["OBC"] * 6242 + ["EWS"] * 1156; random.shuffle(categories)` | **ALLOWED** | **Statutory Reservation Calibration:** Calibrates affirmative action categories to match company-wide statutory ratios (SC 15.02%, ST 11.35%).<br>*Allowed:* Global scaling uniformly distributed across all records. |
| **21-10** | L701–709 | (b) | `grade_pool = ["E9"] * 50 + ["E8"] * 240 + ["E7"] * 849 + ... assert e7_plus_cnt == 1142` | **ALLOWED** | **Executive Grade Pyramid Calibration:** Calibrates executive grade pyramid to match total in-position executive strength (1,142 E7+).<br>*Allowed:* Company-wide executive hierarchy calibration. |
| **21-11** | L711–720 | (b), (c) | `for idx, s in enumerate(e3_e5_execs): if idx < 260: s["force_never_hard_station"] = True` | **VIOLATION** | **Story S2 Hard Station Avoidance Forcing:** Sets `force_never_hard_station = True` on exactly the first 260 E3–E5 executives.<br>*Fix:* Simulate mobility preferences based on discipline, family status, and health flags; let the count of non-hard-station officers emerge. |
| **21-12** | L726–744 | (b), (c) | `for i in range(18): ... (FY27 dob)`<br>`for i in range(16): ... (FY28 dob)`<br>`for i in range(13): ... (FY29 dob)` | **VIOLATION** | **Story S4 E7+ Retirement Staging:** Manufactures exact birthdates to force 18 (FY27), 16 (FY28), and 13 (FY29) retirements (total 47).<br>*Fix:* Model executive age distribution smoothly across the E7+ pool with a continuous demographic curve. |
| **21-13** | L764–776 | (b), (c) | `tech_o50_disc = ["DISC-DRL"] * 642 + ["DISC-GEO"] * 345 + ["DISC-GPS"] * 290 + ["DISC-RES"] * 226 + ["DISC-PRD"] * 711`<br>`for i in range(2214): ...` | **VIOLATION** | **Story S5 Technical Skills Cliff Forcing:** Overwrites discipline and birthdates on 2,214 records to force exact retirements by 2030 (DRL: 642, GEO+GPS: 635, total: 2,215).<br>*Fix:* Parameterize historical recruitment waves per discipline (e.g. 1985–1995 hiring surge); let retirement counts emerge. |
| **21-14** | L808–819 | (b), (c) | `for s in avail_new_females[:28]: ...`<br>`for s in avail_new_males[:139]: ...` | **ALLOWED** | **FY26 New Hires Calibration:** Calibrates total FY26 intake to match public target CAL-HR-HIRES-FY26 (167 total, 28 female).<br>*Allowed:* Global company-wide intake total. |
| **21-15** | L921–931 | (a), (c) | `sep_asset_pool = ["WC-MEH"] * 490 + ["WC-CAU"] * 280 + ["WC-RAJ"] * 80 + ["WC-EAS"] * 60 + ["WC-CAM"] * 44`<br>`safe_sep_wcs = [w for w in WC_BY_ID.keys() if w not in ['WC-EAS', ...]]` | **VIOLATION** | **Stories S3 & S7 Historical Separation Plugs:** Injects synthetic separations into specific work centres to back-solve historical FY21 headcounts.<br>*Fix:* Model historical attrition using asset-level turnover rates rather than balancing quotas. |
| **21-16** | L944–962 | (a), (b) | `for i in range(20): ... "current_wc_id": "WC-DEL" if i < 10 else "WC-MUM"` | **BORDERLINE** | **ED Superannuations Work Centre Split:** Splits 20 ED retirements between Delhi and Mumbai High.<br>*Fix:* Generate superannuations from natural DOBs of E9 incumbents across all active locations. |
| **21-17** | L964–1004 | (a), (b), (c) | `for i in range(42): ... "discipline_id": "DISC-IT", "current_wc_id": "WC-DEL" if i < 20 else "WC-DDN"`<br>`for i in range(38): ... "discipline_id": "DISC-FIN", "current_wc_id": "WC-DEL" if i < 15 else "WC-MUM"` | **VIOLATION** | **Story S12 Mid-Career Resignations Forcing:** Loops through exact counts (42 IT, 38 Finance, total 182) and pins them to Delhi, Dehradun, and Mumbai.<br>*Fix:* Model voluntary turnover using discipline-specific attrition hazards (e.g. IT 4.5% vs core E&P 1.2%); let counts emerge. |
| **21-18** | L1173–1201 | (a), (c) | `selected_resig = it_e3_e5[:21] + fin_e3_e5[:19] + oth_e3_e5[:22] + oth_exec[:29]`<br>`where current_wc_id != "WC-DEL"` | **VIOLATION** | **FY27 H1 Resignation Forcing with Delhi Shielding:** Slices exact resignation quotas for H1 while shielding Delhi from exits.<br>*Fix:* Apply uniform stochastic hazard model across all work centres. |
| **21-19** | L1412–1446 | (a) | `if s["emp_id"] == "EMP-000001": ... elif s["emp_id"] == "EMP-000002": ... EMP-000003, EMP-102451, EMP-103892` | **ALLOWED** | **Canonical Demo Personas:** Hardcoded career histories for the 5 authorized demo personas.<br>*Allowed:* Explicitly permitted by system prompt and World Bible. |
| **21-20** | L1510–1532 | (a), (c) | `if not any(p["wc_id"] in HARD_STATION_WCS for p in emp_postings): emp_postings[0]["wc_id"] = "WC-ASM"` | **VIOLATION** | **Retroactive Hard-Station Posting Rewriting:** Rewrites historical postings to insert `WC-ASM` if an employee did not naturally receive a hard-station posting.<br>*Fix:* Simulate career postings sequentially with proper rotation mechanics. |
| **21-21** | L1626–1675 | (a), (b), (c) | `for i in range(112): emp_cand = active_drl_e4[...] ... "wc_id": "WC-DEL", "discipline_id": "DISC-DRL", "status": "delayed"`<br>`for i in range(74): emp_cand = active_prd_e4[...] ...` | **VIOLATION** | **Story S11 Delayed DPC Fabrication:** Synthetically creates dummy delayed DPC cases (112 DRL, 74 PRD, total 186) assigned to `WC-DEL`.<br>*Fix:* Simulate DPC scheduling with probabilistic clearance bottlenecks (vigilance, court stays); let delayed counts emerge. |

---

### 4.2. File: `data_bank/generators/hr/gen_22_hr_sat.py`

| ID | Line(s) | Category | Code Snippet | Classification | Description & Recommended Fix |
|---|---|:---:|---|:---:|---|
| **22-01** | L278–283 | (a), (b), (c) | `mask_tri = (sanc_grp["wc_id"] == "WC-TRI") & (sanc_grp["grade_band"] == "Executive")`<br>`for i in range(191): sanc_grp.loc[idx_tri[i % len(idx_tri)], "vacancy_count"] += 1` | **VIOLATION** | **Story S2 NE Operational Norm Shortfall Forcing:** Dumps all 191 executive vacancies into `WC-TRI` to artificially shield Assam from having executive vacancies.<br>*Fix:* Model operational manpower norms and vacancies per asset based on facility workload; let vacancies distribute naturally across NE assets. |
| **22-02** | L286–297 | (a), (b), (c) | `mask_c = (sanc_grp["wc_id"].isin(["WC-ASM", "WC-JOR", "WC-SIL"])) & (sanc_grp["grade_id"] == "GRP-C"); for i in range(24): ...`<br>`mask_d = ...; for i in range(6): ...` | **VIOLATION** | **Stories S2 & S35 Assam Formal Vacancies Forcing (LS2067):** Hardcodes exact parliamentary reply counts (24 Group C, 6 Group D) into Assam work centres.<br>*Fix:* Establish formal sanctioned rosters in reference data and let vacancies arise naturally from non-executive retirements. |
| **22-03** | L298–318 | (b), (c) | `for i in range(142): sanc_grp.loc[row_idx, "backlog_vacancies"] += 1 ... special_drive_target_vacancies = 142`<br>`for i in range(188): ... special_drive_target_vacancies = 188` | **VIOLATION** | **Story S16 Affirmative Action Backlog Forcing:** Artificially increments backlog vacancies by looping exact story counts (142 ST, 188 OBC).<br>*Fix:* Derive backlog vacancies from cumulative 5-year shortfalls in recruitment drives. |
| **22-04** | L413–421 | (a), (b) | `monthly_active_df.loc[(monthly_active_df["wc_id"] == "WC-NEH") & (monthly_active_df["cadre"] == "nonexec"), "overtime_hours"] = 48.6`<br>`monthly_active_df.loc[(monthly_active_df["wc_id"] == "WC-MUM") & ..., "overtime_hours"] = 18.2` | **VIOLATION** | **Story S14 Offshore Overtime Hours Forcing:** Directly assigns exact overtime figures (48.6h for Neelam-Heera, 18.2h for Mumbai High).<br>*Fix:* Compute overtime as an emergent function of shift vacancy rates, operational upsets, and turnaround activities. |
| **22-05** | L425–428 | (b) | `monthly_active_df.loc[..., "prp_inr"] = (monthly_active_df["basic_pay_inr"] * 0.35).round(2)` | **ALLOWED** | **Story S27 Global PRP Pool Formulation:** Applies uniform corporate PRP formula (35% of basic pay) across executive cadres.<br>*Allowed:* Global scalar applied uniformly. |
| **22-06** | L438–444 | (b) | `monthly_active_df["superannuation_benefit_pct"] = 28.4` | **ALLOWED** | **Story S26 Superannuation Benefit Cap:** Sets uniform corporate superannuation benefit percentage to 28.4% (DPE 30% cap headroom).<br>*Allowed:* Company-wide benefit policy parameter. |
| **22-07** | L591–605, L649–656 | (a), (b), (c) | `canonical_11 = [("POS-001", "Asset Manager - Mumbai High", "WC-MUM", ...), ...]`<br>`if idx < 11: s1_ready = "Ready 1-2 Years"; s2_ready = "Ready 2-3 Years" else: s1_ready = "Ready Now"` | **VIOLATION** | **Story S4 Critical Succession Vacuum Forcing:** Hardcodes 11 specific roles across assets and gates readiness `if idx < 11` to force exactly 11 roles with zero ready successors.<br>*Fix:* Evaluate candidate readiness dynamically against qualification rules (feeder grade tenure, APAR score, hard-station completion). |
| **22-08** | L852–857 | (b), (c) | `n_e = 8746 if fy == "FY26" else ...; n_ne = 3615 ...`<br>`sampled_e = exec_active.sample(n=n_e, random_state=SEED)...` | **ALLOWED** | **Annual Report Training Calibration:** Calibrates total distinct employees trained to public totals CAL-HR-TRN-EXEC-FY26 (8,746) and CAL-HR-TRN-NONEXEC-FY26 (3,615).<br>*Allowed:* Global company-wide calibration to public totals. |
| **22-09** | L872–882 | (b) | `if fy == "FY26": if disc == "DISC-DRL": hrs = 18.5 elif disc == "DISC-PRD": hrs = 21.2 elif disc == "DISC-HR": hrs = 46.2 ...` | **BORDERLINE** | **Discipline Training Hours Assignment:** Sets average training hours directly by discipline code.<br>*Fix:* Sample training course attendance from course catalog with realistic course credit hours. |
| **22-10** | L958–963 | (a) | `if eid == "EMP-102451": el_bal = 78.0; encash_bal = 48.0 elif eid == "EMP-103892": el_bal = 112.0; encash_bal = 82.0` | **ALLOWED** | **Story S38 Demo Persona Leave Balances:** Pinned leave balances for canonical demo personas.<br>*Allowed:* Explicit demo persona exemption. |
| **22-11** | L1050–1087 | (a) | `MED-000001` for `EMP-102451`, `MED-000002` for `EMP-103892` | **ALLOWED** | **Story S38 Demo Persona Medical Claims:** Pinned claims for demo personas.<br>*Allowed:* Explicit demo persona exemption. |
| **22-12** | L1141–1153 | (b), (c) | `for i in range(312): ... if i < 142: age = 380 + (i * 3) % 450 else: age = 30 + (i * 2) % 320` | **VIOLATION** | **Story S19 Grievance Aging Forcing:** Synthesizes exact counts (312 grievances, 142 aged >1 year) via index threshold `i < 142`.<br>*Fix:* Generate grievance filings via Poisson arrival process and resolve them via duration distribution; let active/aged counts emerge. |
| **22-13** | L1173–1188 | (b), (c) | `for i in range(84): ... if i < 48: cat = "DPC / Seniority" else: ...` | **VIOLATION** | **Story S19 Court Cases Category Forcing:** Loops `range(84)` and splits `if i < 48` to force 48 DPC/Seniority court cases.<br>*Fix:* Simulate court cases as downstream escalations from rejected appeals and delayed DPCs. |
| **22-14** | L1225–1240 | (a), (b) | `base_contract_allocations = {"WC-HAZ": (2450, 1120, 34.33e7), "WC-URN": (1890, 940, 26.50e7), ...}` | **VIOLATION** | **Story S13 Contractor Inversion at Gas Plants:** Directly hardcodes contractor headcount, regular headcount, and spend for `WC-HAZ` (2,450 vs 1,120; ₹412 cr spend) and `WC-URN` (1,890 vs 940; ₹318 cr spend).<br>*Fix:* Model contractor requirements driven by plant gas throughput, maintenance man-hours, and safety norms. |
| **22-15** | L1378–1420 | (a), (b) | `for i in range(4): hse_rows.append({"wc_id": "WC-NEH", "monthly_overtime_hours_per_worker": 48.6, "fatigue_factor_flag": True, ...})`<br>`for i, wc in enumerate(other_wcs): ... "monthly_overtime_hours_per_worker": 18.2` | **VIOLATION** | **Story S14 HSE Lost Time Injuries & Fatigue Forcing:** Hardcodes exactly 4 LTIs at Neelam-Heera with 48.6h overtime and fatigue flags.<br>*Fix:* Model safety incident rates using an incident probability function driven by exposure man-hours and fatigue indices. |
| **22-16** | L1434–1478 | (a) | `TRV-0000001` for `EMP-102451`, `TRV-0000002` for `EMP-103892` | **ALLOWED** | **Story S38 Demo Persona Travel Claims:** Travel claims for demo personas.<br>*Allowed:* Explicit demo persona exemption. |
| **22-17** | L1628–1643 | (a), (b) | `refusal_specs = [("EMP-102451", ...), ("EMP-105120", ...), ("EMP-106400", ...), ...]` | **VIOLATION** | **Story S37 Access Audit Log Refusal Manifest:** Static table of 14 refusal records featuring 8 non-persona employee IDs to hit Story S37 counts exactly.<br>*Fix:* Simulate interactive user queries against resource authorization policies (RBAC); log actual denials dynamically. |

---

### 4.3. File: `data_bank/generators/ops/gen_23_ops.py`

| ID | Line(s) | Category | Code Snippet | Classification | Description & Recommended Fix |
|---|---|:---:|---|:---:|---|
| **23-01** | L196 | (b) | `"FY27": {"crude": 9.420, "condensate": 0.450, "gas": 9.750}, # H1 only (S10 crude: 9.420)` | **BORDERLINE** | **Story S10 Target Setting:** Sets FY27 H1 target directly to story value 9.420 MMT.<br>*Fix:* Use annualized targets and derive H1 target from seasonal monthly weighting. |
| **23-02** | L212–235 | (a), (b) | `if fid in ["FLD-MHN", "FLD-MHS"]: base_oil[fid] = 4.10`<br>`elif fid == "FLD-BOR": base_oil[fid] = 0.042`<br>`elif fid == "FLD-ADI": base_oil[fid] = 0.018` | **VIOLATION** | **Stories S6 & S8 Field Crude Base Rates Cascade:** Hardcodes base production rates per field ID, including exact Story S6 numbers for Borholla (0.042 MMT) and Adiyakkamangalam (0.018 MMT).<br>*Fix:* Derive base production from field in-place reserves and reservoir depletion stage in `fields.yaml`. |
| **23-03** | L240–265 | (a), (b) | `if fid == "FLD-BAS": base_gas[fid] = 7.50`<br>`elif fid == "FLD-CAM": base_gas[fid] = 0.140`<br>`elif fid in ["FLD-BOR", "FLD-ADI", "FLD-KAT"]: base_gas[fid] = 0.005` | **VIOLATION** | **Stories S6 & S7 Field Gas Base Rates Cascade:** Hardcodes base gas rates per field ID, including Cambay and marginal fields.<br>*Fix:* Derive base gas production from field GIIP and gas-oil ratios. |
| **23-04** | L293–311 | (a) | `if fid == "FLD-KG982": ... elif fid == "FLD-DAM": ... elif fid in ["FLD-CAM", "FLD-KAT"]: ...` | **VIOLATION** | **Field-Specific Decline Curve Overrides:** Hardcodes bespoke decline profiles for specific field IDs to force Story S7 Cambay efficiency collapse and KG-98/2 ramp-up.<br>*Fix:* Apply decline curves parameterized by field maturity classification (`maturing`, `plateau`, `developing`) rather than naming field IDs. |
| **23-05** | L325–347 | (a), (b) | `if fid == "FLD-GEL": if m_str == "2026-09": wc_pct = 91.0 elif m_str == "2026-08": wc_pct = 86.5`<br>`elif fid == "FLD-BOR": wc_pct = 89.4 ...` | **VIOLATION** | **Story S36 Geleki Water-Cut Spike & S6 Marginal Water Cuts:** Hardcodes exact 91.0% water cut (+4.5% jump) for Geleki in Sep-2026, and high water cuts for Borholla/Adiyakkamangalam.<br>*Fix:* Simulate water cut evolution using a reservoir water-coning/breakthrough function based on cumulative production. |
| **23-06** | L352–375 | (a) | `if fid in ["FLD-MHN", "FLD-MHS"]: n_prod = 185; n_inj = 62 ... elif fid in ["FLD-BOR", "FLD-ADI"]: n_prod = 14; n_inj = 2` | **BORDERLINE** | **Field Well Count Allocation:** Assigns active well counts by conditional branching on field IDs.<br>*Fix:* Define well counts in `world_bible/reference/fields.yaml` or compute from field surface area and drainage spacing. |
| **23-07** | L378–385 | (a), (b) | `if fid == "FLD-GEL" and m_str == "2026-09": uptime_pct = 89.2; downtime_hrs = 1450.0` | **VIOLATION** | **Story S36 Geleki Outage Forcing:** Overwrites uptime to 89.2% and downtime to 1,450 hours for `FLD-GEL` in September 2026.<br>*Fix:* Model plant uptime and downtime using stochastic failure rates and scheduled maintenance events. |
| **23-08** | L424–443 | (a), (b) | `fixed_oil = {"FLD-BOR": 42000.0, "FLD-ADI": 18000.0, "FLD-KAT": 80000.0, "FLD-PAN": 750000.0, "FLD-MUK": 420000.0, "FLD-MHN": 4095000.0, "FLD-MHS": 4005000.0}`<br>`fixed_gas = {"FLD-CAM": 140.0, ...}` | **VIOLATION** | **Stories S6, S7 & S8 FY26 Fixed Production Dicts:** Directly pins exact annual production volumes to specific fields, bypassing simulation.<br>*Fix:* Eliminate `fixed_oil`/`fixed_gas` dictionaries. Use global scaling factors across basins while allowing field-level production to fluctuate naturally. |
| **23-09** | L489–492 | (a), (b) | `fixed_oil = {"FLD-KAT": 88000.0}`, `fixed_gas = {"FLD-CAM": 154.0}` | **VIOLATION** | **Story S7 FY21 Cambay Production Forcing:** Hardcodes exact FY21 production for Kathana (88k MT) and Cambay (154 MMSCM) to force 0.242 MMTOE.<br>*Fix:* Allow historical production to emerge from standard historical decline models. |
| **23-10** | L729–741 | (c) | `if fy == "FY26": if i < 38: status = "oil_discovery" elif i < 53: status = "gas_discovery" ...` | **BORDERLINE** | **Exploratory Well Success Allocation:** Uses index slicing to allocate 38 oil and 15 gas discoveries (53% success rate).<br>*Fix:* Use Bernoulli trials with calibrated discovery probability ($p=0.53$). |
| **23-11** | L790–798 | (a) | `if fid == "FLD-KG982": terrain = "deepwater"; rig_type = "floater_drillship"` | **ALLOWED** | **KG-98/2 Deepwater Terrain Mapping:** Assigns deepwater terrain to KG-DWN-98/2.<br>*Allowed:* Legitimate physical attribute lookup. |
| **23-12** | L930–975 | (a) | `if fid in ["FLD-MHN", "FLD-MHS"]: oiip = 1650.0 ... elif fid == "FLD-BAS": ... elif fid == "FLD-PAN": r_2p_oil = 7.45 ...` | **BORDERLINE** | **In-Place & 2P Reserves Baseline by Field:** Hardcodes baseline reserves estimates for major fields.<br>*Fix:* Move baseline in-place and 2P estimates into `world_bible/reference/fields.yaml`. |
| **23-13** | L1004–1026 | (b) | `jv_scale = 11.49 / jv_sum`, `op_scale = 697.83 / op_sum`, `df_res.loc[m_fy, "reserves_2p_oil_mmt"] = ... * sc` | **ALLOWED** | **Global 2P Reserves Scaling:** Calibrates total company 2P reserves to Annual Report target CAL-RES-2P-FY26 (697.83 operated, 11.49 JV).<br>*Allowed:* Global company-wide scaling to match public totals. |
| **23-14** | L1031–1050 | (a), (c) | `diff_op = 697.83 - sum; mhn_idx = df_res[... "FLD-MHN"].index[0]; df_res.loc[mhn_idx, "reserves_2p_oil_mmt"] += diff_op`<br>`diff_jv = 11.49 - sum; pan_idx = df_res[... "FLD-PAN"].index[0]; df_res.loc[pan_idx, ...]` | **VIOLATION** | **Balancing Plugs on Mumbai High & Panna:** Explicit breach of NO PLUGS: calculates rounding differences to company totals and forces them onto `FLD-MHN` and `FLD-PAN`.<br>*Fix:* Distribute rounding differences proportionally across fields using Largest Remainder Method, or report unrounded sums. |
| **23-15** | L1055–1063 | (b) | `df_res.loc[mask_26, "gross_reserves_accretion_mmtoe"] = (df_res.loc[mask_26, "annual_production_mmtoe"] * 1.17).round(2)`<br>`df_res.loc[mask_26, "reserve_replacement_ratio_rrr_2p"] = 1.17` | **VIOLATION** | **Reserve Replacement Ratio (RRR) Forcing:** Sets every single field's RRR to exactly 1.17 instead of allowing RRR to emerge from accretion / production.<br>*Fix:* Simulate field-level accretion from new discoveries and revisions; calculate RRR = `accretion / production`. Let company average emerge at ~1.17. |
| **23-16** | L1076–1110 | (b), (c) | `s24_targets = {"Western Offshore": {"finding": 2.50, "dev": 5.70}, "Krishna Godavari": {"finding": 6.20, "dev": 12.30}, ...}`<br>`df_wells.loc[m_b_expl, "drilling_cost_inr_cr"] *= (target_expl_cr / cur_expl_cr)` | **VIOLATION** | **Story S24 Finding & Development Cost Re-scaling:** Post-hoc rescales drilling costs in `wells_drilled.csv` across basins to force exact Story S24 F&D targets ($8.20 Western Offshore, $18.50 KG).<br>*Fix:* Parameterize well costs using rig day-rates and depth benchmarks; let basin F&D cost per BOE emerge from total drilling expenditure divided by reserve additions. |

---

## 5. Architectural Remediation Plan

To bring all generators into full compliance with Rule 5a and the NO PLUGS policy, execute the following 4-step remediation:

1. **Purge Entity-Specific Lookup Dictionaries & Condition Cascades:**
   - Eliminate `fixed_oil`, `fixed_gas`, `fixed_cond` dictionaries in `gen_23_ops.py`.
   - Remove `base_contract_allocations` in `gen_22_hr_sat.py`.
   - Remove `refusal_specs` static rows in `gen_22_hr_sat.py`.
   - Move static field parameters (in-place reserves, baseline capacities, well counts) into `world_bible/reference/fields.yaml`.
2. **Replace Post-Hoc Slicing with Stochastic Propensity Models:**
   - Replace index-based slicing (`if idx < 260: force_never_hard_station`) with probabilistic logistic models driven by employee attributes (cadre, discipline, age, family status).
   - Replace `if idx < 11: s1_ready = "Ready 1-2 Years"` with rule-based qualification scoring on potential successors.
   - Replace grievance and litigation index slicing (`if i < 142`) with Poisson arrival and survival analysis models.
3. **Eliminate All Balancing Plugs:**
   - Remove lines 1031–1050 in `gen_23_ops.py` that dump rounding residuals onto `FLD-MHN` and `FLD-PAN`.
   - Use Largest Remainder Method or standard floating-point sum tolerance for public totals.
4. **Re-tune Global Simulation Scalars:**
   - Calibrate global drivers (turnover rates, decline curves, drilling costs per meter) so that story numbers emerge within their target ranges ($\pm 10\%$) without being artificially pinned.
