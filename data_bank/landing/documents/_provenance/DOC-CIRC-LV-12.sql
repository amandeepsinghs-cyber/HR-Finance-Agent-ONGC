SELECT 
    fiscal_year,
    SUBTY as leave_type,
    transaction_type,
    count(distinct PERNR) as employee_count,
    round(avg(ABWTG), 2) as avg_days_taken,
    round(avg(ANZHL), 2) as avg_leave_quota,
    round(avg(encashable_balance_days), 2) as avg_encashable_days
FROM 'landing/sap/PA2001_PA2006.csv'
WHERE fiscal_year = 'FY25' AND SUBTY = 'Earned_Leave_EL'
GROUP BY fiscal_year, SUBTY, transaction_type
ORDER BY transaction_type;