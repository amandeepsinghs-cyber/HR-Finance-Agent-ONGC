SELECT stage, inquiry_status, count(*) as case_count, 
       round(avg(age_months), 1) as avg_age_months
FROM 'landing/sap/vigilance_cases_confidential.csv'
GROUP BY stage, inquiry_status
ORDER BY case_count DESC;