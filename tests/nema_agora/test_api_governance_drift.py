from nema_agora.api_governance_snapshot import build_snapshot
from nema_agora.api_governance_drift import detect_drift
def snap(n):
 o={"state":"READY_FOR_HUMAN_REVIEW","counts":{"audit_events":n},"control_required_sources":0};h={"state":"HEALTHY","coverage_state":"COMPLETE","finding_count":0}
 return build_snapshot(observatory=o,health=h,captured_at=f"2026-10-04T12:0{n}:00+00:00")
def test_no_drift(): assert detect_drift(baseline=snap(1),current=snap(1))["state"]=="NO_DRIFT"
def test_drift_triggers_review(): r=detect_drift(baseline=snap(1),current=snap(2));assert r["state"]=="REVIEW_TRIGGERED" and r["review_required"]
def test_control_is_high(): a=snap(1);b=snap(2);b["health_state"]="CONTROL_REQUIRED";r=detect_drift(baseline=a,current=b);assert r["severity"]=="HIGH"
