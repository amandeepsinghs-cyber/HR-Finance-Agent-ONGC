-- Answer Key Follow-up SQL: F6__compare_or_so_what
-- Question: How does our Days Sales Outstanding (DSO) compare with historical averages and treasury working capital targets?
-- Type: data
-- Semantic audit 2026-10-20: joined ~12,000 invoice rows to corporate_financials on fiscal_year, so revenue was summed
-- Semantic audit 2026-10-20: once per invoice (DSO 0.003 days). Now per FY: billed revenue and year-end outstanding from
-- Semantic audit 2026-10-20: receivables (aggregated first), DSO = outstanding / billed x 365, and amount-weighted actual
-- Semantic audit 2026-10-20: collection days (invoice -> payment) as the historical average. FY27 is excluded (invoices are
-- Semantic audit 2026-10-20: dated past 2026-10-19). GAP: no treasury DSO / working-capital target exists in the data, and
-- Semantic audit 2026-10-20: FY22-FY25 year-end balances were not retained (all paid), so DSO is NULL for those years.

SELECT
    fiscal_year,
    ROUND(SUM(billed_amount_inr_cr), 0) AS billed_cr,
    ROUND(SUM(outstanding_amount_inr_cr), 1) AS year_end_outstanding_cr,
    IF(SUM(outstanding_amount_inr_cr) > 0, ROUND(SUM(outstanding_amount_inr_cr) * 365 / SUM(billed_amount_inr_cr), 1), NULL) AS dso_days,
    ROUND(SUM(IF(payment_date IS NOT NULL, DATE_DIFF(payment_date, invoice_date, DAY) * paid_amount_inr_cr, 0))
          / NULLIF(SUM(IF(payment_date IS NOT NULL, paid_amount_inr_cr, 0)), 0), 1) AS avg_collection_days,
    ROUND(AVG(DATE_DIFF(due_date, invoice_date, DAY)), 0) AS credit_terms_days
FROM receivables
WHERE fiscal_year IN ('FY22', 'FY23', 'FY24', 'FY25', 'FY26')
GROUP BY fiscal_year
ORDER BY fiscal_year;
