-- Answer Key Follow-up SQL: P13__drill_down
-- Question: What is the exact percentage breakdown of basic pay + DA contributed to CPF, PRBS pension, gratuity, and post-retirement medical?
-- Type: policy_plus_data
-- Semantic audit 2026-10-20: Old SQL returned actuarial liabilities and retiree payouts, not contributions as % of Basic+DA.
-- Semantic audit 2026-10-20: Now FY26 employer contribution by scheme from payroll_monthly (gratuity imputed = superannuation_benefit_pct
-- Semantic audit 2026-10-20: minus CPF/PRBS/PRMB rates), next to the PRBS Clause 3.1 reference rates.
WITH p AS (
    SELECT
        SUM(basic_pay_inr + da_inr) AS bda,
        SUM(employer_cpf_inr) AS cpf,
        SUM(employer_prbs_inr) AS prbs,
        SUM(employer_prmb_inr) AS prmb,
        SUM(superannuation_benefit_pct / 100 * (basic_pay_inr + da_inr)) AS tot
    FROM payroll_monthly
    WHERE fiscal_year = 'FY26'
)
SELECT scheme, ROUND(amount / 1e7, 1) AS employer_contribution_cr, ROUND(100 * amount / bda, 2) AS pct_of_basic_da,
       policy_reference_rate, source
FROM p, UNNEST([
    STRUCT('Contributory Provident Fund (CPF)' AS scheme, cpf AS amount, '12.00%' AS policy_reference_rate, 'payroll_monthly.employer_cpf_inr' AS source, 1 AS ord),
    STRUCT('PRBS pension', prbs, '6.00-9.50% (balancing)', 'payroll_monthly.employer_prbs_inr', 2),
    STRUCT('Post-retirement medical (PRMB)', prmb, '4.00%', 'payroll_monthly.employer_prmb_inr', 3),
    STRUCT('Gratuity (imputed)', tot - cpf - prbs - prmb, '4.16-4.50%', 'superannuation_benefit_pct minus payroll schemes', 4),
    STRUCT('Total employer superannuation', tot, '30.00% cap', 'payroll_monthly.superannuation_benefit_pct', 5)
])
ORDER BY ord;
