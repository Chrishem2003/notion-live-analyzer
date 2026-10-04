import tempfile,pytest
from nema_agora.api_governance_drift_recovery_decision_ledger import authorize_recovery_decision
from nema_agora.api_governance_drift_recovery_review_ledger import review_recovery_recommendation
from nema_agora.api_governance_drift_recovery_review_lifecycle import evaluate_recovery_review
from nema_agora.api_governance_drift_reconciliation_monitor import build_history_integrity_monitor
from nema_agora.api_governance_drift_recovery_decision_reconciliation import reconcile_recovery_decisions
def lc():
 r=build_history_integrity_monitor([],expected_count=0,observed_at="2026-10-04T12:00:00+00:00")
 v=review_recovery_recommendation(r,actor_id="reviewer",role="coordinator",outcome="NO_ACTION_APPROVED",reviewed_at="2026-10-04T12:01:00+00:00")
 return evaluate_recovery_review(v,evaluated_at="2026-10-04T12:02:00+00:00")
def dec(): return authorize_recovery_decision(lc(),actor_id="admin",role="admin",decision="AUTHORIZE_NO_ACTION",decided_at="2026-10-04T12:03:00+00:00")
def test_valid(): assert reconcile_recovery_decisions([lc()],[dec()],expected_ledger_count=1)["state"]=="RECONCILED"
def test_orphan(): x=dec(); assert reconcile_recovery_decisions([], [x])["state"]=="CONTROL_REQUIRED"
def test_tamper(): x=dec(); x["execution_permitted"]=True; assert reconcile_recovery_decisions([lc()],[x])["state"]=="CONTROL_REQUIRED"
def test_duplicate(): x=dec(); assert reconcile_recovery_decisions([lc(),lc()],[x])["state"]=="CONTROL_REQUIRED"
