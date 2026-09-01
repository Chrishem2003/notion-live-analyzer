"""Final Advancement 14 — Unified Career OS.

A single deterministic orchestration layer over the Career Studio modules.
It aggregates user-provided profile, applications, jobs, offers and goals
without inventing missing facts or claiming predictive certainty.
"""
from .analytics import dashboard as analytics_dashboard
from .opportunity import rank_jobs, market_summary as opportunity_summary
from .interview_academy import readiness
from .negotiation import compare_offers, market_summary as salary_summary
from .career_strategy import command_center

def build_career_os(profile=None, applications=None, jobs=None, offers=None,
                    interview_answers=None, job_text=""):
    profile=dict(profile or {})
    applications=applications if applications is not None else profile.get("applications",[])
    jobs=jobs if jobs is not None else profile.get("job_opportunities",[])
    offers=offers if offers is not None else profile.get("offers",[])
    return {
        "profile": {
            "name": profile.get("name",""),
            "target_role": profile.get("target_role",""),
        },
        "career_strategy": command_center(profile),
        "application_analytics": analytics_dashboard(applications),
        "opportunities": {
            "top_matches": rank_jobs(jobs)[:10],
            "summary": opportunity_summary(jobs),
        },
        "interview": readiness(profile, interview_answers or {}, job_text),
        "offers": {
            "ranked": compare_offers(offers),
            "salary_summary": salary_summary(profile.get("salary_records",[])),
        },
        "data_integrity": {
            "jobs_are_user_or_connector_supplied": True,
            "application_outcomes_are_recorded_only": True,
            "salary_market_data_is_user_supplied": True,
            "employment_outcomes_are_not_predicted": True,
        },
    }

def executive_snapshot(data):
    f=data["application_analytics"]["funnel"]
    return {
        "target_role":data["profile"]["target_role"],
        "skill_coverage_pct":data["career_strategy"]["coverage_pct"],
        "skill_gaps":data["career_strategy"]["skill_gaps"],
        "applications":f["applied"],
        "interview_rate":f["interview_rate"],
        "offer_rate":f["offer_rate"],
        "top_job_matches":len(data["opportunities"]["top_matches"]),
        "interview_readiness":data["interview"]["readiness"],
        "offers_tracked":len(data["offers"]["ranked"]),
    }
