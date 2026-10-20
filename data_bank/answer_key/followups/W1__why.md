# Answer Key: W1__why

**Question:** Why do high-lifting-cost onshore assets suffer greater financial vulnerability to crude price contractions?
**Type:** `what_if` | **Result Count:** `5` rows | **Execution:** `0.65s`

## Executive Synthesis
High-lifting-cost onshore fields are the most exposed because their thin margins absorb the same per-barrel price cut: the 5 onshore fields at $37.67/boe lose 53.5% of EBITDA at $60, versus 5.2% for low-cost offshore fields ($5.89/boe). Their simulated margin falls to 12.9% and 3 of them go PBT-negative; no other segment has a loss-maker. Costs are fixed in the model, so vulnerability scales with cost per barrel, not with size.

### Summary Result Table
| onshore_offshore | lifting_cost_band | n_fields | wtd_lifting_cost_usd_boe | base_ebitda_cr | sim_ebitda_at_60_cr | ebitda_change_pct | sim_ebitda_margin_pct | fields_pbt_negative_at_60 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| onshore | 1 high (>= $20/boe) | 5 | 37.67 | 410.71 | 191.05 | -53.5 | 12.9 | 3 |
| offshore | 2 mid ($10-20/boe) | 8 | 12.0 | 27845.21 | 22073.14 | -20.7 | 52.0 | 0 |
| onshore | 2 mid ($10-20/boe) | 23 | 13.47 | 12900.99 | 10256.87 | -20.5 | 54.1 | 0 |
| onshore | 3 low (< $10/boe) | 12 | 6.39 | 13231.51 | 11826.4 | -10.6 | 65.9 | 0 |
| offshore | 3 low (< $10/boe) | 5 | 5.89 | 20889.46 | 19809.69 | -5.2 | 66.4 | 0 |