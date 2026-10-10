import pytest
from nema_agora.core import CATEGORIES, make_observation
from nema_agora.quality import assess_observation
from nema_agora.governance import validate_governance, DEFAULT_SCOPE

def base(**overrides):
    x={"case_id":"NA-1","observation_date":"2026-10-04","category":CATEGORIES[0],"severity":"Moderate",
       "district_or_site":"Pilot A","description":"Visible waste near drainage channel",
       "latitude":2.5,"longitude":32.1,"status":"Under review","consent_confirmed":True}
    x.update(overrides); return x

def test_valid_record_passes():
    assert assess_observation(base()) == {"quality_status":"PASS","flags":["VALID"]}

def test_missing_consent_and_description_require_review():
    result=assess_observation(base(description="",consent_confirmed=False))
    assert result["quality_status"]=="REVIEW"
    assert "MISSING_DESCRIPTION" in result["flags"]
    assert "MISSING_CONSENT" in result["flags"]

def test_invalid_coordinates_are_flagged():
    result=assess_observation(base(latitude=200,longitude=32))
    assert "INVALID_COORDINATES" in result["flags"]

def test_received_record_needs_review():
    assert "NEEDS_REVIEW" in assess_observation(base(status="Received"))["flags"]

def test_near_duplicate_is_flagged():
    peer=base(case_id="NA-2")
    result=assess_observation(base(),peer_records=[peer])
    assert "DUPLICATE_SUSPECTED" in result["flags"]

def test_governance_baseline_is_valid():
    assert validate_governance(DEFAULT_SCOPE)==[]

@pytest.mark.parametrize("key",["allow_personal_data","allow_urgent_incidents","official_integration_enabled"])
def test_disallowed_governance_switch_is_rejected(key):
    policy=dict(DEFAULT_SCOPE); policy[key]=True
    assert validate_governance(policy)

def test_governance_requires_explicit_boolean_controls():
    policy=dict(DEFAULT_SCOPE); policy["required_consent"]="yes"
    assert any("required_consent" in e for e in validate_governance(policy))
