"""Stage 47 Build 2 evidence-intake tests."""

from sovereign_intelligence.research.intake import (
    EvidenceIntakeEngine,
    IntakeRequest,
    TextEvidenceAdapter,
)


def test_text_adapter_accepts_real_text():
    adapter = TextEvidenceAdapter()

    request = IntakeRequest(
        source_id="doc-001",
        source="local-document",
        source_type="document",
        title="Research Document",
        content="This is actual source material.",
        location="documents/research.txt",
    )

    record = adapter.intake(request)

    assert record is not None
    assert record.source_id == "doc-001"
    assert record.content == "This is actual source material."
    assert record.location == "documents/research.txt"


def test_text_adapter_rejects_empty_content():
    adapter = TextEvidenceAdapter()

    request = IntakeRequest(
        source_id="empty-001",
        source="local-document",
        source_type="document",
        title="Empty",
        content="   ",
    )

    assert adapter.intake(request) is None


def test_engine_intakes_multiple_records():
    engine = EvidenceIntakeEngine()

    requests = [
        IntakeRequest(
            source_id="doc-001",
            source="local",
            source_type="document",
            title="One",
            content="Evidence one.",
        ),
        IntakeRequest(
            source_id="doc-002",
            source="local",
            source_type="document",
            title="Two",
            content="Evidence two.",
        ),
    ]

    result = engine.intake_many(requests)

    assert result.accepted_count == 2
    assert result.rejected_count == 0
    assert result.metadata["requested_count"] == 2


def test_engine_records_rejected_empty_source():
    engine = EvidenceIntakeEngine()

    request = IntakeRequest(
        source_id="empty-001",
        source="local",
        source_type="document",
        title="Empty",
        content="",
    )

    result = engine.intake_many([request])

    assert result.accepted_count == 0
    assert result.rejected_count == 1
    assert result.rejected[0]["source_id"] == "empty-001"


def test_engine_supports_generator_requests():
    engine = EvidenceIntakeEngine()

    def requests():
        yield IntakeRequest(
            source_id="generator-001",
            source="local",
            source_type="document",
            title="Generator",
            content="Generator evidence.",
        )

    result = engine.intake_many(requests())

    assert result.accepted_count == 1
    assert result.metadata["requested_count"] == 1
