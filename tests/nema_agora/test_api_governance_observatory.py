from nema_agora.api_governance_observatory import build_observatory
def test_ready():
 r=build_observatory(events=[{}],reconciliations=[{"state":"RECONCILED"}],lifecycles=[{}],decisions=[{}],cases=[{}],queue_items=[{}],reviews=[{}],review_reconciliation={"state":"RECONCILED"})
 assert r["state"]=="READY_FOR_HUMAN_REVIEW" and r["counts"]["audit_events"]==1
def test_control():
 r=build_observatory(events=[],reconciliations=[{"state":"CONTROL_REQUIRED"}],lifecycles=[],decisions=[],cases=[],queue_items=[],reviews=[],review_reconciliation={"state":"RECONCILED"})
 assert r["state"]=="CONTROL_REQUIRED"
