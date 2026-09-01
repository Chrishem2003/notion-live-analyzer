"""Advancement 6: deterministic, evidence-first career intelligence."""
from dataclasses import dataclass, asdict
import re

STOP=set("the and for with from that this your you are have will into our job role work years year experience skills using ability required preferred including their they a an of to in on as is be or at by we us".split())

@dataclass
class Evidence:
    evidence_id:str
    kind:str
    title:str
    text:str
    skills:list
    metrics:list
    source:str="profile"

def tokens(text):
    return {x.lower() for x in re.findall(r"[A-Za-z][A-Za-z0-9+#./-]{1,}", text or "") if x.lower() not in STOP}

def metrics(text):
    return re.findall(r"\b\d+(?:\.\d+)?(?:%|[KMBkmb])?\b", text or "")

def build_evidence_graph(profile):
    out=[]
    for i,e in enumerate(profile.get("experience",[]) or []):
        text=str(e.get("description", ""))
        out.append(Evidence(f"exp-{i+1}","experience",f"{e.get('title','')} — {e.get('company','')}".strip(" —"),text,sorted(tokens(text)&{str(x).lower() for x in profile.get("skills",[])}),metrics(text)))
    for i,p in enumerate(profile.get("projects",[]) or []):
        text=str(p.get("description", "")); out.append(Evidence(f"project-{i+1}","project",str(p.get("title","")),text,sorted(tokens(text)),metrics(text),"project"))
    for i,a in enumerate(profile.get("achievements",[]) or []):
        text=str(a); out.append(Evidence(f"achievement-{i+1}","achievement",f"Achievement {i+1}",text,sorted(tokens(text)),metrics(text)))
    for i,c in enumerate(profile.get("certifications",[]) or []):
        text=str(c); out.append(Evidence(f"cert-{i+1}","certification",text,text,[],[]))
    return out

def extract_requirements(job_text):
    text=job_text or ""; terms=sorted(tokens(text)); must=set()
    for line in text.splitlines():
        if re.search(r"\b(required|must have|must-have|essential|minimum)\b",line,re.I): must |= tokens(line)
    seniority=[x for x in ("intern","junior","mid","senior","lead","principal","manager","director","executive") if re.search(r"\b"+x+r"\b",text,re.I)]
    return {"terms":terms,"must_have":sorted(must),"seniority":seniority}

def match_job(profile, job_text):
    req=extract_requirements(job_text); evidence=build_evidence_graph(profile)
    corpus=tokens("\n".join(e.text+" "+" ".join(e.skills) for e in evidence)) | {str(x).lower() for x in profile.get("skills",[])}
    terms=set(req["terms"]); matched=sorted(corpus&terms); missing=sorted(terms-corpus)
    must=set(req["must_have"]); must_matched=sorted(corpus&must)
    direct=sum(1 for e in evidence if tokens(e.text)&terms); quantified=sum(1 for e in evidence if e.metrics)
    evidence_score=min(100,round(direct/max(1,len(evidence))*70+quantified/max(1,len(evidence))*30,1))
    keyword_score=round(100*len(matched)/max(1,len(terms)),1)
    must_score=round(100*len(must_matched)/max(1,len(must)),1) if must else 100.0
    seniority_score=100.0 if not req["seniority"] or any(x in str(profile).lower() for x in req["seniority"]) else 50.0
    overall=round(keyword_score*.35+must_score*.30+evidence_score*.25+seniority_score*.10,1)
    return {"overall":overall,"keyword_score":keyword_score,"must_have_score":must_score,"evidence_score":evidence_score,"seniority_score":seniority_score,"matched":matched[:80],"missing":missing[:80],"must_have_missing":sorted(must-set(must_matched)),"evidence":[asdict(e) for e in evidence if tokens(e.text)&terms or e.metrics]}

def career_health(profile):
    evidence=build_evidence_graph(profile); metric_count=sum(len(e.metrics) for e in evidence); populated=sum(bool(e.text.strip()) for e in evidence)
    score=min(100,round(min(len(profile.get("skills",[])),15)/15*25+min(populated,10)/10*30+min(metric_count,10)/10*20+min(len(profile.get("achievements",[])),10)/10*15+(10 if profile.get("headline") else 0)))
    rec=[]
    if not metric_count: rec.append("Add measurable outcomes to experience or achievements.")
    if not profile.get("achievements"): rec.append("Create an achievement bank with specific outcomes.")
    if len(profile.get("skills",[]))<5: rec.append("Add more verified skills linked to real evidence.")
    if not profile.get("summary"): rec.append("Add a professional summary grounded in your evidence.")
    return {"score":score,"evidence_count":len(evidence),"metrics":metric_count,"skills":len(profile.get("skills",[])),"achievements":len(profile.get("achievements",[])),"recommendations":rec}
