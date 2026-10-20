SELECT 
    pq_id,
    house,
    session_year,
    question_number,
    question_date,
    question_type,
    ministry,
    mp_name,
    subject_theme,
    brief_text,
    reply_summary,
    sanctioned_strength_reported,
    in_position_strength_reported,
    vacancies_reported,
    reserved_vacancies_sc,
    reserved_vacancies_st,
    reserved_vacancies_obc,
    reserved_vacancies_ews
FROM 'landing/governance/parliament_questions_index.csv'
WHERE pq_id = 'PQ-LS-2024-0101';