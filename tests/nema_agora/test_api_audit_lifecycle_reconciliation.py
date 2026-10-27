from nema_agora.api_audit_binding import fingerprint
from nema_agora.api_audit_lifecycle_reconciliation import reconcile_lifecycle_decisions
def data():
 e={"event_id":"API-1","request_id":"REQ-1"};r={"state":"RECONCILED","reconciliation_fingerprint":"a"*64};l={"event_id":"API-1","reconciliation_fingerprint":"a"*64,"lifecycle_fingerprint":"b"*64}
 p={"event_id":"API-1","request_id":"REQ-1","reconciliation_fingerprint":"a"*64,"lifecycle_fingerprint":"b"*64,"decision":"RETAIN","actor_id":"ACTOR-1","role":"coordinator"}
 d=dict(p,decision_id="DEC-1",decision_fingerprint=fingerprint(p))
 return e,r,l,d
def test_reconciled():
 e,r,l,d=data();x=reconcile_lifecycle_decisions(events=[e],reconciliations=[r],lifecycles=[l],decisions=[d]);assert x["state"]=="RECONCILED"
def test_orphan_control():
 e,r,l,d=data();d["lifecycle_fingerprint"]="c"*64;x=reconcile_lifecycle_decisions(events=[e],reconciliations=[r],lifecycles=[l],decisions=[d]);assert x["state"]=="CONTROL_REQUIRED"
def test_tamper_control():
 e,r,l,d=data();d["role"]="admin";x=reconcile_lifecycle_decisions(events=[e],reconciliations=[r],lifecycles=[l],decisions=[d]);assert x["state"]=="CONTROL_REQUIRED"
