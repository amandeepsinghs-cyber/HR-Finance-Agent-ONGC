-- Answer Key Follow-up SQL: P2__drill_down
-- Question: Do Delhi and Dehradun form separate clusters, and how are Mumbai, Uran, and Panvel treated?
-- Type: policy
-- Semantic audit 2026-10-20: old query returned only the JRTP 5.0 metadata header. Now lists every work centre
-- in Delhi, Dehradun, Mumbai, Uran and Panvel with its JRTP cluster (dim_work_centre).

SELECT
    city,
    wc_id,
    short_name,
    cluster_id,
    cluster_name,
    hard_station_cat
FROM dim_work_centre
WHERE LOWER(city) IN ('new delhi', 'dehradun', 'mumbai', 'uran', 'panvel')
ORDER BY cluster_id, city, wc_id;
