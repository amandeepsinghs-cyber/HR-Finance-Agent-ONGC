-- Answer Key SQL: E2
-- Question: When am I due for transfer, and what is the rotation policy for my grade?
-- Type: policy_plus_data
-- Semantic audit 2026-10-20: Old SQL listed the posting only. Now applies JRTP 3.0 (rotation window 36-60 months) and 9.1 (AGT effective by 1 July) to the current posting (is_current_posting).

SELECT
    p.emp_id,
    p.wc_id,
    w.name AS work_centre,
    w.cluster_id,
    p.grade_id,
    p.from_date AS station_since,
    DATE_DIFF(DATE '2026-10-19', p.from_date, MONTH) AS tenure_months,
    DATE_ADD(p.from_date, INTERVAL 36 MONTH) AS rotation_window_opens,
    DATE_ADD(p.from_date, INTERVAL 60 MONTH) AS rotation_window_closes,
    CASE
        WHEN DATE_DIFF(DATE '2026-10-19', p.from_date, MONTH) > 60 THEN 'beyond 5-year window - due in next AGT'
        WHEN DATE_DIFF(DATE '2026-10-19', p.from_date, MONTH) >= 36 THEN 'within 3-5 year window - eligible'
        ELSE 'not yet eligible (under 3 years)'
    END AS rotation_status,
    DATE '2027-07-01' AS next_agt_effective_by,
    p.exemption_tag
FROM posting_history p
JOIN dim_work_centre w ON p.wc_id = w.wc_id
WHERE p.emp_id = 'EMP-102451'
  AND p.is_current_posting = TRUE;
