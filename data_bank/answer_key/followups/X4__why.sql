-- Answer Key Follow-up SQL: X4__why
-- Question: What demographic aging trends and discount rate assumptions drove the expansion of actuarial liabilities over 5 years?
-- Type: data
-- Semantic audit 2026-10-20: Drivers over FY22-FY26 for PRBS + PRMB: discount rate, active vs retiree members (ageing), combined
-- obligation and obligation per retiree. Old SQL looked at the medical scheme only and had no demographic fields.
SELECT
    fiscal_year,
    MAX(discount_rate_pct) AS discount_rate_pct,
    MAX(medical_inflation_rate_pct) AS medical_inflation_rate_pct,
    MAX(active_members_covered) AS active_members,
    MAX(retiree_beneficiaries_covered) AS retiree_beneficiaries,
    ROUND(MAX(retiree_beneficiaries_covered) / MAX(active_members_covered), 2) AS retirees_per_active,
    SUM(actuarial_liability_inr_cr) AS combined_liability_cr,
    ROUND(SUM(actuarial_liability_inr_cr) * 1e7 / MAX(retiree_beneficiaries_covered) / 1e5, 1) AS liability_per_retiree_lakh,
    SUM(annual_payout_inr_cr) AS combined_annual_payout_cr
FROM benefit_liabilities
WHERE LOWER(scheme_type) IN ('prbs pension', 'post-retirement medical')
GROUP BY fiscal_year
ORDER BY fiscal_year;
