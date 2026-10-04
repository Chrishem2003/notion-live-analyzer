"""Phase 62 — NEMA-AGORA transparent spatial-change evidence scoring."""
from __future__ import annotations
import hashlib,json,math,re
from typing import Any,Mapping
POLICY_VERSION="phase62-v1"
_ID_RE=re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
def fingerprint(value:Any)->str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()).hexdigest()
def _finite(v:Any)->bool:return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(float(v))
def _id(v:Any)->bool:return isinstance(v,str) and bool(_ID_RE.fullmatch(v))
def _bounded(v:Any,lo:float,hi:float)->bool:return _finite(v) and lo<=float(v)<=hi
def validate_scoring_policy(*,ndvi_weight:Any=0.5,ndwi_weight:Any=0.5,quality_weight:Any=0.0,uncertainty_weight:Any=0.0,review_threshold:Any=0.5)->dict[str,Any]:
    findings=[]
    for code,v in (("INVALID_NDVI_WEIGHT",ndvi_weight),("INVALID_NDWI_WEIGHT",ndwi_weight),("INVALID_QUALITY_WEIGHT",quality_weight),("INVALID_UNCERTAINTY_WEIGHT",uncertainty_weight)):
        if not _bounded(v,0,1):findings.append({"code":code})
    if not _bounded(review_threshold,0,1):findings.append({"code":"INVALID_REVIEW_THRESHOLD"})
    total=sum(float(v) for v in (ndvi_weight,ndwi_weight,quality_weight,uncertainty_weight) if _finite(v))
    if total<=0:findings.append({"code":"SCORING_WEIGHTS_SUM_TO_ZERO"})
    return {"policy_version":POLICY_VERSION,"state":"CONTROL_REQUIRED" if findings else "VALID","findings":findings}
def score_candidate(*,candidate:Mapping[str,Any],review_threshold:float=0.5,ndvi_weight:float=0.5,ndwi_weight:float=0.5,quality_weight:float=0.0,uncertainty_weight:float=0.0)->dict[str,Any]:
    if not isinstance(candidate,Mapping):return {"policy_version":POLICY_VERSION,"state":"CONTROL_REQUIRED","findings":[{"code":"INVALID_CANDIDATE"}]}
    findings=[]
    if candidate.get("state")!="CANDIDATE_CHANGE_DETECTED":findings.append({"code":"CANDIDATE_NOT_DETECTED"})
    if not _id(candidate.get("candidate_id")):findings.append({"code":"INVALID_CANDIDATE_ID"})
    for k in ("spatial","change","quality","uncertainty"):
        if k not in candidate:findings.append({"code":f"MISSING_CANDIDATE_FIELD_{k.upper()}"})
    policy=validate_scoring_policy(ndvi_weight=ndvi_weight,ndwi_weight=ndwi_weight,quality_weight=quality_weight,uncertainty_weight=uncertainty_weight,review_threshold=review_threshold)
    findings+=policy["findings"]
    if findings:return {"policy_version":POLICY_VERSION,"state":"CONTROL_REQUIRED","findings":findings}
    ndvi=float(candidate["change"]["NDVI"]["absolute_delta"]);ndwi=float(candidate["change"]["NDWI_MCFEETERS"]["absolute_delta"])
    nu=float(candidate["uncertainty"].get("ndvi_uncertainty",0));wu=float(candidate["uncertainty"].get("ndwi_uncertainty",0))
    if not _finite(ndvi) or not _finite(ndwi):return {"policy_version":POLICY_VERSION,"state":"CONTROL_REQUIRED","findings":[{"code":"INVALID_CHANGE_MAGNITUDE"}]}
    # Magnitude components are bounded engineering indicators, not probabilities.
    magnitude_ndvi=min(1.0,ndvi);magnitude_ndwi=min(1.0,ndwi)
    quality=candidate["quality"]
    cloud=max(float(quality.get("baseline_cloud_cover_pct",100)),float(quality.get("comparison_cloud_cover_pct",100)))
    valid=min(float(quality.get("baseline_valid_fraction",0)),float(quality.get("comparison_valid_fraction",0)))
    quality_component=max(0.0,min(1.0,(1.0-cloud/100.0)*valid))
    uncertainty_component=max(0.0,min(1.0,1.0-(nu+wu)/2.0))
    weights=[float(ndvi_weight),float(ndwi_weight),float(quality_weight),float(uncertainty_weight)]
    total=sum(weights)
    score=(magnitude_ndvi*weights[0]+magnitude_ndwi*weights[1]+quality_component*weights[2]+uncertainty_component*weights[3])/total
    tier="HIGH" if score>=0.75 else "MEDIUM" if score>=0.5 else "LOW"
    payload={"policy_version":POLICY_VERSION,"state":"REVIEW_PRIORITY_ASSIGNED","candidate_id":candidate["candidate_id"],"source_candidate_fingerprint":candidate.get("fingerprint"),"score":round(score,6),"tier":tier,"components":{"ndvi_magnitude":magnitude_ndvi,"ndwi_magnitude":magnitude_ndwi,"quality":quality_component,"uncertainty":uncertainty_component},"weights":{"ndvi":float(ndvi_weight),"ndwi":float(ndwi_weight),"quality":float(quality_weight),"uncertainty":float(uncertainty_weight)},"review_threshold":float(review_threshold),"reason_codes":list(candidate.get("reason_codes",[])),"interpretation":{"status":"HUMAN_REVIEW_REQUIRED" if score>=float(review_threshold) else "LOWER_PRIORITY_REVIEW","environmental_conclusion":None,"regulatory_conclusion":None,"violation":None,"enforcement_action":None}}
    payload["fingerprint"]=fingerprint(payload)
    return payload
