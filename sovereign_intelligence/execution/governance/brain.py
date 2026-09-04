from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from sovereign_intelligence.models import (
    AIRequest,
    AIResponse,
    BrainResult,
    Problem,
    Plan,
)
from sovereign_intelligence.execution import (
    MultiAgentTeam,
    TeamResult,
)
from sovereign_intelligence.execution.decision_engine import DecisionEngine
from sovereign_intelligence.execution.decision_models import DecisionResult
from sovereign_intelligence.execution.governance.pipeline import (
    GovernedDecision,
    GovernedDecisionPipeline,
)
from sovereign_intelligence.verification import (
    VerificationResult,
    Verifier,
)


@dataclass(frozen=True)
class GovernedBrainResult:
    """
    Stage 51 governed brain result.

    The original BrainResult remains intact and is exposed through
    `brain_result`. Governance evidence is retained separately so
    existing BrainResult consumers are not forced to change.
    """

    brain_result: BrainResult
    team_result: TeamResult
    decision: DecisionResult
    governed_decision: GovernedDecision

    @property
    def answer(self) -> str:
        return self.brain_result.answer

    @property
    def plan(self) -> Plan | None:
        return self.brain_result.plan

    @property
    def verification(self) -> VerificationResult | None:
        return self.brain_result.verification

    @property
    def provider(self) -> str | None:
        return self.brain_result.provider

    @property
    def model(self) -> str | None:
        return self.brain_result.model

    @property
    def execution_trace(self) -> list[dict[str, Any]]:
        return self.brain_result.execution_trace

    @property
    def sources(self) -> list[dict[str, Any]]:
        return self.brain_result.sources

    @property
    def control(self):
        return self.governed_decision.control

    @property
    def record(self):
        return self.governed_decision.record

    @property
    def assessment(self):
        return self.governed_decision.assessment


class GovernedBrainExecutor:
    """
    Stage 51 adapter connecting the existing Sovereign Brain components.

    This class does not replace ExecutionEngine. It uses the existing
    ProviderRegistry directly for specialist workers, then routes the
    real specialist contributions through DecisionEngine and the
    Stage 50 GovernedDecisionPipeline.
    """

    def __init__(
        self,
        *,
        providers,
        verifier: Verifier | None = None,
        team: MultiAgentTeam | None = None,
        decision_engine: DecisionEngine | None = None,
        governance_pipeline: GovernedDecisionPipeline | None = None,
    ) -> None:
        self.providers = providers
        self.verifier = verifier or Verifier()
        self.team = team or MultiAgentTeam()
        self.decision_engine = decision_engine or DecisionEngine()
        self.governance_pipeline = (
            governance_pipeline
            or GovernedDecisionPipeline()
        )

    def execute(
        self,
        *,
        problem: Problem,
        plan: Plan,
        provider_name: str,
        model: str,
        memory_context: str = "",
        evidence_context: str = "",
        strategy: str = "direct",
        route: str = "governed_multi_agent",
        decision_id: str | None = None,
    ) -> GovernedBrainResult:

        if not isinstance(problem, Problem):
            raise TypeError("problem must be a Problem")

        if not isinstance(plan, Plan):
            raise TypeError("plan must be a Plan")

        provider = self.providers.get(provider_name)

        selected_strategy = (
            str(strategy or "direct").strip().lower()
        )

        selected_route = str(
            route or "governed_multi_agent"
        ).strip()

        def worker(
            agent_name: str,
            role: str,
            specialist_prompt: str,
        ) -> AIResponse:

            system = (
                "You are a specialist inside Sovereign Intelligence.\n"
                f"Specialist identity: {agent_name}\n"
                f"Specialist role: {role}\n"
                f"Execution strategy: {selected_strategy}\n"
                f"Execution route: {selected_route}\n\n"
                "Operate independently and honestly.\n"
                "Separate facts from assumptions.\n"
                "Do not fabricate evidence, tool execution, or certainty.\n"
                "Provide a concrete conclusion when the evidence permits one."
            )

            context_parts = []

            if memory_context.strip():
                context_parts.append(
                    "Relevant memory:\n"
                    + memory_context[:12000]
                )

            if evidence_context.strip():
                context_parts.append(
                    "Retrieved evidence:\n"
                    + evidence_context[:12000]
                )

            if context_parts:
                specialist_prompt = (
                    specialist_prompt
                    + "\n\n"
                    + "\n\n".join(context_parts)
                )

            request = AIRequest(
                prompt=specialist_prompt,
                system=system,
                model=model,
                provider=provider_name,
            )

            response = provider.generate(request)

            if not isinstance(response, AIResponse):
                raise TypeError(
                    "Provider.generate() must return AIResponse"
                )

            return response

        team_result = self.team.execute(
            problem.original,
            worker,
        )

        decision = self.decision_engine.decide(
            team_result.contributions,
        )

        # Verification is performed against the actual synthesized
        # specialist output. No synthetic score is introduced.
        candidate_answer = (
            team_result.consensus.strip()
            if team_result.consensus.strip()
            else decision.decision.strip()
        )

        verification = self.verifier.evaluate(
            candidate_answer,
        )

        brain_result = BrainResult(
            answer=candidate_answer,
            plan=plan,
            verification=verification,
            provider=provider_name,
            model=model,
            execution_trace=[
                {
                    "event": "governed_multi_agent_started",
                    "provider": provider_name,
                    "model": model,
                    "strategy": selected_strategy,
                    "route": selected_route,
                },
                {
                    "event": "multi_agent_completed",
                    "selected_agents": len(
                        team_result.contributions
                    ),
                    "successful_agents": (
                        team_result.successful_agents
                    ),
                    "failed_agents": (
                        team_result.failed_agents
                    ),
                    "team_confidence": team_result.confidence,
                    "disagreements": list(
                        team_result.disagreements
                    ),
                },
                {
                    "event": "decision_engine_completed",
                    "decision_confidence": decision.confidence,
                    "consensus": decision.consensus,
                    "conflicts": list(decision.conflicts),
                },
                {
                    "event": "verification_completed",
                    "passed": verification.passed,
                    "confidence": verification.confidence,
                    "issues": list(verification.issues),
                },
            ],
        )

        if decision_id is None:
            decision_id = uuid4().hex

        # Stage 50 accepts protocol-like evaluation objects.
        # VerificationResult already provides the real fields needed
        # by the control engine: passed, confidence, issues and
        # recommendations. The pipeline's evaluation_score is mapped
        # from the real verification confidence.
        governed = self.governance_pipeline.run(
            decision,
            verification,
            decision_id=decision_id,
            decision_confidence=decision.confidence,
            evaluation_score=verification.confidence,
            consensus=decision.consensus,
        )

        brain_result.execution_trace.append(
            {
                "event": "governance_completed",
                "decision_id": decision_id,
                "action": governed.control.action.value,
                "governance_accepted": (
                    governed.assessment.accepted
                ),
                "consistency_score": (
                    governed.assessment.consistency_score
                ),
                "confidence_stability": (
                    governed.assessment.confidence_stability
                ),
            }
        )

        return GovernedBrainResult(
            brain_result=brain_result,
            team_result=team_result,
            decision=decision,
            governed_decision=governed,
        )
