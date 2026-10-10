from nema_agora.spatial_evidence_storage import *
def r(i=1):
 return {"record_id":f"SPATIAL-HISTORY-{i:03d}","case_id":"SPATIAL-CASE-001","candidate_id":"CHANGE-001","observed_at":"2026-10-0%dT10:00:00+00:00"%i,"sequence":i,"previous_record_fingerprint":None,"case_fingerprint":"a"*64,"spatial_identity":{"aoi_id":"AOI-01","grid_id":"GRID-10M"},"review_outcome":"CONFIRMED_CHANGE","provenance":{"queue_fingerprint":"b"*64},"record_fingerprint":("%064x"%i),"policy_version":"phase67-v1"}
def test_append_and_query(tmp_path):
 s=SpatialEvidenceStore(str(tmp_path/"x.db"));assert s.append(r())["state"]=="STORED";assert len(s.list(case_id="SPATIAL-CASE-001"))==1
def test_duplicate_rejected(tmp_path):
 s=SpatialEvidenceStore(str(tmp_path/"x.db"));s.append(r())
 try:s.append(r());assert False
 except ValueError as e:assert str(e)=="EVIDENCE_RECORD_CONFLICT"
def test_update_delete_immutable(tmp_path):
 s=SpatialEvidenceStore(str(tmp_path/"x.db"));s.append(r())
 import sqlite3
 with sqlite3.connect(s.database_path) as db:
  try:db.execute("UPDATE spatial_evidence_history SET candidate_id='X'");assert False
  except sqlite3.DatabaseError:pass
def test_invalid_record_fails_closed(tmp_path):
 s=SpatialEvidenceStore(str(tmp_path/"x.db"));assert s.append({})["state"]=="CONTROL_REQUIRED"
