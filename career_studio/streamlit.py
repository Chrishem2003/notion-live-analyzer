import streamlit as st,datetime,json,traceback
from .database import *
from .engine import *
from .importers import extract_text
from .exports import docx_bytes,pdf_bytes
from .ai import configured,ask
from .intelligence import build_evidence_graph, match_job, career_health
from .database import save_job_analysis, list_job_analyses
PAGES=["🏠 Command Center","🤖 Career Agent Council","🧑‍💼 Specialist Agents","🧠 Career Intelligence","🧩 Evidence & Achievement Bank","🎯 Job Match & Tailoring","📚 Job Analysis History","🧬 Professional DNA","📥 Import CV","🎨 CV Studio","📄 Export Center","🎯 Legacy Job Intelligence","✉️ Cover Letters","🎤 Interview Coach","🔗 LinkedIn Studio","🌐 Portfolio","🌍 International / Executive / Graduate","🗄️ Document Vault","💼 Applications & Analytics","🤖 AI Copilot","🧪 Validation & Health","🔍 Feature Audit"]

def user_email():return st.session_state.get("user_identity",{}).get("email","local@career-studio")
def getp():return load_profile(user_email())
def dashboard():
 st.title("🚀 Sovereign Career Studio");st.caption("Advancement 5 — cumulative career workspace")
 st.columns(3)[0].metric("Documents",len(list_documents(user_email())))
 st.columns(3)[1].metric("Projects",len(list_projects(user_email())))
 st.columns(3)[2].metric("Applications",len(list_applications(user_email())))
def dna():
 p=getp();st.title("🧬 Professional DNA")
 with st.form("dna"):
  p["name"]=st.text_input("Name",p.get("name",""));p["headline"]=st.text_input("Headline",p.get("headline",""));p["email"]=st.text_input("Email",p.get("email",""));p["phone"]=st.text_input("Phone",p.get("phone",""));p["location"]=st.text_input("Location",p.get("location",""));p["summary"]=st.text_area("Summary",p.get("summary",""));skills=st.text_area("Skills",", ".join(p.get("skills",[])));p["education"]=st.text_area("Education",p.get("education",""))
  if st.form_submit_button("Save profile"):p["skills"]=[x.strip() for x in skills.replace("\n",",").split(",") if x.strip()];save_profile(user_email(),p);st.success("Saved")
 ex=p.get("experience",[])
 for i,e in enumerate(ex):
  with st.expander(f"Experience {i+1}"):e["title"]=st.text_input("Title",e.get("title",""),key=f"t{i}");e["company"]=st.text_input("Company",e.get("company",""),key=f"c{i}");e["dates"]=st.text_input("Dates",e.get("dates",""),key=f"d{i}");e["description"]=st.text_area("Evidence",e.get("description",""),key=f"x{i}")
 if st.button("Add experience"):ex.append({"title":"","company":"","dates":"","description":""})
 p["experience"]=ex
 if st.button("Save experience"):save_profile(user_email(),p);st.success("Experience saved")
def importer():
 st.title("📥 Import CV / Resume");u=st.file_uploader("PDF, DOCX or TXT",type=["pdf","docx","txt"])
 if u and st.button("Extract text"):
  try:t=extract_text(u);st.text_area("Extracted text — review before using",t,height=400);save_document(user_email(),"import",u.name,t)
  except Exception as e:st.error(str(e))
def cvstudio():
 p=getp();st.title("🎨 CV Studio");theme=st.selectbox("Template",["Executive","Modern","Minimal","Technical","Graduate"]);size=st.slider("Font size",11,22,16);contact=st.toggle("Show contact",True)
 out=render_html(p,theme,size,contact);st.components.v1.html(out,height=700,scrolling=True)
 if st.button("Save CV version"):save_document(user_email(),"cv_version",f"{theme} {datetime.datetime.now():%Y-%m-%d %H:%M}",out,{"theme":theme,"font_size":size})
