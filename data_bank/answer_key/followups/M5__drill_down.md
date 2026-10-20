# Answer Key: M5__drill_down

**Question:** Break down the unauthorized access attempts by department (HR vs Finance vs Operations) and data type (salary, transfer, P&L).
**Type:** `data` | **Result Count:** `7` rows | **Execution:** `0.66s`

## Executive Synthesis
This week's 15 denied attempts split HR 10, Governance 3, Finance 2; no Operations user appears. The most-targeted data is confidential_transfer_draft (draft_transfer_list, 4 denials from HR), and HR staff account for most salary, DPC and transfer-draft probes. Window: 13-19 Oct 2026.

### Summary Result Table
| user_department | resource_data_classification | requested_resource | denial_count | distinct_users |
| --- | --- | --- | --- | --- |
| HR | confidential_transfer_draft | draft_transfer_list | 4 | 4 |
| Governance | confidential_vigilance | vigilance_inquiry | 3 | 3 |
| HR | confidential_dpc | dpc_proceedings | 3 | 3 |
| HR | confidential_salary | individual_salary_record | 2 | 2 |
| Finance | confidential_field_pnl | field_pnl_summary | 1 | 1 |
| Finance | confidential_salary | individual_salary_record | 1 | 1 |
| HR | confidential_field_pnl | field_pnl_summary | 1 | 1 |