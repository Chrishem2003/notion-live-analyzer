import tempfile
import pytest
from nema_agora.api_governance_snapshot import build_snapshot
from nema_agora.api_governance_drift import detect_drift
from nema_agora.api_governance_drift_registry import GovernanceDriftRegistry
def snapshot(n):
 observatory={"state":"READY_FOR_HUMAN_REVIEW","counts":{"audit_events":n},"control_required_sources":0}
 health={"state":"HEALTHY","coverage_state":"COMPLETE","finding_count":0}
 return build_snapshot(observatory=observatory,health=health,captured_at=f"2026-10-04T12:0{n}:00+00:00")
def event():
 return detect_drift(baseline=snapshot(1),current=snapshot(2))
def test_append_list():
 with tempfile.NamedTemporaryFile(suffix=".db") as f:
  r=GovernanceDriftRegistry(f.name);r.append(event());assert len(r.list())==1
def test_duplicate():
 with tempfile.NamedTemporaryFile(suffix=".db") as f:
  r=GovernanceDriftRegistry(f.name);r.append(event())
  try:r.append(event());assert False
  except ValueError as e:assert str(e)=="DRIFT_EVENT_CONFLICT"
def test_immutable():
 with tempfile.NamedTemporaryFile(suffix=".db") as f:
  r=GovernanceDriftRegistry(f.name);r.append(event())
  try:r.db.execute("DELETE FROM governance_drift_events");r.db.commit();assert False
  except Exception:pass

def test_tampered_drift_payload_is_rejected_before_persistence():
 with tempfile.NamedTemporaryFile(suffix=".db") as f:
  r=GovernanceDriftRegistry(f.name)
  d=event()
  d["changes"][0]["current"]="tampered"
  with pytest.raises(ValueError,match="DRIFT_FINGERPRINT_MISMATCH"):
   r.append(d)

def test_tampered_drift_identity_is_rejected_before_persistence():
 with tempfile.NamedTemporaryFile(suffix=".db") as f:
  r=GovernanceDriftRegistry(f.name)
  d=event()
  d["drift_id"]="API-DRIFT-FORGED"
  with pytest.raises(ValueError,match="DRIFT_ID_MISMATCH"):
   r.append(d)
