"""Advancement 12 — Salary & Negotiation Studio."""
from statistics import median

def _num(v):
    try: return float(v)
    except (TypeError,ValueError): return None

def normalize_offers(offers):
    out=[]
    for raw in offers or []:
        x=dict(raw); x["base"]=_num(x.get("base"))
        x["bonus"]=_num(x.get("bonus")) or 0; x["equity"]=_num(x.get("equity")) or 0
        x["currency"]=str(x.get("currency","")).upper(); out.append(x)
    return out

def total_comp(offer):
    return (_num(offer.get("base")) or 0)+(_num(offer.get("bonus")) or 0)+(_num(offer.get("equity")) or 0)

def compare_offers(offers):
    return sorted([{**o,"total_comp":round(total_comp(o),2)} for o in normalize_offers(offers)],
                  key=lambda x:x["total_comp"],reverse=True)

def target_range(minimum,target,stretch):
    a,b,c=(_num(x) for x in (minimum,target,stretch))
    if any(x is None for x in (a,b,c)): raise ValueError("Compensation targets must be numeric.")
    if not a<=b<=c: raise ValueError("Expected minimum <= target <= stretch.")
    return {"minimum":a,"target":b,"stretch":c}

def negotiation_position(current,target,offer):
    c,t,o=(_num(x) for x in (current,target,offer))
    if None in (c,t,o): raise ValueError("Current, target and offer must be numeric.")
    return {"current":c,"target":t,"offer":o,"change_vs_current_pct":round(100*(o-c)/max(abs(c),1),1),
            "gap_to_target":round(t-o,2),"target_met":o>=t}

def script_points(role,strengths,target,floor=None):
    p=[f"Thank you for the offer for the {role} position.",
       "I am excited about the opportunity and the responsibilities.",
       f"Based on my documented experience and strengths, I am targeting compensation around {target}.",
       "I would be happy to discuss the complete compensation package and scope."]
    if strengths: p.insert(2,"Relevant strengths: "+", ".join(map(str,strengths[:5]))+".")
    if floor is not None: p.append("Keep the minimum acceptable figure private unless disclosure is strategically necessary.")
    return p

def package_score(offer,weights=None):
    w=weights or {"base":.55,"bonus":.2,"equity":.15,"benefits":.1}
    return round((_num(offer.get("base")) or 0)*w["base"]+(_num(offer.get("bonus")) or 0)*w["bonus"]+
                 (_num(offer.get("equity")) or 0)*w["equity"]+(_num(offer.get("benefits_value")) or 0)*w["benefits"],2)

def market_summary(records):
    v=[_num(x.get("salary")) for x in records or []]; v=[x for x in v if x is not None]
    return {"count":len(v),"median":median(v) if v else None,"min":min(v) if v else None,
            "max":max(v) if v else None,"source":"user-supplied"}
