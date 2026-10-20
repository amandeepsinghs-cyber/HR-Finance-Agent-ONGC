-- Provenance for Hard Station Deficit Analysis
-- Note: Reads cleaned workbook from landing/excel/_clean/manpower_plan.xlsx (reconstructed from messy landing source)
-- JRTP Clause 1.2 (E0-E9 executives only), Clause 2.1(c) (Category C classification)
SELECT wc_id, discipline_id, grade_band, 
       sum(sanctioned_strength) as sanctioned_strength,
       sum(in_position_strength) as in_position_strength,
       sum(vacancy_count) as total_vacancies
FROM 'landing/excel/_clean/manpower_plan.xlsx'
WHERE fiscal_year = 'FY26' 
  AND wc_id IN ('WC-ASM', 'WC-TRI', 'WC-JOR', 'WC-BAS', 'WC-NEH')
  AND grade_band IN ('E0_E2', 'E3_E5', 'E6_E9')
GROUP BY wc_id, discipline_id, grade_band
HAVING sum(vacancy_count) > 0
ORDER BY total_vacancies DESC
LIMIT 12;