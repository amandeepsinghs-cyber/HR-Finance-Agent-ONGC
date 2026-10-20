-- Answer Key Follow-up SQL: W3__drill_down
-- Question: What is the estimated budget required for Composite Transfer Allowance (CTA) and relocation grants for 200 officers?
-- Type: what_if
-- Semantic audit 2026-10-20: Old SQL listed Category-C vacancies (all cadres) and no budget at all.
-- Semantic audit 2026-10-20: Now: per-officer transfer cost components (CTA, transfer grant, baggage) = FY26 averages over rotation/hard-station postings in posting_history, x 200 officers.

WITH c AS (
    SELECT
        AVG(composite_transfer_grant_cta_inr) AS cta,
        AVG(transfer_grant_inr) AS tg,
        AVG(baggage_transport_cost_inr) AS bag,
        AVG(total_transfer_cost_inr) AS tot,
        COUNT(*) AS n
    FROM posting_history
    WHERE fiscal_year = 'FY26' AND LOWER(posting_type) IN ('rotation', 'hard_station')
)
SELECT
    item.component,
    ROUND(item.per_officer_inr, 0) AS per_officer_inr,
    ROUND(item.per_officer_inr * 200 / 1e7, 2) AS total_for_200_inr_cr,
    c.n AS fy26_transfers_sampled
FROM c
CROSS JOIN UNNEST([
    STRUCT(1 AS ord, 'Composite Transfer Grant (CTA)' AS component, c.cta AS per_officer_inr),
    STRUCT(2, 'Transfer grant', c.tg),
    STRUCT(3, 'Baggage transport', c.bag),
    STRUCT(4, 'Total', c.tot)
]) AS item
ORDER BY item.ord;