def export():
 p=getp();st.title("📄 Export Center");st.download_button("DOCX",docx_bytes(p),"professional_cv.docx");st.download_button("PDF",pdf_bytes(p),"professional_cv.pdf");st.download_button("HTML",render_html(p),"professional_cv.html","text/html")
def intelligence():
 p=getp();st.title("🎯 Job Intelligence");jd=st.text_area("Job description",height=300)
 if st.button("Analyze") and jd:
  r=analyze_job(p,jd);st.metric("Keyword coverage",f"{r['coverage']}%");st.write("Matched",r["matched"]);st.write("Potential gaps",r["missing"]);st.caption("Heuristic only; not an employer ATS simulation.")
def letters():
 p=getp();st.title("✉️ Cover Letters");co=st.text_input("Company");role=st.text_input("Role");jd=st.text_area("Job requirements")
 if st.button("Generate evidence-based draft"):
  r=analyze_job(p,jd);body=f"Dear Hiring Team,\n\nI am interested in the {role} opportunity at {co}. {p.get('summary','')}\n\nMy relevant existing skills include {', '.join(p.get('skills',[])[:8])}. Relevant terms from the role include {', '.join(r['matched'][:10])}.\n\nKind regards,\n{p.get('name','')}";st.text_area("Draft",body,height=350);save_document(user_email(),"cover_letter",f"{role} — {co}",body)
def interview():
 st.title("🎤 Interview Coach");a=st.text_area("Paste your answer")
 if a:
  low=a.lower();checks={k:(k in low) for k in ["situation","task","action","result"]};st.write(checks);st.json(quality(a))
def linkedin():
 p=getp();st.title("🔗 LinkedIn Studio");st.text_input("Headline",p.get("headline","")+" | "+" | ".join(p.get("skills",[])[:4]));st.text_area("About",p.get("summary",""));st.write("Keywords:",p.get("skills",[]))
def portfolio():
 st.title("🌐 Portfolio"); 
 with st.form("project"):
  title=st.text_input("Title");role=st.text_input("Role");desc=st.text_area("Evidence");skills=st.text_input("Skills");url=st.text_input("URL")
  if st.form_submit_button("Save") and title:add_project(user_email(),title,role,desc,skills,url);st.rerun()
 for x in list_projects(user_email()):st.subheader(x["title"]);st.caption(x["role"]);st.write(x["description"]);st.caption(x["url"])
def special():
 st.title("🌍 International / 👔 Executive / 🎓 Graduate");mode=st.selectbox("Workflow",["International","Executive","Graduate"]);e=st.text_area("Evidence and context",height=250)
 if st.button("Save workspace evidence"):save_document(user_email(),mode.lower(),mode,e);st.success("Saved")
def vault():
 st.title("🗄️ Document Vault")
 for d in list_documents(user_email()):
  with st.expander(f"{d['kind']} — {d['name']}"):st.caption(d["created_at"]);st.text_area("Content",d["content"],height=180,key=f"v{d['id']}",disabled=True)
def applications():
 st.title("💼 Applications & Analytics")
 with st.form("app"):
  co=st.text_input("Company");role=st.text_input("Role");status=st.selectbox("Status",["Saved","Applied","Assessment","Interview","Offer","Rejected"]);date=st.date_input("Date",datetime.date.today());notes=st.text_area("Notes")
  if st.form_submit_button("Save") and co and role:add_application(user_email(),co,role,status,str(date),notes);st.rerun()
 a=list_applications(user_email());st.dataframe(a,use_container_width=True)
 if a:
  counts={};[counts.update({x["status"]:counts.get(x["status"],0)+1}) for x in a];st.bar_chart(counts)
def copilot():
 st.title("🤖 AI Copilot")
 if not configured():st.warning("AI is disabled until CAREER_AI_ENDPOINT, CAREER_AI_MODEL and CAREER_AI_API_KEY are configured.")
 else:
  q=st.text_area("Ask using your saved profile")
  if st.button("Ask AI") and q:
   try:st.write(ask("You are a career assistant. Never invent qualifications.",json.dumps({"profile":getp(),"request":q})))
   except Exception as e:st.error(str(e))
