-- Answer Key SQL: P9
-- Question: How do I file a POSH complaint, and who is on the committee at my station?
-- Type: policy
-- Semantic audit 2026-10-20: added committee size, women share, contact e-mail (the filing channel) and WC name;
-- old query showed only presiding officer + external member and the MD rendered empty citations.

SELECT
    i.wc_id,
    w.short_name AS work_centre,
    i.committee_id,
    i.presiding_officer_name,
    i.presiding_officer_gender,
    i.external_member_name,
    i.external_member_ngo,
    i.internal_members_count,
    i.women_members_pct,
    i.contact_email,
    i.expiry_date
FROM icc_committees i
LEFT JOIN dim_work_centre w USING (wc_id)
WHERE LOWER(i.status) = 'active'
ORDER BY i.wc_id;
