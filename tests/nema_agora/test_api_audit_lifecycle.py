from nema_agora.api_audit_lifecycle import evaluate_lifecycle
def e(): return {"state":"RECORDED","event_id":"API-AUDIT-1","request_id":"REQ-91","occurred_at":"2026-10-04T12:00:00+00:00"}
def r(): return {"state":"RECONCILED","reconciliation_fingerprint":"a"*64}
def test_retained(): assert evaluate_lifecycle(e(),r(),now="2026-10-05T12:00:00+00:00",retention_days=365)["state"]=="RETAINED"
def test_expired(): assert evaluate_lifecycle(e(),r(),now="2028-01-01T12:00:00+00:00",retention_days=365)["state"]=="EXPIRED"
def test_requires_reconciliation(): assert evaluate_lifecycle(e(),{"state":"CONTROL_REQUIRED"},now="2026-10-05T12:00:00+00:00")["state"]=="CONTROL_REQUIRED"
