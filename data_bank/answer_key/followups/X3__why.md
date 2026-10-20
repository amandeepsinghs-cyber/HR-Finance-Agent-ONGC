# Answer Key: X3__why

**Question:** What role does fatigue from extended shift overtime play in near-misses and Lost Time Injuries (LTI)?
**Type:** `data` | **Result Count:** `4` rows | **Execution:** `0.64s`

## Executive Synthesis
Fatigue is recorded as a factor in every lost-time injury at high-overtime sites (36 of 36, FY22-FY26) and in none at standard-overtime sites (0 of 38), and high-overtime LTIs occur at 0.211 per million man-hours vs 0.103. Near-misses tell the opposite story: 0.552 per million man-hours at high-overtime sites vs 1.476 elsewhere, with no near-miss fatigue-flagged. So fatigue shows up in injury severity rather than in near-miss reporting - possibly under-reporting of near-misses offshore. Caveat: the fatigue flag appears deterministic (set on all offshore LTIs only), so it should be validated before being used as causal evidence.

### Summary Result Table
| incident_type | overtime_band | incidents_fy22_fy26 | fatigue_flagged_fy22_fy26 | fatigue_flagged_pct | incidents_per_million_manhours |
| --- | --- | --- | --- | --- | --- |
| Lost_Time_Injury_LTI | High overtime (54 h) | 36 | 36 | 100.0 | 0.211 |
| Lost_Time_Injury_LTI | Standard overtime (36 h) | 38 | 0 | 0.0 | 0.103 |
| Near_Miss | High overtime (54 h) | 94 | 0 | 0.0 | 0.552 |
| Near_Miss | Standard overtime (36 h) | 545 | 0 | 0.0 | 1.476 |