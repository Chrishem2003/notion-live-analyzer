from nema_agora.spatial_evidence_longitudinal import *
def case():
 return {"case_id":"SPATIAL-CASE-001","candidate_id":"CHANGE-001","case_fingerprint":"a"*64,"queue_artifact":{"spatial":{"aoi_id":"AOI-01","grid_id":"GRID-10M"}},"review_outcome":"CONFIRMED_CHANGE","provenance":{"queue_fingerprint":"b"*64,"audit_event_fingerprint":"c"*64,"reconciliation_fingerprint":"d"*64}}
def test_record_and_chain():
 a=build_longitudinal_record(case(),observed_at="2026-10-04T10:00:00+00:00",sequence=1)["record"];b=build_longitudinal_record(case(),observed_at="2026-10-05T10:00:00+00:00",sequence=2,previous_record_fingerprint=a["record_fingerprint"])["record"];assert build_timeline([a,b])["state"]=="TIMELINE_READY"
def test_bad_chain_fails_closed():
 a=build_longitudinal_record(case(),observed_at="2026-10-04T10:00:00+00:00",sequence=1)["record"];b=build_longitudinal_record(case(),observed_at="2026-10-05T10:00:00+00:00",sequence=2,previous_record_fingerprint="e"*64)["record"];assert build_timeline([a,b])["state"]=="CONTROL_REQUIRED"
def test_invalid_case_fails_closed():assert build_longitudinal_record({},observed_at="2026-10-04T10:00:00+00:00",sequence=1)["state"]=="CONTROL_REQUIRED"
def test_deterministic():
 a=build_longitudinal_record(case(),observed_at="2026-10-04T10:00:00+00:00",sequence=1)["record"];b=build_longitudinal_record(case(),observed_at="2026-10-04T10:00:00+00:00",sequence=1)["record"];assert a["record_fingerprint"]==b["record_fingerprint"]
def test_non_regulatory():
 r=build_longitudinal_record(case(),observed_at="2026-10-04T10:00:00+00:00",sequence=1)["record"];assert r["interpretation"]["environmental_conclusion"] is None and r["interpretation"]["regulatory_conclusion"] is None
