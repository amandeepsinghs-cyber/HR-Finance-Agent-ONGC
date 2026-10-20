# Answer Key: M5__why

**Question:** Why did specific user accounts trigger repeated RBAC access denials on confidential commercial and personnel tables?
**Type:** `data` | **Result Count:** `5` rows | **Execution:** `0.66s`

## Executive Synthesis
No account triggered repeated denials: across all 102 RBAC denials since 2026-07-21, the most any single user was denied is 1, and 102 distinct users account for them. Each denial was a one-off request for data outside the user's role - Confidential draft transfer proposals under JRTP Section 8 (4 this week), then DPC committee deliberations classified under Regulation 14. The premise of repeat offenders is not supported by the log; the pattern is broad curiosity, which argues for awareness messaging over individual action.

### Summary Result Table
| resource_data_classification | denial_reason | denials_this_week | denials_full_log | distinct_users | max_denials_by_one_user | log_first_date |
| --- | --- | --- | --- | --- | --- | --- |
| confidential_transfer_draft | Confidential draft transfer proposals under JRTP Section 8 | 4 | 25 | 25 | 1 | 2026-07-21 |
| confidential_dpc | DPC committee deliberations classified under Regulation 14 | 3 | 20 | 20 | 1 | 2026-07-21 |
| confidential_salary | Confidential remuneration protected under CDA Rule 5 | 3 | 19 | 19 | 1 | 2026-07-21 |
| confidential_vigilance | Vigilance inquiries confidential under CVC guidelines | 3 | 15 | 15 | 1 | 2026-08-01 |
| confidential_field_pnl | Commercial sensitivity under Disclosure Policy Sec 3.2 | 2 | 23 | 23 | 1 | 2026-07-23 |