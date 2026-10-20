# Answer Key: P7__compare_or_so_what

**Question:** How does the lodging entitlement for Class-A cities like Mumbai and Delhi compare with Class-B field work centres?
**Type:** `policy` | **Result Count:** `4` rows | **Execution:** `0.68s`

## Executive Synthesis
On actual claims, Class-A cities like Mumbai and Delhi reimburse lodging at ₹4,500 per night for E1-E3 versus ₹3,000 in Class-B field centres - a +50% premium; Class-C and offshore stays are also paid at ₹3,000. E4 is the exception: dim_grade gives E4 a Class-A ceiling of ₹6,500, but E4 claims are paid at only ₹4,500 - the grade master and the claims engine disagree. No Class-B ceiling exists in dim_grade or in the TA Regulations text, so the Class-B figure is inferred from 13,976 E1-E4 claims rather than from a published rule.

### Summary Result Table
| grade_id | cat_a_ceiling_inr | class_a_per_night_inr | class_b_per_night_inr | class_c_per_night_inr | offshore_per_night_inr | claims |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | 4500.0 | 4500.0 | 3000.0 | 3000.0 | 3000.0 | 2268 |
| E2 | 4500.0 | 4500.0 | 3000.0 | 3000.0 | 3000.0 | 3389 |
| E3 | 4500.0 | 4500.0 | 3000.0 | 3000.0 | 3000.0 | 4300 |
| E4 | 6500.0 | 4500.0 | 3000.0 | 3000.0 | 3000.0 | 4019 |