"""Advancement 10 — Job Opportunity Intelligence.

This module is provider-neutral: it ranks and organizes job records supplied by
a real connector/importer. It never invents live vacancies, salaries, employers,
or application outcomes.
"""
from collections import Counter
from datetime import datetime

def normalize_jobs(jobs):
    out=[]
    for raw in jobs or []:
        j=dict(raw)
        j["title"]=str(j.get("title","")).strip()
        j["company"]=str(j.get("company","")).strip()
        j["location"]=str(j.get("location","")).strip()
        j["url"]=str(j.get("url","")).strip()
        j["source"]=str(j.get("source","")).strip() or "Imported"
        try: j["match_score"]=float(j.get("match_score",0))
        except (TypeError,ValueError): j["match_score"]=0.0
        out.append(j)
    return out

def rank_jobs(jobs, min_match=0, location=None, remote_only=False):
    rows=normalize_jobs(jobs)
    result=[]
    for j in rows:
        if j["match_score"] < float(min_match): continue
        if location and location.lower() not in j["location"].lower(): continue
        if remote_only and "remote" not in j["location"].lower(): continue
        result.append(j)
    return sorted(result,key=lambda x:(x["match_score"],x["title"].lower()),reverse=True)

def source_summary(jobs):
    c=Counter(j["source"] for j in normalize_jobs(jobs))
    return [{"source":k,"jobs":v} for k,v in sorted(c.items(),key=lambda x:x[1],reverse=True)]

def market_summary(jobs):
    rows=normalize_jobs(jobs)
    if not rows: return {"count":0,"average_match":0,"top_match":0,"sources":[]}
    scores=[j["match_score"] for j in rows]
    return {"count":len(rows),"average_match":round(sum(scores)/len(scores),1),
            "top_match":max(scores),"sources":source_summary(rows)}

def shortlist(jobs, limit=10):
    return rank_jobs(jobs)[:max(1,int(limit))]

def import_contract():
    return {
        "required":["title","company"],
        "recommended":["location","url","source","match_score"],
        "rule":"Only records supplied by a real importer/connector are treated as opportunities."
    }
