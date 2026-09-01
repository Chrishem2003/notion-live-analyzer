"""Advancement 8: Advanced CV/Resume Designer."""
from html import escape
import re

TEMPLATES = {
    "Executive": {"font":"Georgia","density":"spacious","sections":["summary","experience","education","skills","certifications","awards"]},
    "Modern": {"font":"Arial","density":"balanced","sections":["summary","experience","skills","education","projects","certifications"]},
    "Minimal": {"font":"Arial","density":"compact","sections":["summary","experience","skills","education"]},
    "Technical": {"font":"Arial","density":"compact","sections":["summary","skills","experience","projects","education","certifications"]},
    "Graduate": {"font":"Arial","density":"spacious","sections":["summary","education","projects","skills","experience","certifications"]},
    "Academic": {"font":"Georgia","density":"spacious","sections":["summary","education","experience","publications","awards","skills"]},
}
ALL_SECTIONS=("summary","experience","education","skills","projects","certifications","awards","publications")

def design_model(profile, template="Modern", order=None, hidden=None, font_size=11, margin=0.7, show_contact=True):
    cfg=TEMPLATES.get(template,TEMPLATES["Modern"])
    order=list(order or cfg["sections"])
    hidden=set(hidden or [])
    sections=[x for x in order if x in ALL_SECTIONS and x not in hidden]
    return {"template":template if template in TEMPLATES else "Modern",
            "font":cfg["font"],"density":cfg["density"],
            "font_size":max(9,min(18,int(font_size))),
            "margin":max(.3,min(1.5,float(margin))),
            "sections":sections,"show_contact":bool(show_contact)}

def _e(x): return escape(str(x or ""))

def _section(p,n):
    if n=="summary": return "<h2>Summary</h2><p>"+_e(p.get("summary"))+"</p>"
    if n=="skills": return "<h2>Skills</h2><p>"+" • ".join(_e(x) for x in p.get("skills",[]))+"</p>"
    if n=="education": return "<h2>Education</h2><p>"+_e(p.get("education"))+"</p>"
    if n in ("certifications","awards","publications"):
        vals=p.get(n,[]); vals=[vals] if isinstance(vals,str) else vals
        return "<h2>"+n.title()+"</h2><p>"+" • ".join(_e(x) for x in vals)+"</p>"
    if n=="experience":
        return "<h2>Experience</h2>"+"".join(
            "<h3>"+_e(x.get("title"))+" — "+_e(x.get("company"))+"</h3><small>"+_e(x.get("dates"))+
            "</small><p>"+_e(x.get("description")).replace("\n","<br>")+"</p>" for x in p.get("experience",[]))
    if n=="projects":
        return "<h2>Projects</h2>"+"".join("<h3>"+_e(x.get("title"))+"</h3><p>"+_e(x.get("description"))+"</p>" for x in p.get("projects",[]))
    return ""

def render_design(profile, model):
    contact=""
    if model["show_contact"]:
        contact=" • ".join(_e(profile.get(k)) for k in ("email","phone","location") if profile.get(k))
    body="".join(_section(profile,s) for s in model["sections"])
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
body{{font-family:{model['font']};font-size:{model['font_size']}pt;line-height:1.45;max-width:850px;margin:{model['margin']}in auto}}
h1{{margin-bottom:2px}}h2{{border-bottom:1px solid #888;padding-bottom:3px;margin-top:20px}}h3{{margin-bottom:2px}}
small{{opacity:.75}}
</style></head><body><h1>{_e(profile.get("name","Your Name"))}</h1>
<b>{_e(profile.get("headline"))}</b><p>{contact}</p>{body}</body></html>"""

def page_estimate(profile, model):
    words=len(re.sub(r"<[^>]+>"," ",render_design(profile,model)).split())
    per_page={"compact":520,"balanced":430,"spacious":350}.get(model["density"],430)
    return max(1,(words+per_page-1)//per_page)
