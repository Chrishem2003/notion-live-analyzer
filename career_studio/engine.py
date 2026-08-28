def calculate_job_match(user_profile: dict, job_profile: dict) -> dict:
    \"\"\"
    Computes multi-factor job match scoring and gap analysis without faking qualifications.
    \"\"\"
    user_skills = set(s.lower() for s in user_profile.get("skills", []))
    req_skills = set(s.lower() for s in job_profile.get("required_skills", []))
    pref_skills = set(s.lower() for s in job_profile.get("preferred_skills", []))

    matched_req = user_skills.intersection(req_skills)
    matched_pref = user_skills.intersection(pref_skills)
    
    req_score = (len(matched_req) / len(req_skills)) if req_skills else 1.0
    pref_score = (len(matched_pref) / len(pref_skills)) if pref_skills else 1.0
    skills_match_pct = round((req_score * 0.75 + pref_score * 0.25) * 100, 1)

    user_seniority = user_profile.get("seniority", "Mid").lower()
    target_seniority = job_profile.get("seniority", "Mid").lower()
    seniority_match_pct = 100.0 if user_seniority == target_seniority else 80.0

    user_industry = user_profile.get("industry", "").lower()
    target_industry = job_profile.get("industry", "").lower()
    industry_match_pct = 100.0 if user_industry == target_industry else 70.0

    missing_required = list(req_skills - user_skills)

    overall_score = round(
        (skills_match_pct * 0.40) +
        (user_profile.get("experience_relevance", 80) * 0.25) +
        (industry_match_pct * 0.15) +
        (seniority_match_pct * 0.20), 1
    )

    return {
        "overall_match": overall_score,
        "skills_match": skills_match_pct,
        "experience_match": user_profile.get("experience_relevance", 80),
        "industry_match": industry_match_pct,
        "seniority_match": seniority_match_pct,
        "keyword_coverage": skills_match_pct,
        "evidence_strength": user_profile.get("evidence_strength", 85),
        "critical_gaps": missing_required
    }
