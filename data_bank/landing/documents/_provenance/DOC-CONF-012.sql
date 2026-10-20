SELECT e.PERNR as emp_id, e.name as emp_name, e.PERSK as grade_id, 
       e.discipline_id, e.WERKS as current_wc_id,
       e.retirement_date, e.has_hard_station_tenure, e.has_offshore_tenure
FROM 'landing/sap/PA0002_PA0001.csv' e
WHERE e.STAT2 = 'Active' AND e.PERSK IN ('E7', 'E8', 'E9')
  AND e.retirement_date BETWEEN '2026-04-01' AND '2029-03-31'
ORDER BY e.retirement_date ASC
LIMIT 15;