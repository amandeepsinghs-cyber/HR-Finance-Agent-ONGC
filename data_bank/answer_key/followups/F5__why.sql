-- Answer Key Follow-up SQL: F5__why
-- Question: What contract variations, scope changes, or standby day rates caused cost overruns on major turnkey contracts?
-- Type: data
-- Semantic audit 2026-10-20: was all years (FY22-FY27 mixed, parent is FY26), all categories, raw rupees, alphabetical.
-- Semantic audit 2026-10-20: Now FY26 overrun PO lines by service category x overrun reason, in crore: overrun (= scope
-- Semantic audit 2026-10-20: variation; revised PO = original + scope variation), standby charges, overrun % of original PO.

SELECT
    po.service_contract_category,
    po.overrun_reason,
    COUNT(*) AS overrun_lines,
    ROUND(SUM(po.cost_overrun_inr) / 1e7, 2) AS cost_overrun_cr,
    ROUND(SUM(po.scope_variation_value_inr) / 1e7, 2) AS scope_variation_cr,
    ROUND(SUM(po.standby_charges_inr) / 1e7, 2) AS standby_charges_cr,
    ROUND(SUM(po.cost_overrun_inr) * 100 / SUM(po.original_po_value_inr), 1) AS overrun_pct_of_original_po
FROM purchase_orders po
WHERE po.fiscal_year = 'FY26'
  AND po.cost_overrun_inr > 0
GROUP BY po.service_contract_category, po.overrun_reason
ORDER BY cost_overrun_cr DESC;
