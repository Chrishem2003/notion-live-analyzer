import pytest
from career_studio.engine import calculate_job_match

def test_calculate_job_match():
    user = {"skills": ["python", "sql"], "seniority": "mid", "industry": "technology"}
    job = {"required_skills": ["python", "sql"], "preferred_skills": ["tableau"], "seniority": "mid", "industry": "technology"}
    result = calculate_job_match(user, job)
    assert result["overall_match"] > 80.0
    assert len(result["critical_gaps"]) == 0
