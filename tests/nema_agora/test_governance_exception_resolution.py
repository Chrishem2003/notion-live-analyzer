from nema_agora.audit_ledger import AuditLedger
from nema_agora.governance_exception_resolution import GovernanceExceptionResolver

def test_resolution_appends_only(tmp_path):
    path=tmp_path/"db.sqlite"; ledger=AuditLedger(path)
    before=len(ledger.list_entries())
    r=GovernanceExceptionResolver(path).resolve(exception_code="MISSING_AUDIT_EVENT",decision_kind="review_decision",artifact_id="REV-1",actor_id="u1",role="reviewer",outcome="CORRECTED_AT_SOURCE",reason_code="SOURCE_RECHECKED",reconciliation_fingerprint="abc123")
    assert r["event_type"]=="GOVERNANCE_EXCEPTION_RESOLVED"
    assert len(ledger.list_entries())==before+1

def test_resolution_is_idempotent(tmp_path):
    path=tmp_path/"db.sqlite"; resolver=GovernanceExceptionResolver(path)
    args=dict(exception_code="ORPHAN_AUDIT_EVENT",decision_kind="review_decision",artifact_id="REV-X",actor_id="u1",role="coordinator",outcome="ACKNOWLEDGED",reason_code="INVESTIGATED",reconciliation_fingerprint="fp")
    a=resolver.resolve(**args); b=resolver.resolve(**args)
    assert a["entry_id"]==b["entry_id"]

def test_conflicting_resolution_fails_closed(tmp_path):
    path=tmp_path/"db.sqlite"; resolver=GovernanceExceptionResolver(path)
    args=dict(exception_code="ACTOR_MISMATCH",decision_kind="review_decision",artifact_id="REV-1",actor_id="u1",role="reviewer",outcome="ACKNOWLEDGED",reason_code="CHECKED",reconciliation_fingerprint="fp")
    resolver.resolve(**args)
    try: resolver.resolve(**{**args,"outcome":"ESCALATED"})
    except ValueError: pass
    else: assert False

def test_invalid_role_and_outcome(tmp_path):
    resolver=GovernanceExceptionResolver(tmp_path/"db.sqlite")
    args=dict(exception_code="MISSING_AUDIT_EVENT",decision_kind="review_decision",artifact_id="R",actor_id="u",reconciliation_fingerprint="fp")
    for extra in ({"role":"submitter","outcome":"ACKNOWLEDGED"},{"role":"reviewer","outcome":"BAD"}):
        try: resolver.resolve(**args,**extra,reason_code="x")
        except ValueError: pass
        else: assert False
