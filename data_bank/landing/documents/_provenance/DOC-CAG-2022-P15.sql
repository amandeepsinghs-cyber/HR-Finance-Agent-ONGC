SELECT 
    cag_para_id,
    report_number,
    cag_report_year,
    operating_department,
    wc_id,
    para_subject,
    financial_implication_inr_cr,
    notification_date,
    age_in_years,
    is_aged_over_3_years,
    current_status,
    bottleneck_reason
FROM 'landing/excel/cag_paras_register.xlsx'
WHERE cag_para_id = 'CAG-2022-P15';