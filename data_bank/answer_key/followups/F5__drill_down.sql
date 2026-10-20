-- Answer Key Follow-up SQL: F5__drill_down
-- Question: What are the major service contract categories (rig charter, OSV hire, subsea EPC, directional drilling) dominating the top spend?
-- Type: data
-- Semantic audit 2026-10-20: was revised PO value (raw rupees) for all POs, sorted alphabetically. Now FY26 paid spend in
-- Semantic audit 2026-10-20: crore restricted to the parent's top-80% vendor set, by service category, ranked, with share
-- Semantic audit 2026-10-20: and overrun.

WITH v AS (
    SELECT vendor_id, SUM(actual_paid_amount_inr) AS paid
    FROM purchase_orders
    WHERE fiscal_year = 'FY26'
    GROUP BY vendor_id
),
top80 AS (
    SELECT vendor_id
    FROM (
        SELECT vendor_id, paid,
               SUM(paid) OVER (ORDER BY paid DESC, vendor_id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) / SUM(paid) OVER () * 100 AS cum
        FROM v
    )
    WHERE cum - paid / (SELECT SUM(paid) FROM v) * 100 < 80
)
SELECT
    po.service_contract_category,
    COUNT(DISTINCT po.vendor_id) AS vendors,
    COUNT(DISTINCT po.po_number) AS pos,
    ROUND(SUM(po.actual_paid_amount_inr) / 1e7, 1) AS paid_fy26_cr,
    ROUND(SUM(po.actual_paid_amount_inr) * 100 / SUM(SUM(po.actual_paid_amount_inr)) OVER (), 1) AS share_of_top80_spend_pct,
    ROUND(SUM(po.cost_overrun_inr) / 1e7, 2) AS cost_overrun_cr
FROM purchase_orders po
JOIN top80 t ON t.vendor_id = po.vendor_id
WHERE po.fiscal_year = 'FY26'
GROUP BY po.service_contract_category
ORDER BY paid_fy26_cr DESC;
