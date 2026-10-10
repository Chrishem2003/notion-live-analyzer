from nema_agora.api_governance_drift_recovery_review_lifecycle import *
from nema_agora.api_governance_drift_recovery_review_ledger import review_recovery_recommendation
from nema_agora.api_governance_drift_reconciliation_monitor import build_history_integrity_monitor
from nema_agora.api_governance_drift_recovery_review_reconciliation import reconcile_recovery_reviews
def report(): return build_history_integrity_monitor([],expected_count=0,observed_at="2026-10-04T12:00:00+00:00")
def review(outcome="BACKUP_REVIEWED"):
 return review_recovery_recommendation(report(),actor_id="reviewer",role="coordinator",outcome=outcome,reviewed_at="2026-10-04T12:01:00+00:00")
def test_lifecycle_states():
 r=report(); x=review(); assert evaluate_recovery_review(x,evaluated_at="2026-10-04T13:00:00+00:00")["lifecycle_state"]=="ACKNOWLEDGED"
 assert evaluate_recovery_review(review("RECOVERY_DEFERRED"),evaluated_at="2026-10-04T13:00:00+00:00")["lifecycle_state"]=="DEFERRED"
def test_snapshot_requires_reconciled():
 r=report(); x=review(); bad=reconcile_recovery_reviews([r],[],expected_ledger_count=0)
 try: build_recovery_review_lifecycle(bad,[x],evaluated_at="2026-10-04T13:00:00+00:00"); assert False
 except ValueError as e: assert str(e)=="RECONCILIATION_REQUIRED"
def test_validation_detects_tamper():
 x=evaluate_recovery_review(review(),evaluated_at="2026-10-04T13:00:00+00:00"); x["decision_executed"]=True
 try: validate_lifecycle(x); assert False
 except ValueError: pass
