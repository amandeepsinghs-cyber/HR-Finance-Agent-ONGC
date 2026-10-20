-- Answer Key Follow-up SQL: C13__why
-- Question: What one-time transfer grant, composite transfer allowance (CTA), and baggage transportation costs would be incurred?
-- Type: what_if
-- Semantic audit 2026-10-20: old SQL counted current executives in Delhi/Dehradun by city - no cost at all.
-- Now: per-officer averages of transfer grant, composite transfer grant (CTA) and baggage transport cost from
-- actual E3-E5 rotation / hard-station postings in FY24-FY26 (posting_history, cost > 0), scaled to the 200
-- officers in the scenario (scenario parameter from the question), plus the total.

WITH b AS (
    SELECT transfer_grant_inr, composite_transfer_grant_cta_inr, baggage_transport_cost_inr, total_transfer_cost_inr
    FROM posting_history
    WHERE fiscal_year IN ('FY24', 'FY25', 'FY26') AND grade_id IN ('E3', 'E4', 'E5')
      AND LOWER(posting_type) IN ('rotation', 'hard_station') AND total_transfer_cost_inr > 0
),
s AS (
    SELECT COUNT(*) AS postings_basis,
           AVG(transfer_grant_inr) AS tg, AVG(composite_transfer_grant_cta_inr) AS cta,
           AVG(baggage_transport_cost_inr) AS bag, AVG(total_transfer_cost_inr) AS tot,
           MIN(total_transfer_cost_inr) AS min_tot, MAX(total_transfer_cost_inr) AS max_tot
    FROM b
)
SELECT component, per_officer_inr, ROUND(per_officer_inr * 200 / 1e7, 2) AS cost_for_200_officers_cr, postings_basis
FROM (
    SELECT 'One-time transfer grant' AS component, 1 AS ord, ROUND(tg, 0) AS per_officer_inr, postings_basis FROM s
    UNION ALL SELECT 'Composite transfer grant (CTA)', 2, ROUND(cta, 0), postings_basis FROM s
    UNION ALL SELECT 'Baggage transportation', 3, ROUND(bag, 0), postings_basis FROM s
    UNION ALL SELECT 'Total one-time cost', 4, ROUND(tot, 0), postings_basis FROM s
)
ORDER BY ord;
