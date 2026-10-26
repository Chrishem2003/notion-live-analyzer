import os,tempfile
from nema_agora.api_audit_lifecycle_decision import validate_decision,LifecycleDecisionRegistry
def base():
 e={"event_id":"API-AUDIT-1","request_id":"REQ-92"}
 r={"state":"RECONCILED","reconciliation_fingerprint":"a"*64}
 l={"event_id":"API-AUDIT-1","reconciliation_fingerprint":"a"*64,"lifecycle_fingerprint":"b"*64}
 return e,r,l
def test_human_decision_and_append_only():
 e,r,l=base();d=validate_decision(event=e,reconciliation=r,lifecycle=l,decision="RETAIN",actor_id="ACTOR-1",role="coordinator")
 assert d["state"]=="DECISION_RECORDED"
 with tempfile.TemporaryDirectory() as x:
  reg=LifecycleDecisionRegistry(os.path.join(x,"d.db"));reg.append(d);assert len(reg.list("API-AUDIT-1"))==1
def test_requires_reconciled_snapshot():
 e,r,l=base();r["state"]="CONTROL_REQUIRED"
 assert validate_decision(event=e,reconciliation=r,lifecycle=l,decision="RETAIN",actor_id="ACTOR-1",role="coordinator")["state"]=="CONTROL_REQUIRED"
def test_rejects_snapshot_mismatch():
 e,r,l=base();l["reconciliation_fingerprint"]="c"*64
 assert validate_decision(event=e,reconciliation=r,lifecycle=l,decision="RETAIN",actor_id="ACTOR-1",role="coordinator")["state"]=="CONTROL_REQUIRED"
