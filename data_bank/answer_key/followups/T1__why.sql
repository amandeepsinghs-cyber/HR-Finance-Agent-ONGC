-- Answer Key Follow-up SQL: T1__why
-- Question: What are the primary operational factors (water cut >90%, low gas utilization, aging infrastructure) behind Field X's losses?
-- Type: chain
-- Semantic audit 2026-10-20: Old SQL listed average water cut for every field - it ignored Field X and the other named factors.
-- Semantic audit 2026-10-20: Now: Field X (the FY26 loss-maker from T1, chosen dynamically) vs mature-onshore peers and all fields on water cut, gas utilisation, uptime, downtime per well, field age, lifting cost and water-handling share of opex.

WITH x AS (
    SELECT field_id
    FROM field_pnl_annual
    WHERE fiscal_year = 'FY26' AND LOWER(line_type) = 'field' AND pbt_inr_cr < 0
    ORDER BY pbt_inr_cr
    LIMIT 1
),
ops AS (
    SELECT
        field_id,
        AVG(water_cut_pct) AS water_cut,
        AVG(gas_utilisation_pct) AS gas_util,
        AVG(operational_uptime_pct) AS uptime,
        SUM(well_downtime_hours) / NULLIF(SUM(active_producing_wells), 0) AS downtime_per_well_month
    FROM production_monthly
    WHERE fiscal_year = 'FY26'
    GROUP BY field_id
),
base AS (
    SELECT
        p.field_id, f.name, f.onshore_offshore, f.maturity, f.discovery_year,
        p.lifting_cost_per_boe_usd, p.water_handling_cost_inr_cr, p.total_opex_inr_cr, p.pbt_inr_cr, p.root_cause_loss_code,
        o.water_cut, o.gas_util, o.uptime, o.downtime_per_well_month
    FROM field_pnl_annual p
    JOIN dim_field f ON f.field_id = p.field_id
    JOIN ops o ON o.field_id = p.field_id
    WHERE p.fiscal_year = 'FY26' AND LOWER(p.line_type) = 'field'
),
grp AS (
    SELECT 1 AS ord, CONCAT('Field X: ', name) AS comparison_group, root_cause_loss_code AS root_cause, b.* EXCEPT (name, root_cause_loss_code)
    FROM base b WHERE field_id IN (SELECT field_id FROM x)
    UNION ALL
    SELECT 2, 'Mature onshore peers (excl. Field X)', NULL, b.* EXCEPT (name, root_cause_loss_code)
    FROM base b WHERE LOWER(maturity) = 'mature' AND LOWER(onshore_offshore) = 'onshore' AND field_id NOT IN (SELECT field_id FROM x)
    UNION ALL
    SELECT 3, 'All fields', NULL, b.* EXCEPT (name, root_cause_loss_code)
    FROM base b
)
SELECT
    comparison_group,
    COUNT(*) AS n_fields,
    ANY_VALUE(root_cause) AS root_cause,
    ROUND(AVG(water_cut), 1) AS avg_water_cut_pct,
    ROUND(AVG(gas_util), 1) AS avg_gas_utilisation_pct,
    ROUND(AVG(uptime), 2) AS avg_uptime_pct,
    ROUND(AVG(downtime_per_well_month), 1) AS downtime_hrs_per_well_month,
    ROUND(AVG(2026 - discovery_year), 1) AS avg_field_age_years,
    ROUND(AVG(lifting_cost_per_boe_usd), 2) AS avg_lifting_cost_usd_boe,
    ROUND(SUM(water_handling_cost_inr_cr) * 100.0 / NULLIF(SUM(total_opex_inr_cr), 0), 1) AS water_handling_pct_of_opex,
    ROUND(AVG(pbt_inr_cr), 2) AS avg_pbt_inr_cr
FROM grp
GROUP BY ord, comparison_group
ORDER BY ord;
