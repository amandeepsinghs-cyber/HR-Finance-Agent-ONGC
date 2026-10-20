# Answer Key: T1__why

**Question:** What are the primary operational factors (water cut >90%, low gas utilization, aging infrastructure) behind Field X's losses?
**Type:** `chain` | **Result Count:** `3` rows | **Execution:** `0.68s`

## Executive Synthesis
Champang is losing because it is a depleted, high-water-cut field: water cut averages 93.9% versus 76.6% for mature onshore peers, driving lifting cost to $48.12/boe against $15.49. Gas utilisation (97.5% vs 97.5%) and uptime (97.23% vs 97.21%) are in line with peers, so low gas utilisation is not a factor; the field is 53 years old (peers 50), consistent with ageing, depleted reservoirs. Recorded root cause: high_water_cut_depleted.

### Summary Result Table
| comparison_group | n_fields | root_cause | avg_water_cut_pct | avg_gas_utilisation_pct | avg_uptime_pct | downtime_hrs_per_well_month | avg_field_age_years | avg_lifting_cost_usd_boe | water_handling_pct_of_opex | avg_pbt_inr_cr |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Field X: Champang | 1 | high_water_cut_depleted | 93.9 | 97.5 | 97.23 | 22.3 | 53.0 | 48.12 | 2.4 | -4.93 |
| Mature onshore peers (excl. Field X) | 34 | None | 76.6 | 97.5 | 97.21 | 21.9 | 50.4 | 15.49 | 2.7 | 572.68 |
| All fields | 53 | None | 65.1 | 97.5 | 97.07 | 22.9 | 46.0 | 14.29 | 1.2 | 973.16 |