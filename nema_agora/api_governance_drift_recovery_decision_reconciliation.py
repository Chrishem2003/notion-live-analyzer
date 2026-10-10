"""Phase 114 — read-only reconciliation of recovery authorization evidence."""
from __future__ import annotations
from collections import Counter
from typing import Any, Mapping, Sequence
from .api_audit_binding import fingerprint
from .api_governance_drift_recovery_decision_ledger import POLICY_VERSION as DECISION_POLICY, validate_decision
from .api_governance_drift_recovery_review_lifecycle import POLICY_VERSION as LIFECYCLE_POLICY, validate_lifecycle
POLICY_VERSION="phase114-v1"
def reconcile_recovery_decisions(lifecycles:Sequence[Mapping[str,Any]], decisions:Sequence[Mapping[str,Any]], *, expected_ledger_count:int|None=None)->dict[str,Any]:
    if not isinstance(lifecycles,Sequence) or isinstance(lifecycles,(str,bytes)): raise ValueError("INVALID_LIFECYCLES")
    if not isinstance(decisions,Sequence) or isinstance(decisions,(str,bytes)): raise ValueError("INVALID_DECISIONS")
    if expected_ledger_count is not None and (not isinstance(expected_ledger_count,int) or isinstance(expected_ledger_count,bool) or expected_ledger_count<0): raise ValueError("INVALID_EXPECTED_LEDGER_COUNT")
    ls,ds=[],[]; findings=[]
    for i,x in enumerate(lifecycles):
        try: ls.append(validate_lifecycle(x))
        except ValueError as exc: findings.append({"code":"INVALID_LIFECYCLE","index":i,"reason":str(exc)})
    for i,x in enumerate(decisions):
        try: ds.append(validate_decision(x))
        except ValueError as exc: findings.append({"code":"INVALID_DECISION","index":i,"reason":str(exc)})
    lfps=[x["lifecycle_fingerprint"] for x in ls]; dids=[x["decision_id"] for x in ds]; dfps=[x["decision_fingerprint"] for x in ds]
    for key,vals,code in (("lifecycle_fingerprint",lfps,"DUPLICATE_LIFECYCLE"),("decision_id",dids,"DUPLICATE_DECISION_ID"),("decision_fingerprint",dfps,"DUPLICATE_DECISION_FINGERPRINT")):
        for v,c in Counter(vals).items():
            if c>1: findings.append({"code":code,"identity":v})
    by_lfp={x["lifecycle_fingerprint"]:x for x in ls}
    bound={x["lifecycle_fingerprint"]:[] for x in ls}
    for x in ds: bound.setdefault(x["lifecycle_fingerprint"],[]).append(x)
    for fp,l in by_lfp.items():
        matches=bound.get(fp,[])
        if not matches: findings.append({"code":"UNAUTHORIZED_LIFECYCLE","lifecycle_fingerprint":fp}); continue
        if len(matches)>1: findings.append({"code":"MULTIPLE_DECISIONS_FOR_LIFECYCLE","lifecycle_fingerprint":fp})
        for d in matches:
            if d["review_audit_id"]!=l["review_audit_id"]: findings.append({"code":"REVIEW_BINDING_MISMATCH","lifecycle_fingerprint":fp})
            if d["monitor_fingerprint"]!=l["monitor_fingerprint"]: findings.append({"code":"MONITOR_BINDING_MISMATCH","lifecycle_fingerprint":fp})
            if d["policy_version"]!=DECISION_POLICY: findings.append({"code":"DECISION_POLICY_MISMATCH","lifecycle_fingerprint":fp})
            if d["human_authorized"] is not True or d["execution_permitted"] is not False or d["execution_performed"] is not False: findings.append({"code":"EXECUTION_GATE_VIOLATION","lifecycle_fingerprint":fp})
            if any(d.get(k) is not None for k in ("environmental_conclusion","regulatory_conclusion","enforcement_action")): findings.append({"code":"UNEXPECTED_GOVERNANCE_CONCLUSION_FIELD","lifecycle_fingerprint":fp})
            if d["decision"]=="AUTHORIZE_NO_ACTION" and l["lifecycle_state"]!="APPROVED_NO_ACTION": findings.append({"code":"NO_ACTION_LIFECYCLE_MISMATCH","lifecycle_fingerprint":fp})
            if d["decision"]=="AUTHORIZE_ESCALATION" and l["lifecycle_state"]!="ESCALATED": findings.append({"code":"ESCALATION_LIFECYCLE_MISMATCH","lifecycle_fingerprint":fp})
    for d in ds:
        if d["lifecycle_fingerprint"] not in by_lfp: findings.append({"code":"ORPHAN_DECISION","decision_id":d["decision_id"],"lifecycle_fingerprint":d["lifecycle_fingerprint"]})
    if expected_ledger_count is not None and expected_ledger_count!=len(decisions): findings.append({"code":"LEDGER_COUNT_MISMATCH","expected":expected_ledger_count,"observed":len(decisions)})
    findings.sort(key=lambda x:(x.get("code",""),str(x.get("index","")),str(x.get("lifecycle_fingerprint","")),str(x.get("decision_id","")),str(x.get("identity",""))))
    state="CONTROL_REQUIRED" if findings else "RECONCILED"
    payload={"policy_version":POLICY_VERSION,"lifecycle_policy_version":LIFECYCLE_POLICY,"decision_policy_version":DECISION_POLICY,"state":state,"lifecycle_count":len(lifecycles),"valid_lifecycle_count":len(ls),"decision_count":len(decisions),"valid_decision_count":len(ds),"expected_ledger_count":expected_ledger_count,"findings":findings,"read_only":True,"execution_gate_closed":True,"interpretation":"RECOVERY_DECISION_RECONCILIATION","environmental_conclusion":None,"regulatory_conclusion":None,"enforcement_action":None}
    return dict(payload,reconciliation_fingerprint=fingerprint(payload))
