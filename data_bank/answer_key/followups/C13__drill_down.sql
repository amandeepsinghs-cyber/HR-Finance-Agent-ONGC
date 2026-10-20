-- Answer Key Follow-up SQL: C13__drill_down
-- Question: Which field assets (e.g. Assam, Tripura, Karaikal) would gain the most production and maintenance engineering coverage?
-- Type: what_if
-- Semantic audit 2026-10-20: old SQL listed the 10 hard stations with the FEWEST technical officers (incl.
-- separated staff via "OR separation_date IS NULL", and non-asset basins/service units) - not a gain. Now, using
-- the parent scenario's allocation (200 officers pro-rata to each field asset's FY26 executive vacancy), the
-- production & maintenance (P&M) engineering coverage gain per asset: P&M = Production, Mechanical,
-- Electrical, Instrumentation executives; gain = LEAST(allocated officers, P&M vacancy); P&M fill % before and
-- after. Karaikal = Cauvery Asset; Assam = Assam Asset.

WITH vac AS (
    SELECT w.wc_id, w.short_name, w.city,
           SUM(sp.vacancy_count) AS exec_vacancy,
           SUM(IF(sp.discipline_id IN ('DISC-PRD', 'DISC-MEC', 'DISC-ELE', 'DISC-INS'), sp.sanctioned_strength, 0)) AS pm_sanctioned,
           SUM(IF(sp.discipline_id IN ('DISC-PRD', 'DISC-MEC', 'DISC-ELE', 'DISC-INS'), sp.in_position_strength, 0)) AS pm_in_position,
           SUM(IF(sp.discipline_id IN ('DISC-PRD', 'DISC-MEC', 'DISC-ELE', 'DISC-INS'), sp.vacancy_count, 0)) AS pm_vacancy
    FROM sanctioned_posts sp
    JOIN dim_work_centre w ON w.wc_id = sp.wc_id
    WHERE sp.fiscal_year = 'FY26' AND sp.grade_id LIKE 'E%' AND LOWER(w.type) = 'asset'
    GROUP BY 1, 2, 3
),
alloc AS (
    SELECT v.*,
           IF(v.exec_vacancy > 0,
              LEAST(v.exec_vacancy, CAST(ROUND(200 * v.exec_vacancy / SUM(v.exec_vacancy) OVER ()) AS INT64)), 0) AS allocated_officers
    FROM vac v
)
SELECT
    short_name AS field_asset,
    city,
    allocated_officers,
    pm_sanctioned,
    pm_in_position,
    pm_vacancy,
    LEAST(allocated_officers, pm_vacancy) AS pm_coverage_gain,
    ROUND(pm_in_position * 100.0 / NULLIF(pm_sanctioned, 0), 1) AS pm_fill_pct_before,
    ROUND((pm_in_position + LEAST(allocated_officers, pm_vacancy)) * 100.0 / NULLIF(pm_sanctioned, 0), 1) AS pm_fill_pct_after
FROM alloc
ORDER BY pm_coverage_gain DESC, pm_vacancy DESC, field_asset;
