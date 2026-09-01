import re,html
STOP=set("the and for with from that this your you are have will into our job role work years year experience skills using ability required preferred including their they a an of to in on as is be or at by we us".split())
def tokens(text):
 return {x.lower() for x in re.findall(r"[A-Za-z][A-Za-z+#.-]{1,}",text or "") if x.lower() not in STOP}
def profile_text(p):
 return "\n".join([str(p.get(k,"")) for k in ("name","headline","summary","education")]+[" ".join(p.get("skills",[]))]+[str(e.get("description","")) for e in p.get("experience",[])])
def analyze_job(p,jd):
 a,b=tokens(profile_text(p)),tokens(jd); freq={}
 for x in tokens(jd):freq[x]=len(re.findall(r"\b"+re.escape(x)+r"\b",(jd or "").lower()))
 ranked=sorted(freq,key=lambda x:(-freq[x],x))
 return {"coverage":round(len(a&b)/max(1,len(b))*100,1),"matched":[x for x in ranked if x in a][:50],"missing":[x for x in ranked if x not in a][:30]}
def quality(text):
 words=len(text.split()); nums=len(re.findall(r"\b\d+(?:\.\d+)?%?\b",text)); verbs=sum(bool(re.search(r"\b"+v+r"\b",text,re.I)) for v in ["led","managed","built","improved","delivered","designed","analyzed","created","reduced","increased","developed","launched"])
 return {"score":round(min(100,30+min(words,900)/900*30+min(nums,15)/15*20+min(verbs,10)/10*20)),"words":words,"metrics":nums,"action_verbs":verbs}
def validate(p):
 issues=[]
 for k,label in [("name","Name"),("headline","Headline"),("summary","Summary")]:
  if not p.get(k):issues.append(label+" is missing.")
 if not p.get("skills"):issues.append("Skills are missing.")
 if not p.get("experience"):issues.append("Experience is missing.")
 return issues
def render_html(p,theme="Modern",font_size=16,show_contact=True):
 themes={"Executive":"Georgia","Modern":"Arial","Minimal":"Arial","Technical":"Arial","Graduate":"Arial"}
 fs=max(11,min(int(font_size),24)); esc=lambda x:html.escape(str(x or ""))
 contact=" • ".join(esc(p.get(k,"")) for k in ("email","phone","location") if p.get(k)) if show_contact else ""
 ex="".join(f"<h3>{esc(e.get('title'))} — {esc(e.get('company'))}</h3><small>{esc(e.get('dates'))}</small><p>{esc(e.get('description')).replace(chr(10),'<br>')}</p>" for e in p.get("experience",[]))
 return f"<html><body style='font-family:{themes.get(theme,'Arial')};max-width:850px;margin:40px auto;line-height:1.55;font-size:{fs}px'><h1>{esc(p.get('name','Your Name'))}</h1><b>{esc(p.get('headline'))}</b><p>{contact}</p><h2>Summary</h2><p>{esc(p.get('summary'))}</p><h2>Skills</h2><p>{' • '.join(esc(x) for x in p.get('skills',[]))}</p><h2>Experience</h2>{ex}<h2>Education</h2><p>{esc(p.get('education'))}</p></body></html>"
