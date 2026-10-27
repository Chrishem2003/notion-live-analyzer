"""Phase 127 reconciliation tests."""
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_monitor import build_retention_authorization_registry_monitor
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_review import review_retention_registry
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_reconciliation import reconcile_retention_registry_reviews, validate_retention_registry_review_reconciliation
import pytest
from nema_agora.api_audit_binding import fingerprint

def monitor(): return build_retention_authorization_registry_monitor([], expected_count=0, observed_at="2026-10-04T13:00:00+00:00")
def review(m): return review_retention_registry(m, actor_id="reviewer-1", role="coordinator", outcome="REVIEW_RETENTION_REGISTRY", reviewed_at="2026-10-04T13:01:00+00:00")

def test_reconciled():
    m=monitor(); r=review(m); result=reconcile_retention_registry_reviews([m],[r],expected_review_count=1)
    assert result["state"]=="RECONCILED"; validate_retention_registry_review_reconciliation(result)
def test_unreviewed():
    result=reconcile_retention_registry_reviews([monitor()],[])
    assert result["state"]=="CONTROL_REQUIRED" and any(x["code"]=="UNREVIEWED_MONITOR" for x in result["findings"])
def test_orphan():
    r=review(monitor()); orphan=dict(r,monitor_fingerprint="orphan"); orphan["review_fingerprint"]=fingerprint({k:v for k,v in orphan.items() if k!="review_fingerprint"})
    result=reconcile_retention_registry_reviews([], [orphan]); assert any(x["code"]=="ORPHAN_REVIEW" for x in result["findings"])
def test_multiple_reviews():
    m=monitor(); r=review(m); r2=dict(r,reviewed_at="2026-10-04T13:02:00+00:00"); r2["review_fingerprint"]=fingerprint({k:v for k,v in r2.items() if k!="review_fingerprint"})
    result=reconcile_retention_registry_reviews([m],[r,r2]); assert any(x["code"]=="MULTIPLE_REVIEWS_FOR_MONITOR" for x in result["findings"])
def test_binding_mismatch():
    m=monitor(); r=review(m); r2=dict(r,monitor_state="CONTROL_REQUIRED"); r2["review_fingerprint"]=fingerprint({k:v for k,v in r2.items() if k!="review_fingerprint"})
    result=reconcile_retention_registry_reviews([m],[r2]); assert any(x["code"]=="MONITOR_STATE_MISMATCH" for x in result["findings"])
def test_count_mismatch():
    m=monitor(); r=review(m); result=reconcile_retention_registry_reviews([m],[r],expected_review_count=2)
    assert any(x["code"]=="REVIEW_COUNT_MISMATCH" for x in result["findings"])
def test_invalid_review_execution():
    m=monitor(); r=review(m); bad=dict(r,execution_performed=True); bad["review_fingerprint"]=fingerprint({k:v for k,v in bad.items() if k!="review_fingerprint"})
    result=reconcile_retention_registry_reviews([m],[bad]); assert any(x["code"]=="INVALID_REVIEW" for x in result["findings"])
