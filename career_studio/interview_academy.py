"""Advancement 11 — Advanced Interview Academy.

Evidence-first interview preparation. Questions are generated from supplied
job/profile data; model answers are never fabricated.
"""
from collections import Counter

QUESTION_TYPES = ("behavioral","technical","situational","motivation","leadership","culture")

def extract_focus(profile, job_text=""):
    skills=[str(x) for x in profile.get("skills",[]) if str(x).strip()]
    words=set(job_text.lower().split())
    matched=[s for s in skills if s.lower() in words]
    return matched or skills[:8]

def question_bank(profile, job_text="", count=12):
    """Return exactly ``count`` questions, cycling through grounded patterns."""
    count=max(1,int(count))
    focus=extract_focus(profile,job_text)
    role=profile.get("target_role") or "the target role"
    patterns=[
      ("behavioral",f"Tell me about an achievement relevant to {role}."),
      ("behavioral","Describe a difficult problem you solved and how you approached it."),
      ("situational",f"How would you approach a high-priority problem involving {focus[0] if focus else 'a core skill'}?"),
      ("motivation",f"Why are you interested in {role}?"),
      ("leadership","Describe a time you influenced an outcome without relying on authority."),
      ("culture","What working environment helps you perform at your best?"),
      ("technical",f"Explain how you have used {focus[0] if focus else 'a core skill'} in a real project or role."),
      ("technical",f"How would you troubleshoot a difficult problem in {focus[1] if len(focus)>1 else (focus[0] if focus else 'your area')}?"),
      ("situational","Tell me how you would prioritize competing urgent requests."),
      ("behavioral","Describe a mistake, what you learned, and what you changed afterward."),
      ("leadership","How do you handle disagreement with a teammate or stakeholder?"),
      ("motivation",f"What makes you a strong fit for {role}?"),
    ]
    result=[]
    for i in range(count):
        t,q=patterns[i % len(patterns)]
        if i >= len(patterns):
            q=q.rstrip("?") + f" (Practice variation {i+1})?"
        result.append({"type":t,"question":q})
    return result

def build_star_prompt(question, evidence):
    return {"situation":"Use a real situation from your evidence.",
            "task":"State the responsibility or objective.",
            "action":"Explain what you personally did.",
            "result":"State the real outcome; do not invent metrics.",
            "question":question,"evidence":evidence}

def score_answer(answer, question_type="behavioral"):
    text=str(answer or "").strip()
    if not text: return {"score":0,"flags":["No answer supplied."]}
    low=text.lower()
    markers=["because","I ","i ","result","impact","improved","reduced","increased"]
    evidence=sum(1 for x in markers if x.lower() in low)
    length=min(len(text.split())/180,1)
    score=round(min(100,25 + evidence*10 + length*35))
    flags=[]
    if len(text.split())<35: flags.append("Answer may be too brief; add concrete evidence.")
    if not any(x in low for x in ("result","impact","improved","reduced","increased")):
        flags.append("Add a verified outcome or impact where available.")
    return {"score":score,"flags":flags}

def readiness(profile, answers=None, job_text=""):
    qs=question_bank(profile,job_text,12)
    answers=answers or {}
    scores=[score_answer(answers.get(q["question"],""))["score"] for q in qs if answers.get(q["question"])]
    completion=round(100*len(scores)/max(1,len(qs)))
    quality=round(sum(scores)/len(scores)) if scores else 0
    return {"questions":len(qs),"answered":len(scores),"completion":completion,
            "quality":quality,"readiness":round(completion*.45+quality*.55)}
