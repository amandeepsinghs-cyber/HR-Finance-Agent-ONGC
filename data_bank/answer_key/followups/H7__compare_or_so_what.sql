-- Answer Key Follow-up SQL: H7__compare_or_so_what
-- Question: How does women's representation in technical disciplines compare with corporate and support functions (HR, F&A, Medical)?
-- Type: data
-- Semantic audit 2026-10-20: old SQL returned each function's share OF ALL WOMEN (sums to 100%), not women's representation
-- within the function. Now: women as % of active employees in technical vs finance, HR and support functions, plus the
-- named support disciplines (Medical Services) and company total.
WITH act AS (
    SELECT e.gender, d.function, d.name
    FROM employee_master e
    JOIN dim_discipline d ON e.discipline_id = d.discipline_id
    WHERE LOWER(e.employment_status) = 'active'
)
SELECT CONCAT('Function: ', function) AS segment,
       COUNTIF(LOWER(gender) = 'female') AS women, COUNT(*) AS employees,
       ROUND(COUNTIF(LOWER(gender) = 'female') * 100.0 / COUNT(*), 1) AS women_pct
FROM act GROUP BY function
UNION ALL
SELECT CONCAT('Discipline: ', name), COUNTIF(LOWER(gender) = 'female'), COUNT(*),
       ROUND(COUNTIF(LOWER(gender) = 'female') * 100.0 / COUNT(*), 1)
FROM act WHERE name = 'Medical Services' GROUP BY name
UNION ALL
SELECT 'Company', COUNTIF(LOWER(gender) = 'female'), COUNT(*), ROUND(COUNTIF(LOWER(gender) = 'female') * 100.0 / COUNT(*), 1)
FROM act
ORDER BY women_pct DESC;
