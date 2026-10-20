-- Answer Key Follow-up SQL: H9__drill_down
-- Question: Break down pending cases by category (promotion dispute, transfer challenge, disciplinary action, pay anomaly) across High Courts and CAT.
-- Type: data
-- Semantic audit 2026-10-20: old SQL counted only 'pending' (excluded 'stayed') across 7 raw forum codes. Now: open (pending +
-- stayed) cases by category, pivoted across CAT (all benches), High Court, Supreme Court and the internal grievance cell.
SELECT
    case_category,
    COUNTIF(STARTS_WITH(LOWER(forum), 'cat')) AS cat_benches,
    COUNTIF(LOWER(forum) = 'high_court') AS high_court,
    COUNTIF(LOWER(forum) = 'supreme_court') AS supreme_court,
    COUNTIF(LOWER(forum) = 'internal_grievance_cell') AS internal_grievance_cell,
    COUNT(*) AS open_cases
FROM grievances_litigation
WHERE LOWER(status) IN ('pending', 'stayed')
GROUP BY case_category
ORDER BY open_cases DESC, case_category;
