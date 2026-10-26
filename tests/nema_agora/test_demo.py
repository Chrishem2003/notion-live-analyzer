from nema_agora.demo import build_demo_dataset, validate_demo_dataset, serialise_demo_dataset

def test_demo_is_deterministic():
    a,b=build_demo_dataset(),build_demo_dataset()
    assert a.dataset_id==b.dataset_id
    assert a.records==b.records

def test_demo_is_session_safe():
    result=validate_demo_dataset(build_demo_dataset())
    assert result["valid"] is True
    assert result["synthetic"] is True
    assert result["persistent"] is False

def test_demo_serialisation_is_explicit():
    payload=serialise_demo_dataset(build_demo_dataset())
    assert "synthetic" in payload
    assert "not environmental truth" in payload