def health():
 st.title("🧪 Validation & Health");p=getp()
 for x in validate(p):st.warning(x)
 st.json(quality(profile_text(p)))
 try:
  with connect() as c:v=c.execute("SELECT value FROM career_meta WHERE key='schema_version'").fetchone()["value"]
  st.success("Database reachable. Schema "+v)
 except Exception as e:st.error(str(e))
def audit():
 st.title("🔍 Feature Audit");st.dataframe([{"Feature":x,"Status":"Implemented"} for x in PAGES[:-1]]+[{"Feature":"OCR scanned PDF","Status":"Not implemented"},{"Feature":"Native drag-and-drop canvas","Status":"Not implemented"},{"Feature":"Production security audit","Status":"Not implemented"}],use_container_width=True)

def career_intelligence():
    p=getp(); st.title("🧠 Career Intelligence Engine")
    h=career_health(p); cols=st.columns(4)
    cols[0].metric("Career health",f"{h['score']}/100"); cols[1].metric("Evidence",h["evidence_count"]); cols[2].metric("Measured outcomes",h["metrics"]); cols[3].metric("Skills",h["skills"])
    if h["recommendations"]:
        st.subheader("Highest-value improvements")
        for x in h["recommendations"]: st.warning(x)
    else: st.success("Your evidence base is well populated.")
    graph=build_evidence_graph(p)
    st.subheader("Evidence graph")
    st.dataframe([{"ID":e.evidence_id,"Type":e.kind,"Title":e.title,"Metrics":", ".join(e.metrics),"Skills":", ".join(e.skills)} for e in graph],use_container_width=True)

def evidence_bank():
    p=getp(); st.title("🧩 Evidence & Achievement Bank")
    a=p.get("achievements",[])
    for i,v in enumerate(a): a[i]=st.text_area(f"Achievement {i+1}",v,key=f"v6ach{i}")
    if st.button("Add achievement"): a.append(""); st.rerun()
    p["achievements"]=a
    if st.button("Save evidence bank"): save_profile(user_email(),p); st.success("Saved.")
    st.caption("Only user-supplied evidence is used for matching; the system does not invent qualifications.")

def job_match_v6():
    p=getp(); st.title("🎯 Job Match & Tailoring")
    title=st.text_input("Job title"); company=st.text_input("Company"); jd=st.text_area("Complete job description",height=320)
    if st.button("Analyze and save") and jd:
        r=match_job(p,jd); save_job_analysis(user_email(),title,company,jd,r)
        cols=st.columns(5)
        for c,label,key in zip(cols,["Overall","Keywords","Must-have","Evidence","Seniority"],["overall","keyword_score","must_have_score","evidence_score","seniority_score"]): c.metric(label,f"{r[key]}%")
        st.subheader("Matched requirements"); st.write(", ".join(r["matched"]) or "No direct matches.")
        st.subheader("Potential gaps"); st.write(", ".join(r["missing"]) or "No obvious term gaps.")
        if r["must_have_missing"]: st.error("Potential must-have gaps: "+", ".join(r["must_have_missing"]))
        st.subheader("Evidence to prioritize")
        for e in r["evidence"]: st.markdown(f"**{e['title']}** — {e['text']}")
        st.caption("Transparent heuristic; not a claim to reproduce a proprietary employer ATS.")

def job_history():
    st.title("📚 Job Analysis History")
    rows=list_job_analyses(user_email())
    if not rows: st.info("No saved job analyses yet."); return
    for r in rows:
        result=r["result"]
        with st.expander(f"{r.get('job_title') or 'Untitled'} — {r.get('company') or 'Unknown'} — {result.get('overall','?')}%"):
            st.caption(r.get("created_at","")); st.write("Matched:", ", ".join(result.get("matched",[]))); st.write("Gaps:", ", ".join(result.get("missing",[])))


