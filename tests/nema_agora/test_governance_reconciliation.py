from nema_agora.audit_ledger import AuditLedger
from nema_agora.audit_events import AuditEventCapture
from nema_agora.governance_reconciliation import reconcile_decisions

def sources():
    return {"evaluation_completed":[{"run_id":"LAB-1","actor_id":"u1"}],"review_decision":[{"review_id":"REV-1","reviewer_id":"u2","decision":"CONFIRMED_USEFUL"}],"lifecycle_decision":[{"decision_id":"LIFE-1","decided_by":"u3","action":"RETAIN"}]}

def ledger(tmp_path):
    l=AuditLedger(tmp_path/"db.sqlite"); c=AuditEventCapture(l)
    for eid,typ,actor,aid,dec,module,reason,role in [("e1","EVALUATION_COMPLETED","u1","LAB-1","HUMAN_REVIEW_REQUIRED","evaluation","EVALUATION_COMPLETE","reviewer"),("e2","REVIEW_DECISION_RECORDED","u2","REV-1","APPROVE","review","HUMAN_REVIEW","reviewer"),("e3","MODEL_LIFECYCLE_DECIDED","u3","LIFE-1","APPROVE","model_governance","HUMAN_LIFECYCLE_DECISION","coordinator")]:
        c.record(event_id=eid,event_type=typ,actor_id=actor,payload={"artifact_id":aid,"status":"COMPLETED","decision":dec,"reason_code":reason,"source_module":module,"recorded_by_role":role,"policy_version":"phase38-v1"})
    return l

def test_clean(tmp_path):
    l=ledger(tmp_path); r=reconcile_decisions(sources(),l.list_entries(),ledger_verification=l.verify()); assert r["status"]=="TRACEABLE" and r["matched"]==3 and not r["exceptions"]

def test_missing_event(tmp_path):
    l=ledger(tmp_path); es=[e for e in l.list_entries() if e["payload"]["metadata"].get("artifact_id")!="REV-1"]; r=reconcile_decisions(sources(),es,ledger_verification={"valid":True}); assert r["status"]=="CONTROL_REQUIRED" and any(x["code"]=="MISSING_AUDIT_EVENT" for x in r["exceptions"])

def test_orphan_event(tmp_path):
    l=ledger(tmp_path); AuditEventCapture(l).record(event_id="orphan",event_type="REVIEW_DECISION_RECORDED",actor_id="u9",payload={"artifact_id":"REV-X","status":"COMPLETED","decision":"APPROVE","reason_code":"HUMAN_REVIEW","source_module":"review","recorded_by_role":"reviewer","policy_version":"phase38-v1"}); r=reconcile_decisions(sources(),l.list_entries(),ledger_verification=l.verify()); assert any(x["code"]=="ORPHAN_AUDIT_EVENT" for x in r["exceptions"])

def test_duplicate_source(tmp_path):
    l=ledger(tmp_path); s=sources(); s["review_decision"].append(dict(s["review_decision"][0])); r=reconcile_decisions(s,l.list_entries(),ledger_verification=l.verify()); assert any(x["code"]=="DUPLICATE_SOURCE_DECISION" for x in r["exceptions"])

def test_ambiguous_audit(tmp_path):
    l=ledger(tmp_path); AuditEventCapture(l).record(event_id="second",event_type="REVIEW_DECISION_RECORDED",actor_id="u2",payload={"artifact_id":"REV-1","status":"COMPLETED","decision":"APPROVE","reason_code":"HUMAN_REVIEW","source_module":"review","recorded_by_role":"reviewer","policy_version":"phase38-v1"}); r=reconcile_decisions(sources(),l.list_entries(),ledger_verification=l.verify()); assert any(x["code"]=="AMBIGUOUS_AUDIT_COVERAGE" for x in r["exceptions"])

def test_actor_mismatch(tmp_path):
    l=ledger(tmp_path); es=l.list_entries(); [e.update(actor_id="bad") for e in es if e["payload"]["metadata"].get("artifact_id")=="REV-1"]; r=reconcile_decisions(sources(),es,ledger_verification={"valid":True}); assert any(x["code"]=="ACTOR_MISMATCH" for x in r["exceptions"])

def test_decision_mismatch(tmp_path):
    l=ledger(tmp_path); es=l.list_entries(); [e["payload"]["metadata"].update(decision="REJECT") for e in es if e["payload"]["metadata"].get("artifact_id")=="REV-1"]; r=reconcile_decisions(sources(),es,ledger_verification={"valid":True}); assert any(x["code"]=="DECISION_METADATA_MISMATCH" for x in r["exceptions"])

def test_invalid_ledger(tmp_path):
    l=ledger(tmp_path); r=reconcile_decisions(sources(),l.list_entries(),ledger_verification={"valid":False}); assert r["status"]=="CONTROL_REQUIRED" and any(x["code"]=="INVALID_LEDGER" for x in r["exceptions"])

def test_deterministic_fingerprint(tmp_path):
    l=ledger(tmp_path); a=reconcile_decisions(sources(),l.list_entries(),ledger_verification={"valid":True}); b=reconcile_decisions(sources(),l.list_entries(),ledger_verification={"valid":True}); assert a["reconciliation_id"]==b["reconciliation_id"] and a["reconciliation_fingerprint"]==b["reconciliation_fingerprint"]

def test_no_auto_repair(tmp_path):
    l=ledger(tmp_path); before=len(l.list_entries()); r=reconcile_decisions({"evaluation_completed":sources()["evaluation_completed"]},l.list_entries(),ledger_verification={"valid":True}); assert len(l.list_entries())==before and r["status"]=="CONTROL_REQUIRED"
