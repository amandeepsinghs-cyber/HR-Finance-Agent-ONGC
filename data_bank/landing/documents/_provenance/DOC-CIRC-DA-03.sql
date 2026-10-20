SELECT 
    '2023-04' as effective_month,
    round(avg(LGART_1002 / NULLIF(LGART_1001, 0)) * 100, 1) as da_pct,
    count(distinct PERNR) as covered_employees,
    fiscal_year
FROM 'landing/sap/PY_CLUSTER_EXP.csv'
WHERE FPPER = '2023-04'
GROUP BY fiscal_year;