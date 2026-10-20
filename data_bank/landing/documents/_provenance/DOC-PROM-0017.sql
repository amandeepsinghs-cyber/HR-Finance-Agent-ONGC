SELECT 
    pr.order_no,
    pr.BEGDA as effective_date,
    pr.PERNR as emp_id,
    e.name as emp_name,
    pr.from_grade_id,
    pr.PERSK as to_grade_id,
    pr.discipline_id,
    pr.wc_id,
    pr.dpc_id,
    pr.residency_years_completed,
    pr.apar_benchmark_met,
    pr.vigilance_cleared
FROM 'landing/sap/PA0000_promotions.csv' pr
JOIN 'landing/sap/PA0002_PA0001.csv' e ON pr.PERNR = e.PERNR
WHERE pr.order_no = 'ORD/PROM/2026/2753'
ORDER BY pr.PERNR;