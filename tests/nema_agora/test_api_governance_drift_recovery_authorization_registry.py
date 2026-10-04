import tempfile,pytest
from nema_agora.api_governance_drift_recovery_authorization_history import build_authorization_continuity
from nema_agora.api_governance_drift_recovery_review_ledger import review_recovery_recommendation
from nema_agora.api_governance_drift_reconciliation_monitor import build_history_integrity_monitor
from nema_agora.api_governance_drift_recovery_review_lifecycle import evaluate_recovery_review
from nema_agora.api_governance_drift_recovery_decision_ledger import authorize_recovery_decision
from nema_agora.api_governance_drift_recovery_authorization_registry import RecoveryAuthorizationHistoryRegistry
def d():
 r=build_history_integrity_monitor([],expected_count=0,observed_at="2026-10-04T12:00:00+00:00"); v=review_recovery_recommendation(r,actor_id="reviewer",role="coordinator",outcome="NO_ACTION_APPROVED",reviewed_at="2026-10-04T12:01:00+00:00"); l=evaluate_recovery_review(v,evaluated_at="2026-10-04T12:02:00+00:00"); return authorize_recovery_decision(l,actor_id="admin",role="admin",decision="AUTHORIZE_NO_ACTION",decided_at="2026-10-04T12:03:00+00:00")
def s(seq,prev=None): return build_authorization_continuity([d()],captured_at="2026-10-04T12:04:00+00:00",sequence=seq,previous_snapshot_fingerprint=prev)
def test_append_and_reconcile():
 with tempfile.TemporaryDirectory() as t:
  led=RecoveryAuthorizationHistoryRegistry(t+"/x.db"); a=s(1); led.append(a); assert led.count()==1; assert led.reconcile_history()["state"]=="HISTORY_READY"
def test_sequence_guard():
 with tempfile.TemporaryDirectory() as t:
  led=RecoveryAuthorizationHistoryRegistry(t+"/x.db"); led.append(s(1))
  with pytest.raises(ValueError,match="SNAPSHOT_SEQUENCE_NOT_NEXT"): led.append(s(3))
def test_update_delete_blocked():
 with tempfile.TemporaryDirectory() as t:
  led=RecoveryAuthorizationHistoryRegistry(t+"/x.db"); a=led.append(s(1))
  import sqlite3
  with sqlite3.connect(t+"/x.db") as db:
   with pytest.raises(sqlite3.IntegrityError): db.execute("DELETE FROM recovery_authorization_history")
