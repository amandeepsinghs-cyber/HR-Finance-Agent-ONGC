-- Answer Key Follow-up SQL: F6__why
-- Question: What billing disputes, price reconciliation delays, or subsidy settlement issues delayed clearance of aged trade receivables?
-- Type: data
-- Semantic audit 2026-10-20: SQL was directionally right but alphabetical, unlabelled metric and no aged-receivable share.
-- Semantic audit 2026-10-20: Now disputed balances by reason with invoices, average age, product, and share of all >90-day
-- Semantic audit 2026-10-20: dues (as at 31-Mar-2026). No subsidy-settlement reason exists in the data (GAP).

SELECT
    r.dispute_reason,
    STRING_AGG(DISTINCT r.product_type, ', ') AS products,
    COUNT(*) AS invoices,
    COUNT(DISTINCT r.customer_id) AS customers,
    ROUND(SUM(r.outstanding_amount_inr_cr), 1) AS disputed_outstanding_cr,
    ROUND(AVG(r.aging_days), 0) AS avg_age_days,
    ROUND(SUM(r.outstanding_amount_inr_cr) * 100
          / (SELECT SUM(outstanding_amount_inr_cr) FROM receivables WHERE outstanding_amount_inr_cr > 0 AND aging_days > 90), 1) AS share_of_over_90d_pct
FROM receivables r
WHERE r.is_disputed = TRUE AND r.outstanding_amount_inr_cr > 0
GROUP BY r.dispute_reason
ORDER BY disputed_outstanding_cr DESC;
