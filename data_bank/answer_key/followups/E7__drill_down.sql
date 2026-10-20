-- Answer Key Follow-up SQL: E7__drill_down
-- Question: What was the breakdown between standalone profit after tax (PAT) and consolidated group profit for FY25/FY26?
-- Type: data
-- Semantic audit 2026-10-20: Added subsidiaries' contribution (consolidated - standalone); removed dead '2025'/'2026' alternates.

SELECT
    fiscal_year,
    pat_inr_cr AS standalone_pat_inr_cr,
    consolidated_pat_inr_cr,
    consolidated_pat_inr_cr - pat_inr_cr AS group_entities_contribution_inr_cr
FROM corporate_financials
WHERE fiscal_year IN ('FY25', 'FY26')
ORDER BY fiscal_year;
