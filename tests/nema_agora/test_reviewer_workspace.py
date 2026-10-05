from nema_agora.evidence_case import EvidenceReference, build_evidence_case
from nema_agora.evidence_case_store import EvidenceCaseStore
from nema_agora.reviewer_workspace import ReviewerWorkspace


def test_reviewer_workspace_reconstructs_review_and_export_history(tmp_path):
    store = EvidenceCaseStore(tmp_path / "cases.db")
    case = build_evidence_case(
        case_id="c1",
        observation={"x": 1},
        evidence=[
            EvidenceReference(
                "e1", "photo", "pilot",
                "2026-10-04T12:00:00+00:00", "f" * 64
            )
        ],
        created_at="2026-10-04T12:01:00+00:00",
    )
    store.append(case)
    ws = ReviewerWorkspace(store)

    view = ws.inspect("c1")
    assert view["review_required"] is True
    assert view["execution_gate"] == "CLOSED"

    reviewed = ws.review(
        case,
        reviewer_id="r1",
        role="coordinator",
        decision="ACKNOWLEDGED",
        reviewed_at="2026-10-04T12:02:00+00:00",
    )
    assert reviewed.state == "REVIEWED"
    assert ws.inspect("c1")["state"] == "REVIEWED"

    exported = ws.export_ready(
        reviewed,
        actor_id="r1",
        role="coordinator",
        exported_at="2026-10-04T12:03:00+00:00",
    )
    assert exported.state == "EXPORTED"
    inspected = ws.inspect("c1")
    assert inspected["state"] == "EXPORTED"
    assert inspected["events"][1]["created_at"] == "2026-10-04T12:03:00+00:00"


def test_reviewer_rejects_stale_case(tmp_path):
    store = EvidenceCaseStore(tmp_path / "cases.db")
    case = build_evidence_case(
        case_id="c2",
        observation={"x": 2},
        evidence=[
            EvidenceReference("e2", "note", "pilot", "2026-10-04T12:00:00+00:00", "f" * 64)
        ],
    )
    store.append(case)
    ws = ReviewerWorkspace(store)
    ws.review(case, reviewer_id="r1", role="reviewer", decision="ACKNOWLEDGED")
    try:
        ws.review(case, reviewer_id="r2", role="reviewer", decision="ACKNOWLEDGED")
    except ValueError as exc:
        assert "stale" in str(exc)
    else:
        raise AssertionError("stale case was accepted")
