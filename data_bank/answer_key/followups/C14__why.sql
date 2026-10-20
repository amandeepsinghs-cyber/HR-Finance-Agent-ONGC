-- Answer Key Follow-up SQL: C14__why
-- Question: What specific reservoir recovery mechanism or operating constraint is identified as the root cause of loss in each field?
-- Type: document
-- Semantic audit 2026-10-20: old SQL kept only rows WITH a root-cause code, so it answered for 1 of the 5
-- fields and silently dropped the others. Now: all five parent fields with the recorded root_cause_loss_code
-- ('Not recorded' when absent), the production-weighted FY26 water cut and the largest opex component per BOE,
-- so each field has an evidenced operating constraint even where no code is recorded.

WITH b AS (
    SELECT pnl.*, f.name AS field_name, f.maturity, f.hydrocarbon
    FROM field_pnl_annual pnl
    JOIN dim_field f ON pnl.field_id = f.field_id
    WHERE pnl.fiscal_year = 'FY26' AND LOWER(pnl.line_type) = 'field'
    ORDER BY pnl.pbt_inr_cr ASC
    LIMIT 5
),
wc AS (
    SELECT field_id, SUM(water_cut_pct * total_production_boe) / NULLIF(SUM(total_production_boe), 0) AS water_cut_pct
    FROM production_monthly WHERE fiscal_year = 'FY26' GROUP BY field_id
),
comp AS (
    SELECT b.field_id, c.name AS component, c.val
    FROM b,
    UNNEST([
        STRUCT('manpower' AS name, b.allocated_manpower_cost_inr_cr AS val),
        STRUCT('power_fuel', b.power_fuel_cost_inr_cr),
        STRUCT('workover_repairs', b.workover_repairs_cost_inr_cr),
        STRUCT('water_handling', b.water_handling_cost_inr_cr),
        STRUCT('logistics', b.logistics_osv_chopper_cost_inr_cr),
        STRUCT('chemicals', b.chemicals_consumables_cost_inr_cr),
        STRUCT('contractor', b.contractor_cost_inr_cr)
    ]) c
    QUALIFY ROW_NUMBER() OVER (PARTITION BY b.field_id ORDER BY c.val DESC) = 1
)
SELECT
    b.field_name,
    b.maturity,
    b.hydrocarbon,
    b.pbt_inr_cr,
    COALESCE(NULLIF(b.root_cause_loss_code, 'None'), 'Not recorded') AS root_cause_loss_code,
    ROUND(wc.water_cut_pct, 1) AS water_cut_pct,
    comp.component AS largest_opex_component,
    ROUND(comp.val * 100.0 / NULLIF(b.total_opex_inr_cr, 0), 1) AS largest_component_pct_of_opex,
    b.manpower_cost_per_boe_usd
FROM b
LEFT JOIN wc ON wc.field_id = b.field_id
LEFT JOIN comp ON comp.field_id = b.field_id
ORDER BY b.pbt_inr_cr ASC;
