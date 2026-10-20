-- Answer Key Follow-up SQL: X6__compare_or_so_what
-- Question: How does our annual green energy capex compare with the milestone spending targets outlined in the Net Zero 2038 roadmap?
-- Type: data
-- Semantic audit 2026-10-20: Annual green capex by FY (not SUM of the stored cumulative column across technologies) against the
-- only roadmap signal in the data, the milestone flag. GAP: no Net Zero 2038 spend milestones/targets exist in silver,
-- gold or the document corpus, so the 'vs target' comparison cannot be quantified.
SELECT
    fiscal_year,
    ROUND(SUM(IF(LOWER(technology_type) = 'solar pv', annual_capex_inr_cr, 0)), 1) AS solar_capex_cr,
    ROUND(SUM(IF(LOWER(technology_type) LIKE 'wind%', annual_capex_inr_cr, 0)), 1) AS wind_capex_cr,
    ROUND(SUM(IF(LOWER(technology_type) = 'green hydrogen', annual_capex_inr_cr, 0)), 1) AS green_hydrogen_capex_cr,
    ROUND(SUM(annual_capex_inr_cr), 1) AS total_green_capex_cr,
    COUNTIF(annual_capex_inr_cr > 0) AS projects_spending,
    COUNTIF(net_zero_2038_roadmap_milestone_met) AS projects_flagged_milestone_met,
    COUNT(*) AS projects
FROM energy_transition
GROUP BY fiscal_year
ORDER BY fiscal_year;
