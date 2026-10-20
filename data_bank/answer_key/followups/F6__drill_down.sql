-- Answer Key Follow-up SQL: F6__drill_down
-- Question: Which public sector OMCs (IOCL, BPCL, HPCL) or regional gas consumers have outstanding dues aged beyond 90 days?
-- Type: data
-- Semantic audit 2026-10-20: filtered dim_customer.type = 'PSU' exactly, which dropped HPCL and MRPL ('PSU / Subsidiary')
-- Semantic audit 2026-10-20: and every gas consumer (State PSU, City Gas JV, Private); sorted alphabetically. Now every
-- Semantic audit 2026-10-20: customer with >90-day dues, tagged OMC/refiner vs gas consumer, ranked by >90-day amount.

SELECT
    c.short_name AS customer,
    c.type AS customer_type,
    IF(c.short_name IN ('IOCL', 'BPCL', 'HPCL', 'MRPL', 'CPCL', 'NRL', 'RIL', 'Nayara'), 'OMC / refiner (crude)', 'Gas / other consumer') AS segment,
    ROUND(SUM(r.outstanding_amount_inr_cr), 1) AS over_90d_cr,
    ROUND(SUM(IF(r.aging_days > 180, r.outstanding_amount_inr_cr, 0)), 1) AS over_180d_cr,
    COUNT(*) AS invoices,
    MAX(r.aging_days) AS oldest_days,
    ROUND(SUM(IF(r.is_disputed, r.outstanding_amount_inr_cr, 0)), 1) AS disputed_cr
FROM receivables r
JOIN dim_customer c ON r.customer_id = c.customer_id
WHERE r.outstanding_amount_inr_cr > 0 AND r.aging_days > 90
GROUP BY c.short_name, c.type
ORDER BY over_90d_cr DESC;
