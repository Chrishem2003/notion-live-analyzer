from __future__ import annotations

from sovereign_intelligence.research.discovery.engine import (
    SourceDiscoveryEngine,
)
from sovereign_intelligence.research.discovery.registry import SourceRegistry
from sovereign_intelligence.research.discovery.sources import (
    ExistingSourceAdapter,
)
from sovereign_intelligence.research.pipeline.engine import (
    ResearchPipelineEngine,
)


def build_pipeline(sources):
    registry = SourceRegistry()

    registry.register(
        "test-existing-sources",
        ExistingSourceAdapter(sources),
    )

    discovery_engine = SourceDiscoveryEngine(
        registry=registry
    )

    return ResearchPipelineEngine(
        discovery_engine=discovery_engine
    )


def test_pipeline_converts_discovered_content_to_evidence():
    sources = [
        {
            "id": "doc-001",
            "source": "local-document",
            "source_type": "document",
            "title": "Research Source",
            "location": "documents/research.txt",
            "metadata": {
                "content": (
                    "This is real source material for the research pipeline."
                ),
            },
        }
    ]

    pipeline = build_pipeline(sources)

    result = pipeline.run("research pipeline")

    assert result.candidate_count == 1
    assert result.evidence_count == 1
    assert result.rejected_count == 0

    evidence = result.evidence[0]

    assert evidence.source_id == "doc-001"
    assert evidence.content == (
        "This is real source material for the research pipeline."
    )


def test_pipeline_rejects_candidate_without_content():
    sources = [
        {
            "id": "doc-empty",
            "source": "local-document",
            "source_type": "document",
            "title": "Empty Source",
            "location": "documents/empty.txt",
        }
    ]

    pipeline = build_pipeline(sources)

    result = pipeline.run("research pipeline")

    assert result.candidate_count == 1
    assert result.evidence_count == 0
    assert result.rejected_count == 1

    assert result.rejected[0]["source_id"] == "doc-empty"
    assert result.rejected[0]["reason"] == (
        "candidate_has_no_source_content"
    )


def test_pipeline_handles_multiple_sources():
    sources = [
        {
            "id": "doc-001",
            "source": "local",
            "source_type": "document",
            "title": "First",
            "metadata": {
                "content": "First source evidence.",
            },
        },
        {
            "id": "doc-002",
            "source": "local",
            "source_type": "document",
            "title": "Second",
            "metadata": {
                "content": "Second source evidence.",
            },
        },
    ]

    pipeline = build_pipeline(sources)

    result = pipeline.run("multi source research")

    assert result.candidate_count == 2
    assert result.evidence_count == 2
    assert result.rejected_count == 0

    contents = {
        evidence.content
        for evidence in result.evidence
    }

    assert contents == {
        "First source evidence.",
        "Second source evidence.",
    }
