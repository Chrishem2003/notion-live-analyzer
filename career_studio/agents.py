
"""Advancement 7: transparent multi-agent career system.

Agents are deterministic by default. Optional real LLM calls are delegated to
career_studio.ai.ask only when the user has configured a real provider.
No agent fabricates credentials, employment, dates, metrics, or qualifications.
"""
from dataclasses import dataclass
from .intelligence import match_job, career_health, build_evidence_graph
from .ai import configured, ask

@dataclass
class AgentResult:
    agent: str
    status: str
    summary: str
    findings: list
    next_actions: list
    ai_enhanced: bool=False

def cv_architect(profile):
    h=career_health(profile)
    findings=[]
    if not profile.get("headline"): findings.append("Headline is missing.")
    if not profile.get("summary"): findings.append("Professional summary is missing.")
    if len(profile.get("skills",[]))<5: findings.append("Skill inventory is thin.")
    if not h["metrics"]: findings.append("Add measurable outcomes to career evidence.")
    return AgentResult("CV Architect","ready","CV structure and evidence assessment completed.",
                       findings,["Strengthen the highest-impact evidence.","Run a job-specific match before tailoring."])

def job_analyst(profile,job_text):
    r=match_job(profile,job_text)
    return AgentResult("Job Analyst","ready",f"Overall transparent match: {r['overall']}%.",
                       [f"Keyword coverage: {r['keyword_score']}%.",
                        f"Must-have coverage: {r['must_have_score']}%.",
                        f"Evidence strength: {r['evidence_score']}%."],
                       [("Address gaps: "+", ".join(r["must_have_missing"])) if r["must_have_missing"] else "No explicit must-have gaps detected.",
                        "Use only evidence-supported claims in the tailored CV."])

def interview_strategist(profile,job_text=""):
    r=match_job(profile,job_text) if job_text else None
    focus=(r["matched"][:10] if r else profile.get("skills",[])[:10])
    return AgentResult("Interview Strategist","ready","Interview preparation focus generated from profile evidence.",
                       ["Prioritize examples involving: "+", ".join(focus) if focus else "your strongest verified achievements."],
                       ["Prepare STAR stories using real situations, actions and outcomes.",
                        "Do not invent examples or metrics."])

def career_strategist(profile):
    h=career_health(profile)
    return AgentResult("Career Strategist","ready",f"Career health: {h['score']}/100.",
                       h["recommendations"] or ["Maintain a quantified evidence bank."],
                       ["Choose a target role family.","Build evidence around the skills required by that role."])

def application_agent(profile,job_text):
    r=match_job(profile,job_text)
    return AgentResult("Application Agent","ready","Application preparation plan generated.",
                       ["Match "+str(r["overall"])+"%","Potential gaps: "+(", ".join(r["missing"][:10]) or "none obvious")],
                       ["Tailor the CV using matched evidence.","Review every generated claim before submission."])

def run_career_council(profile,job_text=""):
    results=[cv_architect(profile),career_strategist(profile)]
    if job_text:
        results += [job_analyst(profile,job_text),interview_strategist(profile,job_text),application_agent(profile,job_text)]
    return results

def ai_enhance(agent_result,profile,user_request):
    if not configured():
        return agent_result
    prompt=("You are enhancing a career-planning result. Never invent qualifications, "
            "employment, dates, metrics or skills. Only recommend edits supported by the supplied data.\n"
            f"Agent: {agent_result.agent}\nProfile: {profile}\nRequest: {user_request}\n"
            f"Current findings: {agent_result.findings}")
    text=ask("Evidence-first career assistant. Never fabricate.",prompt)
    return AgentResult(agent_result.agent,"ai-enhanced",text,agent_result.findings,agent_result.next_actions,True)
