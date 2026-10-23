# Verbatim 23: v3 Decisions & Realistic Employee-360 / Cost-Analytics Data Foundation

**Date Captured**: October 23, 2026, 07:07 UTC  
**Source**: Typed in chat (response to the 23-Oct deep diagnosis, decisions 1–7)  
**Persona**: Product Sponsor  
**Tags**: `#decisions` `#employee-360` `#cost-optimisation` `#reconciliation` `#field-economics` `#illustrative-policies`

---

## 1. Verbatim Transcript

> "I agree with 1 to 5. on 6th keep it illustrative. 7. on the data side on employee it should be realistic and we need to generate one big query table with all the possible type of details one can ask. eg the salary breakdown, benefits, hrs, da, health insurance and all the other that will be important to employees and management in terms of cost optimisation, the employee count is another factors, revenue per employee basically all the kind of analysis one may think of running and ask for insights, operating cost per field when one goes on a field level detail and they should match to the total company level aggregate"

*(Lightly spell-corrected from the typed original; meaning unchanged.)*

---

## 2. Decisions Recorded (answers to the diagnosis §7)

| # | Decision | Answer |
|---|---|---|
| 1 | Finance source of truth | **Approved.** Zero-error primary = ONGC Annual Reports (standalone FY17–FY26, consolidated FY22–FY26), backfilled by NSE XBRL; Yahoo Finance = separately labelled consolidated view (FY23–FY26) + cross-check + market data. |
| 2 | Download public data | **Approved.** Fetch ARs FY16–FY19 and NSE XBRL files into `knowledge/public_sources/`. |
| 3 | WIP snapshot | **Approved.** Committed locally as branch `wip/pre-v3-snapshot` (no push). |
| 4 | Docs | **Approved.** Update `BUILD.md`, `UPGRADE_CHECKLIST.md`, `feature_list.md` in place as v3; archive prior versions under `docs/archive/`. |
| 5 | DCF timing | **Approved.** DCF agent is built after the real finance SSOT lands. |
| 6 | Gemini-generated policy clauses | **Keep, labelled "Illustrative".** |
| 7 | Employee data | **New requirement** (below). |

---

## 3. Core Requirement Identified (Decision 7)

1. **Realistic employee data**: plausible ONGC pay structure, career pyramid, names, postings — not a toy dataset.
2. **One comprehensive BigQuery table** (employee-360) containing every attribute an employee or management might ask about: salary breakdown (basic, DA, HRA, allowances, perks), benefits (health insurance / medical, PF, superannuation, gratuity, leave encashment, LTC …), and other cost-relevant details.
3. **Cost-optimisation analytics**: headcount, cost per employee, revenue per employee, overtime, allowance mix, etc. — any analysis a CMD / Director might ask for insights on.
4. **Field-level drill-down**: operating cost per field; field values must **sum exactly to the company-level aggregates** (which are themselves real, public AR numbers).

---

## 4. Key Directives Extracted

* **Employee-360 table** in BigQuery: one wide, analysis-ready table (grain to be specified in SPEC-04) covering identity, grade, function, location, tenure, full pay & benefit components, leave, overtime, and cost-to-company.
* **Hard reconciliation**: Σ employee cost per FY = AR "Employee benefits expense" (gross, incl. capitalised portion); Σ field opex per FY = AR P&L cost lines; headcount = AR "Number of Employees". Reconciliation checks are automated and block publication on mismatch.
* **Derived KPIs available to the agent**: revenue per employee, employee cost per employee, cost-to-company, opex per field / per boe, overtime share, allowance share, etc.
* **Illustrative labelling** for synthetic policies (Decision 6) and for employee-level synthetic records.
