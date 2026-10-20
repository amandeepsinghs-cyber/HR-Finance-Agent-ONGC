# Answer Key: M5__compare_or_so_what

**Question:** How does this week's frequency of access violations compare with the 30-day baseline security audit log?
**Type:** `data` | **Result Count:** `6` rows | **Execution:** `0.63s`

## Executive Synthesis
This week's 15 confidential-data denials are 1.95x the 30-day baseline of 7.7 per week (33 in 13-Sep to 12-Oct). The rise is led by confidential_transfer_draft (4 vs 1.2/week) and confidential_dpc (3 vs 1.2/week). Counts are small, so a single week roughly doubling is a watch signal rather than an incident.

### Summary Result Table
| classification | denials_this_week | denials_prior_30d | baseline_per_week | ratio_vs_baseline |
| --- | --- | --- | --- | --- |
| ALL CONFIDENTIAL | 15 | 33 | 7.7 | 1.95 |
| confidential_transfer_draft | 4 | 5 | 1.17 | 3.43 |
| confidential_dpc | 3 | 5 | 1.17 | 2.57 |
| confidential_vigilance | 3 | 9 | 2.1 | 1.43 |
| confidential_salary | 3 | 5 | 1.17 | 2.57 |
| confidential_field_pnl | 2 | 9 | 2.1 | 0.95 |