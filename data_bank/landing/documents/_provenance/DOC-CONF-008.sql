SELECT dpc_id, from_grade_id, to_grade_id, discipline_id, status,
       eligible_candidates_count, recommended_candidates_count,
       held_date
FROM 'landing/excel/DPC_tracker.xlsx'
WHERE fiscal_year = 'FY26' AND status = 'completed'
ORDER BY dpc_id
LIMIT 12;