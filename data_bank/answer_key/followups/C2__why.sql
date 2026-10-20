-- Answer Key Follow-up SQL: C2__why
-- Question: Why have previous annual transfer cycles left North-East work centres persistently below sanctioned executive strength?
-- Type: data
-- Semantic audit 2026-10-20: previous SQL counted every posting row ever made in NE grouped by exemption_tag
-- (which holds the literal string 'None' for >99.9% of rows) - 19,478 "exempt" postings, meaningless. Now the
-- transfer-cycle flow for the last five full cycles (FY22-FY26): executives posted INTO a North-East work
-- centre from outside NE vs posted OUT of NE to another sector (posting_history ordered per employee), the
-- net flow, and the NE executive strength gap vs FY26 sanctioned posts (only FY26 sanctions exist, so the
-- "persistently" part can be tested only through flows, not through a sanctioned-strength history).

WITH p AS (
    SELECT ph.emp_id, ph.fiscal_year, ph.grade_id, ph.posting_type, w.sector,
           LAG(w.sector) OVER (PARTITION BY ph.emp_id ORDER BY ph.from_date, ph.posting_id) AS prev_sector
    FROM posting_history ph
    JOIN dim_work_centre w ON ph.wc_id = w.wc_id
),
flows AS (
    SELECT fiscal_year,
           COUNTIF(LOWER(sector) = 'ne' AND prev_sector IS NOT NULL AND LOWER(prev_sector) != 'ne') AS executives_posted_into_ne,
           COUNTIF(LOWER(sector) != 'ne' AND LOWER(prev_sector) = 'ne') AS executives_posted_out_of_ne
    FROM p
    WHERE grade_id LIKE 'E%'
      AND fiscal_year IN ('FY22', 'FY23', 'FY24', 'FY25', 'FY26')
    GROUP BY fiscal_year
),
gap AS (
    SELECT SUM(sp.sanctioned_strength) AS ne_exec_sanctioned_fy26,
           SUM(sp.in_position_strength) AS ne_exec_in_position_fy26,
           SUM(sp.vacancy_count) AS ne_exec_vacancy_fy26
    FROM sanctioned_posts sp
    JOIN dim_work_centre w ON sp.wc_id = w.wc_id
    WHERE sp.fiscal_year = 'FY26' AND sp.grade_id LIKE 'E%' AND LOWER(w.sector) = 'ne'
)
SELECT
    f.fiscal_year,
    f.executives_posted_into_ne,
    f.executives_posted_out_of_ne,
    f.executives_posted_into_ne - f.executives_posted_out_of_ne AS net_flow_into_ne,
    SUM(f.executives_posted_into_ne - f.executives_posted_out_of_ne) OVER (ORDER BY f.fiscal_year) AS cumulative_net_flow,
    g.ne_exec_sanctioned_fy26,
    g.ne_exec_in_position_fy26,
    g.ne_exec_vacancy_fy26
FROM flows f
CROSS JOIN gap g
ORDER BY f.fiscal_year;
