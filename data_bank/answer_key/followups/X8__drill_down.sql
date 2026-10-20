-- Answer Key Follow-up SQL: X8__drill_down
-- Question: Which operating departments (Procurement/MM, Finance, HR) have the largest volume of outstanding CAG audit paragraphs?
-- Type: data
-- Semantic audit 2026-10-20: Logic unchanged (open paras by department) with LOWER() status hygiene and average age added.
SELECT
    operating_department,
    COUNT(cag_para_id) AS open_paras,
    ROUND(SUM(financial_implication_inr_cr), 2) AS financial_implication_cr,
    ROUND(AVG(DATE_DIFF(DATE '2026-10-19', notification_date, DAY)) / 365.25, 1) AS avg_age_years,
    COUNTIF(DATE_DIFF(DATE '2026-10-19', notification_date, DAY) > 3 * 365) AS paras_over_3_years
FROM cag_paras
WHERE LOWER(current_status) != 'closed'
GROUP BY operating_department
ORDER BY open_paras DESC, financial_implication_cr DESC;