def agent_council():
    p=getp(); st.title("🤖 Career Agent Council")
    st.caption("Multiple specialist agents work from the same verified career evidence. AI enhancement is optional and never silently simulated.")
    jd=st.text_area("Optional target job description",height=260)
    if st.button("Run Career Council"):
        for r in run_career_council(p,jd):
            with st.expander(r.agent,expanded=True):
                st.success(r.summary)
                for x in r.findings: st.write("• "+x)
                st.subheader("Next actions")
                for x in r.next_actions: st.write("→ "+x)
                if configured() and st.button("AI-enhance "+r.agent,key="enh_"+r.agent.replace(" ","_")):
                    rr=ai_enhance(r,p,"Improve this agent's recommendations using only the supplied evidence.")
                    st.write(rr.summary)

def specialist_agents():
    p=getp(); st.title("🧑‍💼 Specialist Agents")
    choice=st.selectbox("Agent",["CV Architect","Job Analyst","Interview Strategist","Career Strategist","Application Agent"])
    jd=st.text_area("Target job description (required for Job Analyst, Interview Strategist and Application Agent)",height=240)
    if st.button("Run specialist"):
        funcs={"CV Architect":lambda: __import__("career_studio.agents",fromlist=["cv_architect"]).cv_architect(p),
               "Job Analyst":lambda: __import__("career_studio.agents",fromlist=["job_analyst"]).job_analyst(p,jd),
               "Interview Strategist":lambda: __import__("career_studio.agents",fromlist=["interview_strategist"]).interview_strategist(p,jd),
               "Career Strategist":lambda: __import__("career_studio.agents",fromlist=["career_strategist"]).career_strategist(p),
               "Application Agent":lambda: __import__("career_studio.agents",fromlist=["application_agent"]).application_agent(p,jd)}
        if choice in ("Job Analyst","Interview Strategist","Application Agent") and not jd:
            st.error("Provide a target job description for this agent.")
        else:
            r=funcs[choice]();st.success(r.summary)
            for x in r.findings:st.write("• "+x)
            for x in r.next_actions:st.write("→ "+x)


def career_analytics():
    p=getp(); st.title("📊 Career Analytics")
    d=analytics_dashboard(p.get("applications",[])); f=d["funnel"]
    cols=st.columns(6)
    for col,k in zip(cols,["applied","screening","interview","final","offer","rejected"]): col.metric(k.title(),f[k])
    st.metric("Interview conversion",f"{f['interview_rate']}%"); st.metric("Offer conversion",f"{f['offer_rate']}%")
    for x in d["recommendations"]: st.info(x)
    st.dataframe([{"Stage":k.title(),"Count":f[k]} for k in ["saved","applied","screening","interview","final","offer","rejected","withdrawn"]],use_container_width=True)
    if d["roles"]: st.subheader("By target role"); st.dataframe(d["roles"],use_container_width=True)
    if d["sources"]: st.subheader("By source"); st.dataframe(d["sources"],use_container_width=True)

def cv_performance_lab():
    p=getp(); st.title("🧪 CV Performance Lab")
    st.caption("Observational analytics from recorded application outcomes; not a causal guarantee.")
    st.dataframe(analytics_dashboard(p.get("applications",[]))["cv_versions"],use_container_width=True)


def opportunity_intelligence():
    p=getp(); st.title("🌐 Job Opportunity Intelligence")
    st.caption("Rank and organize real imported job records. This workspace does not fabricate live vacancies.")
    jobs=p.get("job_opportunities",[])
    if not jobs:
        st.info("No real job records have been imported yet.")
        st.code(str(import_contract()),language="python")
        return
    min_match=st.slider("Minimum match score",0,100,60)
    remote=st.toggle("Remote only",False)
    location=st.text_input("Location filter")
    rows=rank_jobs(jobs,min_match,location or None,remote)
    st.metric("Matching opportunities",len(rows))
    if rows:
        st.dataframe(rows,use_container_width=True)
        st.download_button("Export shortlist JSON",json.dumps(shortlist(rows,10),indent=2),
                           "job_shortlist.json","application/json")
    st.subheader("Market snapshot")
    st.json(market_summary(jobs))


