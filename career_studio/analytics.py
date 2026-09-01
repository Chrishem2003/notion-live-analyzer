"""Advancement 9: deterministic career/application analytics."""
from collections import Counter, defaultdict
STATUSES=("saved","applied","screening","interview","final","offer","rejected","withdrawn")

def normalize(apps):
    out=[]
    for a in apps or []:
        x=dict(a); x["status"]=str(x.get("status","saved")).lower()
        if x["status"] not in STATUSES: x["status"]="saved"
        out.append(x)
    return out

def funnel(apps):
    c=Counter(a["status"] for a in normalize(apps)); n=c["applied"]
    return {"total":sum(c.values()), **{s:c[s] for s in STATUSES},
            "response_rate":round(100*(sum(c.values())-c["saved"]-n)/max(1,n),1),
            "interview_rate":round(100*c["interview"]/max(1,n),1),
            "offer_rate":round(100*c["offer"]/max(1,n),1)}

def group(apps,key):
    rows=defaultdict(Counter)
    for a in normalize(apps): rows[a.get(key) or "Unspecified"][a["status"]]+=1
    result=[]
    for name,c in rows.items():
        n=c["applied"]
        result.append({key:name,"applications":n,"interviews":c["interview"],
                       "offers":c["offer"],"interview_rate":round(100*c["interview"]/max(1,n),1),
                       "offer_rate":round(100*c["offer"]/max(1,n),1)})
    return sorted(result,key=lambda x:(x["interview_rate"],x["offer_rate"]),reverse=True)

def by_cv_version(apps): return group(apps,"cv_version")
def by_role(apps): return group(apps,"role")

def by_source(apps):
    rows=defaultdict(Counter)
    for a in normalize(apps): rows[a.get("source") or "Unspecified"][a["status"]]+=1
    return [{"source":k,"applications":v["applied"],"interviews":v["interview"],"offers":v["offer"]} for k,v in rows.items()]

def recommendations(apps):
    f=funnel(apps); r=[]
    if f["applied"]<5: r.append("Collect at least five completed applications before treating conversion rates as directional.")
    if f["applied"] and f["interview_rate"]<10: r.append("Review job targeting, evidence match and CV tailoring.")
    if not r: r.append("Keep recording outcomes to improve the reliability of your analytics.")
    return r

def dashboard(apps):
    return {"funnel":funnel(apps),"cv_versions":by_cv_version(apps),"roles":by_role(apps),
            "sources":by_source(apps),"recommendations":recommendations(apps)}
