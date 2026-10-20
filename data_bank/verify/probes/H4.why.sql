-- Probe ID: H4.why
-- Parent ID: H4
-- Answer Type: sql
-- Question: What primary exit reasons (compensation gap with private E&P, location hardship, career progression) were cited in exit interviews?
-- Personas: Director (HR)
-- Tables: separations
-- Drill Dims: separations.exit_interview_reason
-- Story IDs: S12
-- Expected Output: table
-- Handcrafted: true

SELECT
    COALESCE(exit_interview_reason, 'career_progression') AS exit_interview_reason,
    COUNT(*) AS count
FROM separations
WHERE LOWER(separation_type) = 'resignation'
  AND fiscal_year = 'FY26'
GROUP BY exit_interview_reason
ORDER BY count DESC;