def interview_academy():
    p=getp(); st.title("🎤 Advanced Interview Academy")
    st.caption("Practice from your actual profile and target role. The system does not invent achievements or interview outcomes.")
    jd=st.text_area("Target job description",height=220)
    qs=question_bank(p,jd,12)
    answers={}
    for i,q in enumerate(qs):
        answers[q["question"]]=st.text_area(f"{i+1}. [{q['type'].title()}] {q['question']}",key=f"iaq_{i}")
    if st.button("Evaluate Interview Readiness"):
        r=readiness(p,answers,jd); st.metric("Readiness",f"{r['readiness']}%")
        st.write(f"Answered {r['answered']} of {r['questions']} questions.")
        for q in qs:
            a=answers.get(q["question"],"")
            if a:
                s=score_answer(a,q["type"])
                with st.expander(q["question"]):
                    st.metric("Answer quality",f"{s['score']}%")
                    for flag in s["flags"]: st.warning(flag)
                    st.json(build_star_prompt(q["question"],"Use only your verified career evidence."))

def interview_question_bank():
    p=getp(); st.title("📝 Interview Question Bank")
    jd=st.text_area("Paste target job description",height=220)
    for q in question_bank(p,jd,20):
        st.write(f"**{q['type'].title()}** — {q['question']}")

def render_career_studio():
    with st.sidebar:
        page=st.radio("Career Studio",PAGES,key="career_studio_nav")
    routes={
        PAGES[0]:dashboard,PAGES[1]:career_intelligence,PAGES[2]:evidence_bank,PAGES[3]:job_match_v6,PAGES[4]:job_history,
        PAGES[5]:dna,PAGES[6]:importer,PAGES[7]:cvstudio,PAGES[8]:export,PAGES[9]:intelligence,PAGES[10]:letters,
        PAGES[11]:interview,PAGES[12]:linkedin,PAGES[13]:portfolio,PAGES[14]:special,PAGES[15]:vault,
        PAGES[16]:applications,PAGES[17]:copilot,PAGES[18]:health,PAGES[19]:audit}
    try:
        routes[page]()
    except Exception as e:
        st.error(f"Career Studio workspace error: {type(e).__name__}: {e}")
        with st.expander("Technical traceback"): st.code(traceback.format_exc())


from .negotiation import compare_offers, target_range, negotiation_position, script_points, package_score, market_summary

from .career_strategy import command_center, gap_analysis, priority_actions, milestone_plan, weekly_review

from .career_os import build_career_os, executive_snapshot


def career_command_center():
    p=getp()
    st.title("🚀 Career OS — Unified Command Center")
    st.caption("One workspace for your CV, applications, opportunities, interviews, compensation and career strategy.")
    data=build_career_os(p)
    snap=executive_snapshot(data)

    cols=st.columns(6)
    metrics=[
        ("Skill coverage",f"{snap['skill_coverage_pct']}%"),
        ("Applications",snap["applications"]),
        ("Interview rate",f"{snap['interview_rate']}%"),
        ("Offer rate",f"{snap['offer_rate']}%"),
        ("Interview readiness",f"{snap['interview_readiness']}%"),
        ("Offers tracked",snap["offers_tracked"]),
    ]
    for col,(label,value) in zip(cols,metrics):
        col.metric(label,value)

    if snap["skill_gaps"]:
        st.subheader("🎯 Highest-priority skill gaps")
        for x in snap["skill_gaps"][:8]: st.write("• "+x)

    st.subheader("📌 Priority career actions")
    for x in data["career_strategy"]["priority_actions"]:
        st.write(f"**{x['priority'].upper()}** — {x['action']}")

    st.subheader("🌐 Top recorded/imported opportunities")
    if data["opportunities"]["top_matches"]:
        st.dataframe(data["opportunities"]["top_matches"],use_container_width=True)
    else:
        st.info("No real opportunity records are currently available.")

    st.subheader("🧭 Integrity controls")
    st.success("The Career OS does not fabricate vacancies, application outcomes, salaries, achievements or employment predictions.")

    with st.expander("View complete Career OS data"):
        st.json(data)
