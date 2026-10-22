"""Phase 65 tests — spatial review reconciliation and evidence integrity."""
from nema_agora.spatial_review_reconciliation import reconcile_spatial_reviews

def queue_item(fp="a"*64, state="QUEUED", candidate="CHANGE-001"):
    return {"review_item_id":"REVIEW-001","candidate_id":candidate,"record_fingerprint":fp,"queue_state":state}

def audit(fp="a"*64, candidate="CHANGE-001", item="REVIEW-001"):
    return {"review_event_id":"SPATIAL-REVIEW-001","review_item_id":item,"candidate_id":candidate,"source_queue_fingerprint":fp}

def test_reconciled_pair():
    result=reconcile_spatial_reviews([queue_item()],[audit()])
    assert result["state"]=="RECONCILED"
    assert result["summary"]["missing_reviews"]==0

def test_missing_review_is_control_required():
    result=reconcile_spatial_reviews([queue_item()],[])
    assert result["state"]=="CONTROL_REQUIRED"
    assert any(x["code"]=="MISSING_REVIEW" for x in result["findings"])

def test_orphan_review_is_control_required():
    result=reconcile_spatial_reviews([], [audit()])
    assert result["state"]=="CONTROL_REQUIRED"
    assert any(x["code"]=="ORPHAN_REVIEW" for x in result["findings"])

def test_duplicate_review_is_detected():
    result=reconcile_spatial_reviews([queue_item()],[audit(),dict(audit(),review_event_id="SPATIAL-REVIEW-002")])
    assert result["summary"]["duplicate_reviews"]==1

def test_fingerprint_mismatch_is_detected():
    result=reconcile_spatial_reviews([queue_item(fp="a"*64)],[audit(fp="b"*64)])
    assert result["summary"]["fingerprint_mismatches"]==1

def test_stale_queue_item_is_detected():
    result=reconcile_spatial_reviews([queue_item(state="REVIEWED")],[audit()])
    assert result["summary"]["stale_reviews"]==1

def test_identity_mismatch_is_detected():
    result=reconcile_spatial_reviews([queue_item(candidate="CHANGE-001")],[audit(candidate="CHANGE-999")])
    assert result["summary"]["identity_mismatches"]==1

def test_malformed_input_fails_closed():
    result=reconcile_spatial_reviews("bad", [])
    assert result["state"]=="CONTROL_REQUIRED"

def test_deterministic_result_and_non_regulatory_output():
    a=reconcile_spatial_reviews([queue_item()],[audit()])
    b=reconcile_spatial_reviews([queue_item()],[audit()])
    assert a["reconciliation_fingerprint"]==b["reconciliation_fingerprint"]
    for key in ("environmental_conclusion","regulatory_conclusion","violation","enforcement_action"):
        assert a["interpretation"][key] is None
