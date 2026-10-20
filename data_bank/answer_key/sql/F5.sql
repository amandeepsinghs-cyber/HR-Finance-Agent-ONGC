-- Answer Key SQL: F5
-- Question: Which contracts or vendors make up the top 80% of spend, and where were the cost overruns?
-- Type: data
-- Semantic audit 2026-10-20: was every vendor alphabetically with LIMIT 100 (no Pareto cut), grouped by vendor NAME
-- Semantic audit 2026-10-20: (2,000 vendor_ids share 1,975 names -> merged vendors), raw rupees. Now FY26 (last full FY)
-- Semantic audit 2026-10-20: paid spend by vendor_id, cumulative share, and only vendors inside the top 80% of spend
-- Semantic audit 2026-10-20: (incl. the vendor that crosses 80%), with cost overrun (revised - original PO) in crore.

WITH v AS (
    SELECT
        po.vendor_id,
        SUM(po.actual_paid_amount_inr) / 1e7 AS paid_cr,
        SUM(po.original_po_value_inr) / 1e7 AS original_po_cr,
        SUM(po.cost_overrun_inr) / 1e7 AS overrun_cr,
        COUNTIF(po.cost_overrun_inr > 0) AS overrun_lines,
        COUNT(DISTINCT po.po_number) AS pos
    FROM purchase_orders po
    WHERE po.fiscal_year = 'FY26'
    GROUP BY po.vendor_id
),
r AS (
    SELECT *,
        ROW_NUMBER() OVER (ORDER BY paid_cr DESC, vendor_id) AS spend_rank,
        SUM(paid_cr) OVER (ORDER BY paid_cr DESC, vendor_id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
            / SUM(paid_cr) OVER () * 100 AS cum_share_pct,
        SUM(paid_cr) OVER () AS total_paid_cr,
        COUNT(*) OVER () AS total_vendors,
        SUM(overrun_cr) OVER () AS total_overrun_cr
    FROM v
)
SELECT
    r.spend_rank,
    r.vendor_id,
    d.name AS vendor_name,
    d.category AS vendor_category,
    r.pos,
    ROUND(r.paid_cr, 2) AS paid_fy26_cr,
    ROUND(r.cum_share_pct, 2) AS cum_share_pct,
    ROUND(r.overrun_cr, 2) AS cost_overrun_cr,
    ROUND(r.overrun_cr * 100 / NULLIF(r.original_po_cr, 0), 2) AS overrun_pct_of_po,
    r.overrun_lines,
    ROUND(r.total_paid_cr, 0) AS total_paid_all_vendors_cr,
    r.total_vendors,
    ROUND(r.total_overrun_cr, 1) AS total_overrun_all_vendors_cr
FROM r
LEFT JOIN dim_vendor d ON d.vendor_id = r.vendor_id
WHERE r.cum_share_pct - r.paid_cr / r.total_paid_cr * 100 < 80
ORDER BY r.spend_rank;
