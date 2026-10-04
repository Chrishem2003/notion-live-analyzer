"""Phase 115 — governed continuity history for recovery authorizations."""
from __future__ import annotations
from collections import Counter
from typing import Any, Mapping, Sequence
from .api_audit_binding import fingerprint
from .api_governance_drift_recovery_decision_ledger import validate_decision
POLICY_VERSION="phase115-v1"
def build_authorization_continuity(decisions:Sequence[Mapping[str,Any]], *, captured_at:str, sequence:int, previous_snapshot_fingerprint:str|None=None)->dict[str,Any]:
    if not isinstance(decisions,Sequence) or isinstance(decisions,(str,bytes)): raise ValueError("INVALID_DECISIONS")
    if not isinstance(sequence,int) or isinstance(sequence,bool) or sequence<1: raise ValueError("INVALID_SEQUENCE")
    if not isinstance(captured_at,str) or not captured_at.strip(): raise ValueError("CAPTURE_TIME_REQUIRED")
    valid=[]
    for x in decisions: valid.append(validate_decision(x))
    ids=[x["decision_id"] for x in valid]; fps=[x["decision_fingerprint"] for x in valid]
    if len(ids)!=len(set(ids)) or len(fps)!=len(set(fps)): raise ValueError("DUPLICATE_DECISION_IDENTITY")
    payload={"policy_version":POLICY_VERSION,"captured_at":captured_at,"sequence":sequence,"previous_snapshot_fingerprint":previous_snapshot_fingerprint,"decision_count":len(valid),"decisions":valid,"human_governed":True,"execution_gate_closed":True,"interpretation":"GOVERNED_AUTHORIZATION_CONTINUITY","environmental_conclusion":None,"regulatory_conclusion":None,"enforcement_action":None}
    return dict(payload,snapshot_fingerprint=fingerprint(payload))
def validate_authorization_snapshot(snapshot:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(snapshot,Mapping): raise ValueError("INVALID_SNAPSHOT")
    required=("policy_version","captured_at","sequence","previous_snapshot_fingerprint","decision_count","decisions","human_governed","execution_gate_closed","snapshot_fingerprint")
    if any(k not in snapshot for k in required): raise ValueError("SNAPSHOT_FIELDS_REQUIRED")
    if snapshot["policy_version"]!=POLICY_VERSION or snapshot["human_governed"] is not True or snapshot["execution_gate_closed"] is not True: raise ValueError("SNAPSHOT_CONTROL_VIOLATION")
    if snapshot["decision_count"]!=len(snapshot["decisions"]): raise ValueError("SNAPSHOT_COUNT_MISMATCH")
    for x in snapshot["decisions"]: validate_decision(x)
    payload={k:snapshot[k] for k in required if k!="snapshot_fingerprint"}
    if fingerprint(payload)!=snapshot["snapshot_fingerprint"]: raise ValueError("SNAPSHOT_FINGERPRINT_MISMATCH")
    return dict(snapshot)
def reconcile_authorization_history(snapshots:Sequence[Mapping[str,Any]])->dict[str,Any]:
    if not isinstance(snapshots,Sequence) or isinstance(snapshots,(str,bytes)): raise ValueError("INVALID_SNAPSHOTS")
    findings=[]; valid=[]
    for i,x in enumerate(snapshots):
        try: valid.append(validate_authorization_snapshot(x))
        except ValueError as exc: findings.append({"code":"INVALID_SNAPSHOT","index":i,"reason":str(exc)})
    sequences=[x["sequence"] for x in valid]; fps=[x["snapshot_fingerprint"] for x in valid]
    for v,c in Counter(sequences).items():
        if c>1: findings.append({"code":"DUPLICATE_SEQUENCE","sequence":v})
    for v,c in Counter(fps).items():
        if c>1: findings.append({"code":"DUPLICATE_SNAPSHOT","fingerprint":v})
    ordered=sorted(valid,key=lambda x:x["sequence"])
    for i,x in enumerate(ordered):
        if i==0:
            if x["sequence"]!=1: findings.append({"code":"HISTORY_MUST_START_AT_ONE","sequence":x["sequence"]})
            if x["previous_snapshot_fingerprint"] is not None: findings.append({"code":"UNEXPECTED_FIRST_PREDECESSOR","sequence":x["sequence"]})
        else:
            prev=ordered[i-1]
            if x["sequence"]!=prev["sequence"]+1: findings.append({"code":"SEQUENCE_GAP","previous":prev["sequence"],"observed":x["sequence"]})
            if x["previous_snapshot_fingerprint"]!=prev["snapshot_fingerprint"]: findings.append({"code":"PREDECESSOR_MISMATCH","sequence":x["sequence"]})
        if any(d["execution_permitted"] is not False or d["execution_performed"] is not False for d in x["decisions"]): findings.append({"code":"EXECUTION_GATE_VIOLATION","sequence":x["sequence"]})
    findings.sort(key=lambda z:(z.get("code",""),str(z.get("index","")),str(z.get("sequence",""))))
    payload={"policy_version":POLICY_VERSION,"state":"CONTROL_REQUIRED" if findings else ("HISTORY_READY" if valid else "NO_HISTORY"),"snapshot_count":len(snapshots),"valid_snapshot_count":len(valid),"findings":findings,"read_only":True,"execution_gate_closed":True,"interpretation":"GOVERNED_AUTHORIZATION_HISTORY_RECONCILIATION","environmental_conclusion":None,"regulatory_conclusion":None,"enforcement_action":None}
    return dict(payload,reconciliation_fingerprint=fingerprint(payload))
