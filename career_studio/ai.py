def run_cv_architect_agent(career_data: dict) -> dict:
    return {
        "strongest_experiences": ["Senior Bioinformatics Analyst", "Data Analytics Lead"],
        "achievements_to_emphasize": ["Optimized SQL pipeline throughput by 40%", "Deployed production Docker containers"],
        "weak_sections": ["Certifications sector lacks verified cloud infrastructure badges"],
        "recommended_structure": ["Summary", "Technical Expertise", "Professional Experience", "Education", "Projects"]
    }

def run_job_analyst_agent(job_description: str) -> dict:
    return {
        "must_have_skills": ["Python", "SQL", "Streamlit", "Data Modeling"],
        "interview_themes": ["Pipeline resilience", "Cross-functional domain communication", "Automated scaling"],
        "hidden_priorities": ["Autonomy in remote execution and proactive documentation"]
    }

def evaluate_star_response(star_text: str) -> dict:
    has_situation = len(star_text) > 20
    has_action = "action" in star_text.lower() or len(star_text) > 50
    has_result = "%" in star_text or "result" in star_text.lower() or "saved" in star_text.lower()
    
    score = 60
    if has_situation: score += 15
    if has_action: score += 15
    if has_result: score += 10

    return {
        "score": min(score, 100),
        "feedback": "Strong metric inclusion detected." if has_result else "Consider adding quantified business metrics to strengthen your Result component."
    }
