# P2H.5 Evidence: Employee-360 Synthetic Generator (pre-G4 r2)

## 1. Test Results
`5 failed, 58 passed in 93.26s (0:01:33)`

## 2. Targets vs Generated Values & Residuals
Knobs are correctly restricted to `[0.85, 1.15]`. Negative "Pool" plugs for lines a and b have been eliminated entirely. Note 35 lines c–f (actuarial provisions and welfare/infra) are booked to SPEC-04 cost pools with the `real_total_modelled_split` basis.

| FY | Target | Generated | Residual % | Knobs |
|---|---|---|---|---|
| FY17 | 11,550.77 Cr | 9,691.70 Cr | 16.09% | 1.15 |
| FY18 | 11,381.05 Cr | 9,205.11 Cr | 19.12% | 1.15 |
| FY19 | 12,113.03 Cr | 10,189.55 Cr | 15.88% | 1.15 |
| FY20 | 11,512.40 Cr | 10,350.84 Cr | 10.09% | 1.15 |
| FY21 | 10,126.54 Cr | 10,124.80 Cr | 0.02% | 1.15 |
| FY22 | 11,082.09 Cr | 9,754.34 Cr | 11.98% | 1.15 |
| FY23 | 10,620.71 Cr | 9,730.10 Cr | 8.39% | 1.15 |
| FY24 | 10,525.66 Cr | 10,316.16 Cr | 1.99% | 1.15 |
| FY25 | 10,720.52 Cr | 10,565.23 Cr | 1.45% | 1.15 |
| FY26 | 10,210.71 Cr | 10,174.08 Cr | 0.36% | 1.15 |


## 3. Findings & Blocker
The generator now perfectly generates the historic statutory headcount targets (R10: 33,660 for FY17).
However, with the 1.15x multiplier cap, the FY17 Line A (Salaries) target of ₹7,440 Cr cannot be met. The 2007 scales (e.g. E1 starting at ₹24,900) simply produce too low a baseline (~16.3L avg CTC) to hit the statutory 22.1L avg target without a higher `k_fy` multiplier.
As instructed ("If a line truly cannot be met within the bounds, stop and report the gap with the reason; never loosen tests"), I am blocked from committing because the tests are red, and I will report this to the coordinator.
