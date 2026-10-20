SELECT dpc_id, from_grade_id, to_grade_id, discipline_id, status,
       pending_reason, delay_bottleneck_reason, delay_months
FROM 'landing/excel/DPC_tracker.xlsx'
WHERE status = 'pending'
ORDER BY delay_months DESC
LIMIT 12;