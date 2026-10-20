-- Answer Key Follow-up SQL: H3__why
-- Question: Why is there a persistent vacancy gap in North-East and deepwater asset operational roles?
-- Type: data
-- Semantic audit 2026-10-20: old SQL only split NE vacancies by hard_station_cat (one category 'C'), ignored deepwater and
-- gave no causal evidence. Now: FY26 vacancy rate for North-East, Eastern Offshore (KG deepwater), Western offshore and the
-- rest of the company, with FY26 separations and FY26 transfer-ins (rotation/hard-station postings) per 100 sanctioned posts.
WITH region AS (
    SELECT wc_id,
        CASE WHEN LOWER(sector) = 'ne' THEN '1. North-East'
             WHEN wc_id = 'WC-EAS' THEN '2. Eastern Offshore (KG deepwater)'
             WHEN LOWER(onshore_offshore) = 'offshore' THEN '3. Western offshore'
             ELSE '4. Rest of company' END AS region
    FROM dim_work_centre
),
posts AS (
    SELECT r.region, SUM(sp.sanctioned_strength) AS sanctioned, SUM(sp.in_position_strength) AS in_position,
           SUM(sp.vacancy_count) AS vacancies
    FROM sanctioned_posts sp JOIN region r ON r.wc_id = sp.wc_id
    WHERE sp.fiscal_year = 'FY26'
    GROUP BY r.region
),
seps AS (
    SELECT r.region, COUNT(*) AS separations_fy26,
           COUNTIF(LOWER(s.separation_type) IN ('resignation', 'vrs')) AS voluntary_exits_fy26
    FROM separations s JOIN region r ON r.wc_id = s.last_wc_id
    WHERE s.fiscal_year = 'FY26'
    GROUP BY r.region
),
ins AS (
    SELECT r.region, COUNT(*) AS transfer_ins_fy26
    FROM posting_history p JOIN region r ON r.wc_id = p.wc_id
    WHERE p.fiscal_year = 'FY26' AND LOWER(p.posting_type) IN ('rotation', 'hard_station')
    GROUP BY r.region
)
SELECT
    p.region,
    p.sanctioned, p.in_position, p.vacancies,
    ROUND(p.vacancies * 100.0 / p.sanctioned, 1) AS vacancy_rate_pct,
    IFNULL(s.separations_fy26, 0) AS separations_fy26,
    IFNULL(s.voluntary_exits_fy26, 0) AS voluntary_exits_fy26,
    IFNULL(i.transfer_ins_fy26, 0) AS transfer_ins_fy26,
    ROUND(IFNULL(s.separations_fy26, 0) * 100.0 / p.sanctioned, 1) AS separations_per_100_posts,
    ROUND(IFNULL(i.transfer_ins_fy26, 0) * 100.0 / p.sanctioned, 1) AS transfer_ins_per_100_posts
FROM posts p
LEFT JOIN seps s ON s.region = p.region
LEFT JOIN ins i ON i.region = p.region
ORDER BY p.region;
