
from __future__ import annotations


def test_all_four_providers_registered():
    from sovereign_intelligence.providers.registry import ProviderRegistry

    registry = ProviderRegistry.default()
    names = set(registry.as_dict().keys())

    assert {"openai", "anthropic", "google", "openrouter"} <= names


def test_all_eight_specialists_available():
    from sovereign_intelligence.execution.multi_agent import MultiAgentTeam

    names = {name for name, _ in MultiAgentTeam().agents}

    assert {
        "research",
        "coding",
        "mathematics",
        "engineering",
        "data",
        "document",
        "cad",
        "general",
    } <= names


def test_data_routing():
    from sovereign_intelligence.execution.multi_agent import MultiAgentTeam

    selected = dict(
        MultiAgentTeam().select_agents(
            "Analyze the dataset, calculate the metrics and identify outliers."
        )
    )

    assert "data" in selected
    assert "general" in selected


def test_document_routing():
    from sovereign_intelligence.execution.multi_agent import MultiAgentTeam

    selected = dict(
        MultiAgentTeam().select_agents(
            "Review this contract and identify conflicting requirements."
        )
    )

    assert "document" in selected
    assert "general" in selected


def test_cad_routing():
    from sovereign_intelligence.execution.multi_agent import MultiAgentTeam

    selected = dict(
        MultiAgentTeam().select_agents(
            "Analyze this CAD drawing and its dimensions and constraints."
        )
    )

    assert "cad" in selected
    assert "engineering" in selected
    assert "general" in selected


def test_existing_governed_api_remains_available():
    from sovereign_intelligence.orchestrator import SovereignBrain

    brain = SovereignBrain()

    assert callable(brain.solve)
    assert callable(brain.solve_governed)
