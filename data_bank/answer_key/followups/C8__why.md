# Answer Key: C8__why

**Question:** What technical operating constraints make in-house secondary/tertiary recovery uneconomic compared to third-party PEC operators?
**Type:** `data` | **Result Count:** `3` rows | **Execution:** `0.71s`

## Executive Synthesis
The binding constraints are extreme water cut and a fixed in-house workforce on tiny volumes: the candidate fields run at 93.9% and 93.8% water cut (company 49.5%), lifting 15.4 and 15.2 barrels of water per BOE against 2.2. That pushes lifting cost to $48.12 and $46.49/BOE vs $9.13, of which manpower alone is $32.23 and $31.04 vs $3.00, with only 1,284 and 1,335 BOE per regular employee (company 18,167). Uptime is in line with the company (97.2% and 96.8% vs 97.1%), so the problem is cost structure, not reliability - which is what a lean PEC operator changes; third-party PEC cost benchmarks are not in the data.

### Summary Result Table
| field_name | water_cut_pct | water_bbl_per_boe | avg_uptime_pct | well_downtime_hours | lifting_cost_usd_boe | manpower_cost_usd_boe | boe_per_regular_employee | root_cause_loss_code |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Champang | 93.9 | 15.4 | 97.2 | 4019.0 | 48.12 | 32.23 | 1284.0 | high_water_cut_depleted |
| Borholla | 93.8 | 15.2 | 96.8 | 4559.0 | 46.49 | 31.04 | 1335.0 | None |
| All FY26 fields (benchmark) | 49.5 | 2.2 | 97.1 | 9146.0 | 9.13 | 3.0 | 18167.0 | None |