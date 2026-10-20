-- Answer Key SQL: X4
-- Question: What is our pension and post-retirement medical liability, and its 5-year trend?
-- Type: data
-- Semantic audit 2026-10-20: Adds the 5-year trend the question asks for (old SQL returned FY26 only, and mixed in PF and gratuity).
-- One row per FY (FY22-FY26; FY21 not in benefit_liabilities) with PRBS pension and PRMB medical obligations,
-- plan assets and net unfunded. Balances are taken per FY, never summed across years.
SELECT
    fiscal_year,
    SUM(IF(LOWER(scheme_type) = 'prbs pension', actuarial_liability_inr_cr, 0)) AS prbs_pension_liability_cr,
    SUM(IF(LOWER(scheme_type) = 'post-retirement medical', actuarial_liability_inr_cr, 0)) AS prmb_medical_liability_cr,
    SUM(actuarial_liability_inr_cr) AS combined_liability_cr,
    SUM(plan_assets_inr_cr) AS combined_plan_assets_cr,
    SUM(net_liability_inr_cr) AS combined_net_unfunded_cr,
    ROUND(SUM(plan_assets_inr_cr) * 100 / SUM(actuarial_liability_inr_cr), 1) AS combined_funded_pct
FROM benefit_liabilities
WHERE LOWER(scheme_type) IN ('prbs pension', 'post-retirement medical')
GROUP BY fiscal_year
ORDER BY fiscal_year;
