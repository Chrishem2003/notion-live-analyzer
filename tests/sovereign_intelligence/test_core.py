from sovereign_intelligence.agents import AgentRegistry
from sovereign_intelligence.execution import Planner
from sovereign_intelligence.knowledge import chunk_text
from sovereign_intelligence.models import Problem
from sovereign_intelligence.verification import Verifier


def test_agents_exist():

    registry = AgentRegistry()

    assert "general" in registry.names()
    assert "coding" in registry.names()
    assert "research" in registry.names()


def test_planner():

    planner = Planner()

    problem = Problem(
        original="Analyze this Python error",
        objective="Fix the error",
    )

    plan = planner.build(problem)

    assert plan.steps
    assert any(
        step.agent == "coding"
        for step in plan.steps
    )


def test_chunking():

    chunks = chunk_text(
        "hello " * 1000
    )

    assert len(chunks) > 1


def test_verifier():

    result = Verifier().evaluate(
        "This is a reasonable answer."
    )

    assert result.passed
    assert result.confidence > 0