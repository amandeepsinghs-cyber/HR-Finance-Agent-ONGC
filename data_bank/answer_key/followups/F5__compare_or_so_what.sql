-- Answer Key Follow-up SQL: F5__compare_or_so_what
-- Question: How does actual contract expenditure compare against the initial purchase order commitment and engineer's estimate?
-- Type: data
-- Semantic audit 2026-10-20: was paid minus engineer's estimate per PO number for overrun POs only, all years mixed,
-- Semantic audit 2026-10-20: 100 alphabetical rows. Now FY26 by service category plus an all-category total: engineer's
-- Semantic audit 2026-10-20: estimate, original PO, revised PO, actual paid (crore), PO vs estimate and paid vs PO ratios.

SELECT
    COALESCE(po.service_contract_category, 'ALL CATEGORIES') AS service_contract_category,
    ROUND(SUM(po.engineers_estimate_inr) / 1e7, 1) AS engineers_estimate_cr,
    ROUND(SUM(po.original_po_value_inr) / 1e7, 1) AS original_po_cr,
    ROUND(SUM(po.revised_po_value_inr) / 1e7, 1) AS revised_po_cr,
    ROUND(SUM(po.actual_paid_amount_inr) / 1e7, 1) AS actual_paid_cr,
    ROUND((SUM(po.original_po_value_inr) / SUM(po.engineers_estimate_inr) - 1) * 100, 2) AS po_vs_estimate_pct,
    ROUND(SUM(po.actual_paid_amount_inr) * 100 / SUM(po.original_po_value_inr), 1) AS paid_pct_of_original_po,
    ROUND(SUM(po.actual_paid_amount_inr) * 100 / SUM(po.engineers_estimate_inr), 1) AS paid_pct_of_estimate
FROM purchase_orders po
WHERE po.fiscal_year = 'FY26'
GROUP BY ROLLUP (po.service_contract_category)
ORDER BY po.service_contract_category IS NULL DESC, actual_paid_cr DESC;
