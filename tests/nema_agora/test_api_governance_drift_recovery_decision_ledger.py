import tempfile, pytest
from nema_agora.api_governance_drift_recovery_decision_ledger import *
from nema_agora.api_governance_drift_recovery_review_lifecycle import evaluate_recovery_review
from nema_agora.api_governance_drift_recovery_review_ledger import review_recovery_recommendation
from nema_agora.api_audit_binding import fingerprint
from nema_agora.api_governance_drift_reconciliation_monitor import build_history_integrity_monitor
def lifecycle(outcome="NO_ACTION_APPROVED"):
 r=build_history_integrity_monitor([],expected_count=0,observed_at="2026-10-04T12:00:00+00:00"); r["state"]="MONITORING_CLEAR"; r["recovery_recommendation"]="NO_RECOVERY_ACTION"; r["recovery_required"]=False; r.pop("monitor_fingerprint",None); r["monitor_fingerprint"]=fingerprint(r)
 v=review_recovery_recommendation(r,actor_id="reviewer",role="coordinator",outcome=outcome,reviewed_at="2026-10-04T12:01:00+00:00")
 return evaluate_recovery_review(v,evaluated_at="2026-10-04T12:02:00+00:00")
def test_no_action_requires_approved_lifecycle():
 x=authorize_recovery_decision(lifecycle(),actor_id="admin",role="admin",decision="AUTHORIZE_NO_ACTION",decided_at="2026-10-04T12:03:00+00:00")
 assert x["execution_permitted"] is False
def test_wrong_lifecycle_rejected():
 with pytest.raises(ValueError,match="NO_ACTION_REQUIRES_APPROVED_LIFECYCLE"):
  authorize_recovery_decision(lifecycle("RECOVERY_DEFERRED"),actor_id="admin",role="admin",decision="AUTHORIZE_NO_ACTION",decided_at="2026-10-04T12:03:00+00:00")
def test_append_only():
 x=authorize_recovery_decision(lifecycle(),actor_id="admin",role="admin",decision="AUTHORIZE_NO_ACTION",decided_at="2026-10-04T12:03:00+00:00")
 with tempfile.TemporaryDirectory() as d:
  led=RecoveryDecisionLedger(d+"/x.db"); led.append(x); assert led.count()==1; assert led.list()[0]["decision_id"]==x["decision_id"]
def test_tamper_rejected():
 x=authorize_recovery_decision(lifecycle(),actor_id="admin",role="admin",decision="AUTHORIZE_NO_ACTION",decided_at="2026-10-04T12:03:00+00:00"); x["execution_performed"]=True
 with pytest.raises(ValueError): validate_decision(x)
