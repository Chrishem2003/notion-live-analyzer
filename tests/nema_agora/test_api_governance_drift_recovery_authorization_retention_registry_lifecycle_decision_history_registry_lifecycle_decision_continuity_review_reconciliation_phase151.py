"""Tests for Phase 151 continuity review reconciliation."""
from __future__ import annotations
import pytest
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_phase147 import build_authorization_history_registry_decision_history_lifecycle_decision_continuity
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_monitor_phase149 import build_authorization_history_registry_decision_history_lifecycle_decision_continuity_monitor
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_review_phase150 import review_authorization_history_registry_decision_history_lifecycle_decision_continuity
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_decision_history_registry_lifecycle_decision_continuity_review_reconciliation_phase151 import reconcile_authorization_history_registry_decision_history_lifecycle_decision_continuity_reviews,validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_reconciliation
def healthy():
 s=build_authorization_history_registry_decision_history_lifecycle_decision_continuity([],captured_at="2026-10-04T09:00:00+00:00",sequence=1)
 return build_authorization_history_registry_decision_history_lifecycle_decision_continuity_monitor([s],expected_count=1,observed_at="2026-10-04T10:00:00+00:00")
def test_reconciled():
 m=healthy(); r=review_authorization_history_registry_decision_history_lifecycle_decision_continuity(m,actor_id="reviewer",role="coordinator",outcome="ACKNOWLEDGED",reviewed_at="2026-10-04T11:00:00+00:00")
 x=reconcile_authorization_history_registry_decision_history_lifecycle_decision_continuity_reviews([m],[r],expected_review_count=1)
 assert x["state"]=="RECONCILED"; assert x["findings"]==[]; assert validate_authorization_history_registry_decision_history_lifecycle_decision_continuity_review_reconciliation(x)==x
def test_unreviewed_monitor():
 x=reconcile_authorization_history_registry_decision_history_lifecycle_decision_continuity_reviews([healthy()],[])
 assert x["state"]=="CONTROL_REQUIRED"; assert any(f["code"]=="UNREVIEWED_MONITOR" for f in x["findings"])
def test_orphan_review():
 m=healthy(); r=review_authorization_history_registry_decision_history_lifecycle_decision_continuity(m,actor_id="reviewer",role="coordinator",outcome="ACKNOWLEDGED",reviewed_at="2026-10-04T11:00:00+00:00")
 r=dict(r,monitor_fingerprint="orphan"); r["review_fingerprint"]=__import__("nema_agora.api_audit_binding",fromlist=["fingerprint"]).fingerprint({k:v for k,v in r.items() if k!="review_fingerprint"})
 x=reconcile_authorization_history_registry_decision_history_lifecycle_decision_continuity_reviews([m],[r]); assert any(f["code"]=="ORPHAN_REVIEW" for f in x["findings"])
def test_multiple_reviews():
 m=healthy(); r=review_authorization_history_registry_decision_history_lifecycle_decision_continuity(m,actor_id="a",role="coordinator",outcome="ACKNOWLEDGED",reviewed_at="2026-10-04T11:00:00+00:00")
 r2=review_authorization_history_registry_decision_history_lifecycle_decision_continuity(m,actor_id="b",role="admin",outcome="ACKNOWLEDGED",reviewed_at="2026-10-04T11:01:00+00:00")
 x=reconcile_authorization_history_registry_decision_history_lifecycle_decision_continuity_reviews([m],[r,r2]); assert any(f["code"]=="MULTIPLE_REVIEWS_FOR_MONITOR" for f in x["findings"])
def test_count_mismatch():
 m=healthy(); r=review_authorization_history_registry_decision_history_lifecycle_decision_continuity(m,actor_id="a",role="coordinator",outcome="ACKNOWLEDGED",reviewed_at="2026-10-04T11:00:00+00:00")
 x=reconcile_authorization_history_registry_decision_history_lifecycle_decision_continuity_reviews([m],[r],expected_review_count=2); assert any(f["code"]=="REVIEW_COUNT_MISMATCH" for f in x["findings"])
def test_binding_mismatch():
 m=healthy(); r=review_authorization_history_registry_decision_history_lifecycle_decision_continuity(m,actor_id="a",role="coordinator",outcome="ACKNOWLEDGED",reviewed_at="2026-10-04T11:00:00+00:00")
 r=dict(r,monitor_state="NO_HISTORY"); r["review_fingerprint"]=__import__("nema_agora.api_audit_binding",fromlist=["fingerprint"]).fingerprint({k:v for k,v in r.items() if k!="review_fingerprint"})
 x=reconcile_authorization_history_registry_decision_history_lifecycle_decision_continuity_reviews([m],[r]); assert any(f["code"]=="MONITOR_STATE_MISMATCH" for f in x["findings"])
def test_execution_tamper_is_invalid():
 m=healthy(); r=review_authorization_history_registry_decision_history_lifecycle_decision_continuity(m,actor_id="a",role="coordinator",outcome="ACKNOWLEDGED",reviewed_at="2026-10-04T11:00:00+00:00")
 r=dict(r,execution_performed=True)
 x=reconcile_authorization_history_registry_decision_history_lifecycle_decision_continuity_reviews([m],[r]); assert any(f["code"]=="INVALID_REVIEW" for f in x["findings"])
