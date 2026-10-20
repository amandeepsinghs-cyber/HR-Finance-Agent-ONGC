SELECT vigilance_case_id, emp_id, grade_id, discipline_id, wc_id, 
       complaint_date, stage, inquiry_status, vigilance_clearance_status, age_months
FROM 'landing/sap/vigilance_cases_confidential.csv'
WHERE age_months > 12 OR stage IN ('regular_departmental_action', 'prosecution_sanction')
ORDER BY age_months DESC
LIMIT 12;