-- Answer Key SQL: P16
-- Question: Who has the authority to approve a ₹50 crore drilling contract under the delegated powers?
-- Type: policy_plus_data
-- Semantic audit 2026-10-20: Old SQL listed the top-50 drilling POs by value and never mapped them to an approval authority.
-- Semantic audit 2026-10-20: Now maps the BDP 2015 delegation ladder (Clauses 2.1, 3.3, 4.2, 6.1) onto drilling-category PO value
-- Semantic audit 2026-10-20: (revised value of drilling lines per PO, rupees -> crore), so the ₹50 cr case and actual usage are both visible.
-- Semantic audit 2026-10-20: Bands are upper-inclusive ("up to ₹X Crore"): a ₹50 cr drilling award falls in the Functional Director tier.
WITH po AS (
    SELECT po_number, SUM(revised_po_value_inr) / 1e7 AS po_value_cr
    FROM purchase_orders
    WHERE LOWER(service_contract_category) LIKE '%drilling%'
    GROUP BY po_number
),
tiers AS (
    SELECT * FROM UNNEST([
        STRUCT(1 AS tier, 'Up to ₹10 cr' AS value_band, 0.0 AS lo_cr, 10.0 AS hi_cr, 'Level 3: Asset/Basin Manager, ED heading work centre (open tender, Associate Finance concurrence)' AS approving_authority, 'BDP Clause 2.1' AS bdp_clause),
        STRUCT(2, '₹10-50 cr', 10.0, 50.0, 'Functional Director (drilling/well-service award) with Director (Finance) concurrence', 'BDP Clause 3.3'),
        STRUCT(3, '₹50-100 cr', 50.0, 100.0, 'Executive Committee (CMD + all Whole-Time Directors)', 'BDP Clause 4.2'),
        STRUCT(4, 'Above ₹100 cr', 100.0, 1e9, 'Board of Directors (EC appraisal first)', 'BDP Clause 6.1(a)')
    ])
)
SELECT
    t.tier,
    t.value_band,
    t.approving_authority,
    t.bdp_clause,
    COUNT(po.po_number) AS drilling_pos,
    ROUND(COALESCE(SUM(po.po_value_cr), 0), 1) AS drilling_po_value_cr,
    ROUND(MAX(po.po_value_cr), 2) AS largest_po_cr
FROM tiers t
LEFT JOIN po ON po.po_value_cr > t.lo_cr AND po.po_value_cr <= t.hi_cr
GROUP BY 1, 2, 3, 4
ORDER BY t.tier;
