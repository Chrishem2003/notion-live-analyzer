import pytest
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_registry_monitor import build_retention_registry_authorization_registry_monitor
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_review_phase134 import review_authorization_history_registry
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_review_reconciliation_phase135 import reconcile_authorization_history_registry_reviews
from nema_agora.api_governance_drift_recovery_authorization_retention_registry_lifecycle_phase136 import evaluate_authorization_history_registry_review_lifecycle,build_authorization_history_registry_review_lifecycle,validate_authorization_history_registry_lifecycle

def _review(outcome="REVIEW_AUTHORIZATION_HISTORY_REGISTRY"):
    m=build_retention_registry_authorization_registry_monitor([],expected_count=1,observed_at="2026-10-04T12:00:00+00:00")
    return review_authorization_history_registry(m,actor_id="reviewer",role="coordinator",outcome=outcome,reviewed_at="2026-10-04T12:01:00+00:00")

def test_mapping():
    assert evaluate_authorization_history_registry_review_lifecycle(_review(),evaluated_at="2026-10-04T12:02:00+00:00")["lifecycle_state"]=="DEFERRED"
    assert evaluate_authorization_history_registry_review_lifecycle(_review("PRESERVE_AND_ESCALATE"),evaluated_at="2026-10-04T12:02:00+00:00")["lifecycle_state"]=="ESCALATED"

def test_bundle_requires_reconciled():
    m=build_retention_registry_authorization_registry_monitor([],expected_count=1,observed_at="2026-10-04T12:00:00+00:00")
    review=_review()
    bad=reconcile_authorization_history_registry_reviews([m],[],expected_review_count=0)
    with pytest.raises(ValueError,match="RECONCILIATION_MUST_BE_RECONCILED"):
        build_authorization_history_registry_review_lifecycle(bad,[review],evaluated_at="2026-10-04T12:02:00+00:00")

def test_bundle_builds():
    m=build_retention_registry_authorization_registry_monitor([],expected_count=1,observed_at="2026-10-04T12:00:00+00:00")
    review=_review()
    rec=reconcile_authorization_history_registry_reviews([m],[review],expected_review_count=1)
    bundle=build_authorization_history_registry_review_lifecycle(rec,[review],evaluated_at="2026-10-04T12:02:00+00:00")
    assert bundle["lifecycle_count"]==1
    assert validate_authorization_history_registry_lifecycle(bundle["lifecycles"][0])==bundle["lifecycles"][0]

def test_tamper_rejected():
    lifecycle=evaluate_authorization_history_registry_review_lifecycle(_review(),evaluated_at="2026-10-04T12:02:00+00:00")
    lifecycle["execution_performed"]=True
    with pytest.raises(ValueError,match="AUTHORIZATION_HISTORY_REGISTRY_LIFECYCLE_FINGERPRINT_MISMATCH"):
        validate_authorization_history_registry_lifecycle(lifecycle)
