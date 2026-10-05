from nema_agora.api_governance_drift_recovery_review_ledger import review_recovery_recommendation
from nema_agora.api_audit_binding import fingerprint
from nema_agora.api_governance_drift_reconciliation_monitor import build_history_integrity_monitor
from nema_agora.api_governance_drift_recovery_review_lifecycle import evaluate_recovery_review
from nema_agora.api_governance_drift_recovery_decision_ledger import authorize_recovery_decision
from nema_agora.api_governance_drift_recovery_authorization_history import *
def decision():
 r=build_history_integrity_monitor([],expected_count=0,observed_at="2026-10-04T12:00:00+00:00"); r["state"]="MONITORING_CLEAR"; r["recovery_recommendation"]="NO_RECOVERY_ACTION"; r["recovery_required"]=False; r.pop("monitor_fingerprint",None); r["monitor_fingerprint"]=fingerprint(r); v=review_recovery_recommendation(r,actor_id="reviewer",role="coordinator",outcome="NO_ACTION_APPROVED",reviewed_at="2026-10-04T12:01:00+00:00"); l=evaluate_recovery_review(v,evaluated_at="2026-10-04T12:02:00+00:00"); return authorize_recovery_decision(l,actor_id="admin",role="admin",decision="AUTHORIZE_NO_ACTION",decided_at="2026-10-04T12:03:00+00:00")
def test_continuity_ready():
 s=build_authorization_continuity([decision()],captured_at="2026-10-04T12:04:00+00:00",sequence=1); assert reconcile_authorization_history([s])["state"]=="HISTORY_READY"
def test_gap(): 
 s=build_authorization_continuity([decision()],captured_at="2026-10-04T12:04:00+00:00",sequence=2); assert reconcile_authorization_history([s])["state"]=="CONTROL_REQUIRED"
