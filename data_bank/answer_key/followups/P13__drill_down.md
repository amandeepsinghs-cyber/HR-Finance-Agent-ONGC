# Answer Key: P13__drill_down

**Question:** What is the exact percentage breakdown of basic pay + DA contributed to CPF, PRBS pension, gratuity, and post-retirement medical?
**Type:** `policy_plus_data` | **Result Count:** `5` rows | **Execution:** `0.78s`

## Executive Synthesis
In FY26 the employer put 12.00% of Basic + DA into CPF, 8.40% into PRBS pension, 4.20% into gratuity and 3.00% into post-retirement medical, 27.60% in total (₹1,372 cr). PRMB at 3.00% is below the 4.00% reference rate in PRBS Clause 3.1, while PRBS (₹418 cr) sits inside its 6.00-9.50% (balancing) band. Gratuity is imputed from the payroll superannuation rate because it is not booked in payroll.

### Summary Result Table
| scheme | employer_contribution_cr | pct_of_basic_da | policy_reference_rate | source |
| --- | --- | --- | --- | --- |
| Contributory Provident Fund (CPF) | 596.7 | 12.0 | 12.00% | payroll_monthly.employer_cpf_inr |
| PRBS pension | 417.7 | 8.4 | 6.00-9.50% (balancing) | payroll_monthly.employer_prbs_inr |
| Post-retirement medical (PRMB) | 149.2 | 3.0 | 4.00% | payroll_monthly.employer_prmb_inr |
| Gratuity (imputed) | 208.9 | 4.2 | 4.16-4.50% | superannuation_benefit_pct minus payroll schemes |
| Total employer superannuation | 1372.5 | 27.6 | 30.00% cap | payroll_monthly.superannuation_benefit_pct |