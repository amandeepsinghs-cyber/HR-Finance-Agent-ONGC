# Answer Key: E3__drill_down

**Question:** What is the settlement breakdown between approved claim amount, deduction heads, and net payable for my recent medical claims?
**Type:** `data` | **Result Count:** `2` rows | **Execution:** `0.65s`

## Executive Synthesis
Settlement breakdown — CLM-P002: ₹42,000 claimed, still pending_scrutiny so no approval or deduction yet; CLM-P001: claimed ₹18,500, deduction ₹1,300 (non_reimbursable_consumables), net payable ₹17,200. Across your claims, ₹1,300 has been deducted out of ₹60,500 claimed.

### Summary Result Table
| claim_id | claim_status | claimed_amount_inr | approved_amount_inr | deduction_amount_inr | deduction_reason | net_payable_inr |
| --- | --- | --- | --- | --- | --- | --- |
| CLM-P002 | pending_scrutiny | 42000.0 | 0.0 | 0.0 | none | 0.0 |
| CLM-P001 | approved_paid | 18500.0 | 17200.0 | 1300.0 | non_reimbursable_consumables | 17200.0 |