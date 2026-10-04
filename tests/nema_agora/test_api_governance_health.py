from nema_agora.api_governance_health import evaluate_health
def obs(n=1):
 return {"state":"READY_FOR_HUMAN_REVIEW","counts":{k:n for k in ("audit_events","reconciliations","lifecycles","decisions","cases","queued_reviews","human_reviews")}}
def test_complete():
 r=evaluate_health({**obs(), "counts":{**obs()["counts"],"review_reconciliation":1}});assert r["state"]=="HEALTHY"
def test_gap():
 r=evaluate_health({**obs(), "counts":{**obs()["counts"],"review_reconciliation":0}});assert r["state"]=="CONTROL_REQUIRED"
def test_upstream_control():
 r=evaluate_health({**obs(), "state":"CONTROL_REQUIRED","counts":{**obs()["counts"],"review_reconciliation":1}});assert r["state"]=="CONTROL_REQUIRED"
