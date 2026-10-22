from nema_agora.evidence_pack import build_demo_evidence_pack


def test_demo_evidence_pack_runs_full_advisory_chain():
    pack = build_demo_evidence_pack(git_revision="abc123")
    assert len(pack["records"]) == 5
    assert pack["safety"]["persistent_state_written"] is False
    assert all(item["analysis"]["human_review_required"] is True for item in pack["records"])


def test_demo_evidence_pack_is_deterministic_for_fixed_inputs():
    first = build_demo_evidence_pack(git_revision="abc123")
    second = build_demo_evidence_pack(git_revision="abc123")
    assert first["evidence_fingerprint"] == second["evidence_fingerprint"]


def test_demo_evidence_pack_requires_explicit_revision():
    try:
        build_demo_evidence_pack(git_revision="")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected explicit Git revision to be required")
