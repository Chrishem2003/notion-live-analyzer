import tempfile
from pathlib import Path
from nema_agora.spatial_evidence_sqlite_repository import SQLiteSpatialEvidenceRepository
def rec():
    return {"record_id":"REC-1","case_id":"CASE-1","candidate_id":"CHANGE-1","observed_at":"2026-10-01T00:00:00Z","sequence":1,"previous_record_fingerprint":None,"case_fingerprint":"a"*64,"spatial_identity":{"aoi_id":"AOI-1","grid_shape":[2,2]},"review_outcome":"CONFIRMED_CHANGE","provenance":{"queue_fingerprint":"b"*64,"audit_fingerprint":"c"*64,"reconciliation_fingerprint":"d"*64},"record_fingerprint":"e"*64,"policy_version":"phase67-v1"}
def test_append_and_list():
    with tempfile.TemporaryDirectory() as d:
        r=SQLiteSpatialEvidenceRepository(str(Path(d)/"evidence.db")); r.append(rec()); assert r.list(case_id="CASE-1")[0]["record_id"]=="REC-1"
def test_filters():
    with tempfile.TemporaryDirectory() as d:
        r=SQLiteSpatialEvidenceRepository(str(Path(d)/"evidence.db")); r.append(rec()); assert r.list(candidate_id="CHANGE-1"); assert not r.list(candidate_id="OTHER")
def test_duplicate_is_rejected():
    with tempfile.TemporaryDirectory() as d:
        r=SQLiteSpatialEvidenceRepository(str(Path(d)/"evidence.db")); r.append(rec())
        try: r.append(rec()); assert False
        except Exception: pass
