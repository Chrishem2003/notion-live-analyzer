"""Phase 63 tests — persistent spatial-change review queue."""
from pathlib import Path
import sqlite3
import pytest
from nema_agora.spatial_change_review_queue import SpatialChangeReviewQueue, build_review_record, validate_scored_candidate

def scored():
    return {"state":"REVIEW_PRIORITY_ASSIGNED","candidate_id":"CHANGE-001","source_candidate_fingerprint":"a"*64,
            "score":0.82,"tier":"HIGH","components":{"ndvi_magnitude":0.8,"ndwi_magnitude":0.6,"quality":0.9,"uncertainty":0.96},
            "weights":{"ndvi":0.5,"ndwi":0.5,"quality":0.0,"uncertainty":0.0},"review_threshold":0.5,
            "reason_codes":["NDVI_CHANGE_THRESHOLD_MET","COMBINED_CHANGE_SIGNAL"],
            "spatial":{"aoi_id":"AOI-01","grid_id":"GRID-10M"}}

def test_valid_scored_candidate_and_deterministic_record():
    assert validate_scored_candidate(scored())["state"]=="VALID"
    a=build_review_record(scored(),created_at="2026-10-04T10:00:00+00:00")
    b=build_review_record(scored(),created_at="2026-10-04T10:00:00+00:00")
    assert a["review_item_id"].startswith("REVIEW-") and a["fingerprint"]==b["fingerprint"]
    assert a["queue_state"]=="QUEUED" and a["human_review_required"] is True

def test_invalid_scoring_fails_closed():
    bad=scored(); bad["state"]="CANDIDATE_CHANGE_DETECTED"
    assert build_review_record(bad)["state"]=="CONTROL_REQUIRED"

def test_invalid_fingerprint_and_score_fail_closed():
    bad=scored(); bad["source_candidate_fingerprint"]="not-a-hash"; bad["score"]=1.5
    assert validate_scored_candidate(bad)["state"]=="CONTROL_REQUIRED"

def test_persistent_append_only_queue(tmp_path: Path):
    q=SpatialChangeReviewQueue(str(tmp_path/"queue.sqlite"))
    row=q.enqueue(scored(),created_at="2026-10-04T10:00:00+00:00")
    assert q.list()[0]["review_item_id"]==row["review_item_id"] and q.counts()["total"]==1
    with pytest.raises(ValueError,match="REVIEW_ITEM_CONFLICT"): q.enqueue(scored(),created_at="2026-10-04T11:00:00+00:00")

def test_update_delete_are_blocked(tmp_path: Path):
    db=str(tmp_path/"queue.sqlite"); q=SpatialChangeReviewQueue(db); row=q.enqueue(scored())
    with sqlite3.connect(db) as conn:
        with pytest.raises(sqlite3.IntegrityError): conn.execute("UPDATE spatial_change_review_queue SET queue_state='REVIEWED' WHERE review_item_id=?",(row["review_item_id"],))
        with pytest.raises(sqlite3.IntegrityError): conn.execute("DELETE FROM spatial_change_review_queue WHERE review_item_id=?",(row["review_item_id"],))

def test_non_regulatory_output():
    row=build_review_record(scored())
    assert all(row["interpretation"][k] is None for k in ("environmental_conclusion","regulatory_conclusion","violation","enforcement_action"))
