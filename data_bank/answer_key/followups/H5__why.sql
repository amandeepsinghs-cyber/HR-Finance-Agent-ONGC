-- Answer Key Follow-up SQL: H5__why
-- Question: What procedural bottlenecks (e.g. pending vigilance clearances, APAR grading appeals, seniority litigation) delayed convening the DPCs?
-- Type: data
-- Semantic audit 2026-10-20: SQL logic was sound; aligned the pending filter with H5 (status 'delayed'), added the coded
-- pending_reason, share and split by promotion step.
SELECT
    pending_reason,
    delay_bottleneck_reason,
    COUNT(*) AS case_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS share_pct,
    COUNTIF(from_grade_id = 'E4') AS e4_to_e5,
    COUNTIF(from_grade_id = 'E5') AS e5_to_e6,
    ROUND(AVG(delay_months), 1) AS avg_recorded_delay_months
FROM dpc_cases
WHERE LOWER(status) = 'delayed' AND delay_months >= 6
GROUP BY pending_reason, delay_bottleneck_reason
ORDER BY case_count DESC;
