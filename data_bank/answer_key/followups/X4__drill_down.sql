-- Answer Key Follow-up SQL: X4__drill_down
-- Question: What is the actuarial valuation breakdown between Post-Retirement Medical Scheme (PRMB) and PRBS pension liabilities?
-- Type: data
-- Semantic audit 2026-10-20: FY26 valuation breakdown PRMB vs PRBS: obligation, share of combined, plan assets, net, funded ratio and
-- actuarial assumptions. Old SQL listed assumptions for all four schemes and no liability split.
SELECT
    scheme_name,
    scheme_type,
    actuarial_liability_inr_cr AS actuarial_liability_cr,
    ROUND(actuarial_liability_inr_cr * 100 / SUM(actuarial_liability_inr_cr) OVER (), 1) AS share_of_combined_pct,
    plan_assets_inr_cr AS plan_assets_cr,
    net_liability_inr_cr AS net_unfunded_cr,
    funded_ratio_pct,
    discount_rate_pct,
    salary_escalation_rate_pct,
    medical_inflation_rate_pct,
    active_members_covered,
    retiree_beneficiaries_covered
FROM benefit_liabilities
WHERE fiscal_year = 'FY26' AND LOWER(scheme_type) IN ('prbs pension', 'post-retirement medical')
ORDER BY actuarial_liability_cr DESC;
