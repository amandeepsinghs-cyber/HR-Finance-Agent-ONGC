SELECT 
    p.order_no,
    p.BEGDA as effective_date,
    p.PERNR as emp_id,
    e.name as emp_name,
    p.designation,
    p.PERSK as grade_id,
    p.discipline_id,
    p.WERKS as to_wc_id,
    p.MASSN as action_type,
    p.composite_transfer_grant_cta_inr,
    p.baggage_transport_cost_inr,
    p.total_transfer_cost_inr
FROM 'landing/sap/PA0001.csv' p
JOIN 'landing/sap/PA0002_PA0001.csv' e ON p.PERNR = e.PERNR
WHERE p.order_no = 'ORD/HR/2026/8168'
ORDER BY p.PERNR;