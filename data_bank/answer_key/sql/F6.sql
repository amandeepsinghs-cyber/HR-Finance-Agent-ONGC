-- Answer Key SQL: F6
-- Question: How old are receivables from oil marketing companies and gas buyers, by customer?
-- Type: data
-- Semantic audit 2026-10-20: was customer x bucket rows ordered alphabetically with LIMIT 100 (125 combinations exist ->
-- Semantic audit 2026-10-20: 25 rows silently dropped). Now one row per customer with the aging buckets pivoted, total,
-- Semantic audit 2026-10-20: >90-day share and disputed amount. Balances are as at 31-Mar-2026 (only FY26 invoices carry
-- Semantic audit 2026-10-20: outstanding; aging_days is measured from invoice date to FY26 year-end).

SELECT
    c.short_name AS customer,
    c.type AS customer_type,
    STRING_AGG(DISTINCT r.product_type, ', ') AS products,
    ROUND(SUM(r.outstanding_amount_inr_cr), 1) AS outstanding_cr,
    ROUND(SUM(IF(r.aging_days <= 30, r.outstanding_amount_inr_cr, 0)), 1) AS d0_30_cr,
    ROUND(SUM(IF(r.aging_days BETWEEN 31 AND 60, r.outstanding_amount_inr_cr, 0)), 1) AS d31_60_cr,
    ROUND(SUM(IF(r.aging_days BETWEEN 61 AND 90, r.outstanding_amount_inr_cr, 0)), 1) AS d61_90_cr,
    ROUND(SUM(IF(r.aging_days BETWEEN 91 AND 180, r.outstanding_amount_inr_cr, 0)), 1) AS d91_180_cr,
    ROUND(SUM(IF(r.aging_days > 180, r.outstanding_amount_inr_cr, 0)), 1) AS d180_plus_cr,
    ROUND(SUM(IF(r.aging_days > 90, r.outstanding_amount_inr_cr, 0)) * 100 / SUM(r.outstanding_amount_inr_cr), 1) AS over_90d_pct,
    ROUND(SUM(IF(r.is_disputed, r.outstanding_amount_inr_cr, 0)), 1) AS disputed_cr
FROM receivables r
LEFT JOIN dim_customer c ON r.customer_id = c.customer_id
WHERE r.outstanding_amount_inr_cr > 0
GROUP BY c.short_name, c.type
ORDER BY outstanding_cr DESC;
