-- Answer Key SQL: P13
-- Question: Are we within the DPE 30% superannuation cap on benefits? How much headroom is left?
-- Type: policy_plus_data
-- Semantic audit 2026-10-20: Old SQL listed benefit_liabilities.annual_payout_inr_cr (benefits PAID to retirees) and a flag;
-- Semantic audit 2026-10-20: the DPE cap (PRBS Clause 3.1) is on EMPLOYER CONTRIBUTIONS as % of (Basic Pay + DA). Now computed
-- Semantic audit 2026-10-20: from payroll_monthly: employer CPF + PRBS + PRMB; gratuity is not in payroll, so its accrual rate is
-- Semantic audit 2026-10-20: imputed as superannuation_benefit_pct minus the three payroll rates (stated as an assumption).
-- Semantic audit 2026-10-20: FY25 and FY26 full years plus FY27 YTD (Apr-Sep, 6 months; rates comparable, crore amounts are not).
WITH p AS (
    SELECT fiscal_year,
        COUNT(DISTINCT month) AS months_covered,
        SUM(basic_pay_inr + da_inr) / 1e7 AS basic_da_cr,
        SUM(employer_cpf_inr) / 1e7 AS cpf_cr,
        SUM(employer_prbs_inr) / 1e7 AS prbs_cr,
        SUM(employer_prmb_inr) / 1e7 AS prmb_cr,
        SUM(superannuation_benefit_pct / 100 * (basic_pay_inr + da_inr)) / 1e7 AS total_super_cr
    FROM payroll_monthly
    WHERE fiscal_year IN ('FY25', 'FY26', 'FY27')
    GROUP BY fiscal_year
)
SELECT
    fiscal_year,
    months_covered,
    ROUND(basic_da_cr, 1) AS basic_plus_da_cr,
    ROUND(100 * cpf_cr / basic_da_cr, 2) AS cpf_pct,
    ROUND(100 * prbs_cr / basic_da_cr, 2) AS prbs_pct,
    ROUND(100 * prmb_cr / basic_da_cr, 2) AS prmb_pct,
    ROUND(100 * (total_super_cr - cpf_cr - prbs_cr - prmb_cr) / basic_da_cr, 2) AS gratuity_pct_imputed,
    ROUND(100 * total_super_cr / basic_da_cr, 2) AS total_employer_super_pct,
    30.0 AS dpe_cap_pct,
    ROUND(30.0 - 100 * total_super_cr / basic_da_cr, 2) AS headroom_pct_points,
    ROUND(total_super_cr, 1) AS employer_super_contribution_cr,
    ROUND(0.30 * basic_da_cr, 1) AS cap_amount_cr,
    ROUND(0.30 * basic_da_cr - total_super_cr, 1) AS headroom_cr,
    100 * total_super_cr / basic_da_cr <= 30.0 AS within_cap
FROM p
ORDER BY fiscal_year;
