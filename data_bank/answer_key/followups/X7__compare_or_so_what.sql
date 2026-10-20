-- Answer Key Follow-up SQL: X7__compare_or_so_what
-- Question: How does the vacancy percentage in North-East work centres compare with ONGC's national average vacancy level?
-- Type: document
-- Semantic audit 2026-10-20: NE vs rest of India vs national vacancy rate (old SQL grouped by hard-station category A/B/C,
-- which is not the NE comparison asked).
WITH base AS (
    SELECT IF(wc.sector = 'NE', 'North-East (Assam + Tripura)', 'Rest of India') AS region_name,
        sp.sanctioned_strength, sp.in_position_strength, sp.vacancy_count
    FROM sanctioned_posts sp
    JOIN dim_work_centre wc ON sp.wc_id = wc.wc_id
    WHERE sp.fiscal_year = 'FY26'
)
SELECT
    COALESCE(region_name, 'ONGC national') AS region,
    SUM(sanctioned_strength) AS sanctioned,
    SUM(in_position_strength) AS in_position,
    SUM(vacancy_count) AS vacancies,
    ROUND(SUM(vacancy_count) * 100 / SUM(sanctioned_strength), 2) AS vacancy_rate_pct
FROM base
GROUP BY ROLLUP (region_name)
ORDER BY vacancy_rate_pct;
