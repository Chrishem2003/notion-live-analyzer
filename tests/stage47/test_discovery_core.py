from sovereign_intelligence.research.discovery import (
    ExistingSourceAdapter,
    SourceCandidate,
    SourceDiscoveryEngine,
    SourceRegistry,
    StaticSourceAdapter,
    detect_intent,
    plan_discovery,
)


def test_intent_detection():
    assert detect_intent(
        "compare two database systems"
    ) == "comparative"

    assert detect_intent(
        "what is the latest AI research"
    ) == "freshness"


def test_discovery_plan():
    plan = plan_discovery(
        "research evidence for distributed systems"
    )

    assert plan.query
    assert plan.intent == "research"
    assert plan.objectives
    assert plan.search_queries
    assert plan.diversity_required is True


def test_static_source_discovery():
    candidate = SourceCandidate.create(
        source_id="source-1",
        source="stage47-test",
        source_type="document",
        title="Stage 47 Test Source",
    )

    registry = SourceRegistry()

    registry.register(
        "static",
        StaticSourceAdapter([candidate]),
    )

    engine = SourceDiscoveryEngine(registry)

    result = engine.discover_query(
        "research stage 47"
    )

    assert len(result.candidates) == 1
    assert result.total_candidates == 1
    assert result.sources == ["stage47-test"]


def test_existing_source_adapter():
    registry = SourceRegistry()

    registry.register(
        "existing",
        ExistingSourceAdapter(
            [
                {
                    "id": "doc-1",
                    "source": "repository",
                    "source_type": "repository",
                    "title": "Repository source",
                }
            ]
        ),
    )

    result = SourceDiscoveryEngine(
        registry
    ).discover_query(
        "repository research"
    )

    assert len(result.candidates) == 1
    assert result.candidates[0].source_type == (
        "repository"
    )


def test_duplicate_source_candidates():
    candidate = SourceCandidate.create(
        source_id="duplicate",
        source="same-source",
        source_type="document",
    )

    registry = SourceRegistry()

    registry.register(
        "a",
        StaticSourceAdapter([candidate]),
    )

    registry.register(
        "b",
        StaticSourceAdapter([candidate]),
    )

    result = SourceDiscoveryEngine(
        registry
    ).discover_query(
        "duplicate test"
    )

    assert result.total_candidates == 1
    assert len(result.candidates) == 1
