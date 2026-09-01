"""Advancement 13 — Personal Career Command Center & Strategy Engine.

Deterministic planning from user-owned career goals, evidence, applications,
skills and milestones. It does not predict employment outcomes.
"""
from datetime import date, timedelta

def _clean_list(v):
    return [str(x).strip() for x in (v or []) if str(x).strip()]

def gap_analysis(profile):
    current=set(_clean_list(profile.get("skills")))
    target=set(_clean_list(profile.get("target_skills")))
    missing=sorted(target-current,key=str.lower)
    strengths=sorted(current&target,key=str.lower)
    return {"current_skills":sorted(current,key=str.lower),"target_skills":sorted(target,key=str.lower),
            "strengths":strengths,"skill_gaps":missing,"coverage_pct":round(100*len(strengths)/max(1,len(target)),1)}

def priority_actions(profile):
    g=gap_analysis(profile); actions=[]
    for skill in g["skill_gaps"][:10]:
        actions.append({"priority":"high","action":f"Build verified evidence for {skill}.","category":"skill"})
    if not profile.get("summary"): actions.append({"priority":"high","action":"Create a concise evidence-based professional summary.","category":"profile"})
    if not profile.get("applications"): actions.append({"priority":"medium","action":"Start tracking applications and outcomes.","category":"execution"})
    if not actions: actions.append({"priority":"medium","action":"Review and strengthen the highest-impact career evidence.","category":"evidence"})
    return actions

def milestone_plan(profile, days=90):
    days=max(7,int(days)); start=date.today()
    actions=priority_actions(profile)
    step=max(1,days//max(1,len(actions)))
    return [{"day":min(days,step*(i+1)),"due":str(start+timedelta(days=min(days,step*(i+1)))),
             "action":a["action"],"category":a["category"]} for i,a in enumerate(actions)]

def command_center(profile):
    g=gap_analysis(profile)
    return {"coverage_pct":g["coverage_pct"],"skill_gaps":g["skill_gaps"],
            "priority_actions":priority_actions(profile),"milestones":milestone_plan(profile)}

def weekly_review(profile, completed=None):
    completed=set(completed or [])
    actions=priority_actions(profile)
    done=sum(1 for a in actions if a["action"] in completed)
    return {"planned":len(actions),"completed":done,
            "completion_pct":round(100*done/max(1,len(actions)),1),
            "next_actions":[a for a in actions if a["action"] not in completed][:5]}
