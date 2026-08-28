def generate_export_text(profile_data: dict) -> str:
    return \"\"\"
==================================================
{profile_data.get('name', 'Professional Candidate').upper()}
==================================================
Industry: {profile_data.get('industry', 'Technology')} | Seniority: {profile_data.get('seniority', 'Mid')}

EXECUTIVE SUMMARY:
{profile_data.get('summary', 'Results-driven professional specializing in high-impact execution.')}

CORE COMPETENCIES & SKILLS:
{', '.join(profile_data.get('skills', []))}
==================================================
\"\"\"
