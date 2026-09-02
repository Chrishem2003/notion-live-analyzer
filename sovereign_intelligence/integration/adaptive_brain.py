from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..models import BrainResult, Plan, Problem
from ..execution.orchestrator import ExecutionEngine
from ..optimization.context import ProblemContextClassifier
from ..optimization.routing import (
    DynamicRouteDecisionEngine,
    RoutingConstraints,
    StrategyEligibilityEngine,
)
from ..execution.adaptive_orchestration import (
    AdaptiveExecutionController,
    ExecutionProgressMonitor,
    ExecutionState,
    IntermediateResultEvaluator,
    ExecutionRecoveryPolicy,
    DynamicStrategySwitcher,
    AdaptiveExecutionTrace,
)


@dataclass
class AdaptiveExecutionResult:
    """Internal Stage 45 execution result."""

    result: BrainResult
    state: ExecutionState
    trace: list[dict[str, Any]] = field(default_factory=list)


class AdaptiveBrainExecutionAdapter:
    """
    Stage 45 integration boundary.

    Combines Stage 42 context intelligence, Stage 43 dynamic routing,
    and Stage 44 adaptive execution around the existing ExecutionEngine.

    The existing ExecutionEngine remains responsible for provider calls.
    """

    STRATEGIES = (
        "direct",
        "deep",
        "verify",
        "research",
        "analysis",
        "debug",
        "plan",
    )

    ROUTES = {
        "direct": "standard_execution",
        "deep": "deep_reasoning_execution",
        "verify": "verified_execution",
        "research": "research_execution",
        "analysis": "analytical_execution",
        "debug": "debug_execution",
        "plan": "planning_execution",
    }

    def __init__(
        self,
        executor: ExecutionEngine,
        *,
        max_recovery_attempts: int = 3,
        minimum_score: float = 0.40,
        minimum_confidence: float = 0.40,
        minimum_switch_confidence: float = 0.50,
    ) -> None:
        self.executor = executor

        self.classifier = ProblemContextClassifier()
        self.eligibility = StrategyEligibilityEngine()
        self.router = DynamicRouteDecisionEngine()

        self.monitor = ExecutionProgressMonitor(
            minimum_score=minimum_score,
            minimum_confidence=minimum_confidence,
        )

        self.evaluator = IntermediateResultEvaluator()

        self.switcher = DynamicStrategySwitcher(
            minimum_switch_confidence=minimum_switch_confidence,
        )

        self.recovery = ExecutionRecoveryPolicy(
            max_attempts=max_recovery_attempts,
        )

    def _candidate_history(
        self,
        context: Any,
        historical_ranked: list[Any] | None,
    ) -> dict[str, dict[str, float]]:
        history: dict[str, dict[str, float]] = {}

        for item in historical_ranked or []:
            if isinstance(item, dict):
                strategy = str(
                    item.get("strategy", "")
                ).strip().lower()

                if not strategy:
                    continue

                history[strategy] = {
                    "confidence": max(
                        0.0,
                        min(
                            1.0,
                            float(
                                item.get(
                                    "confidence",
                                    0.0,
                                )
                            ),
                        ),
                    ),
                    "historical_score": max(
                        0.0,
                        min(
                            1.0,
                            float(
                                item.get(
                                    "score",
                                    0.0,
                                )
                            ),
                        ),
                    ),
                }

            else:
                strategy = str(
                    getattr(
                        item,
                        "strategy",
                        "",
                    )
                ).strip().lower()

                if not strategy:
                    continue

                history[strategy] = {
                    "confidence": max(
                        0.0,
                        min(
                            1.0,
                            float(
                                getattr(
                                    item,
                                    "confidence",
                                    0.0,
                                )
                            ),
                        ),
                    ),
                    "historical_score": max(
                        0.0,
                        min(
                            1.0,
                            float(
                                getattr(
                                    item,
                                    "score",
                                    0.0,
                                )
                            ),
                        ),
                    ),
                }

        return history

    def _build_candidates(
        self,
        context: Any,
        historical_ranked: list[Any] | None = None,
    ) -> list[dict[str, Any]]:
        evaluations = self.eligibility.eligible_strategies(
            context,
            strategies=list(self.STRATEGIES),
        )

        history = self._candidate_history(
            context,
            historical_ranked,
        )

        candidates: list[dict[str, Any]] = []

        for evaluation in evaluations:
            strategy = str(
                evaluation.strategy
            ).strip().lower()

            if not strategy:
                continue

            historical = history.get(
                strategy,
                {},
            )

            candidates.append(
                {
                    "strategy": strategy,
                    "confidence": historical.get(
                        "confidence",
                        0.0,
                    ),
                    "historical_score": historical.get(
                        "historical_score",
                        0.0,
                    ),
                }
            )

        return candidates

    def route(
        self,
        prompt: str,
        *,
        historical_ranked: list[Any] | None = None,
        default_strategy: str = "direct",
    ):
        context = self.classifier.classify(prompt)

        candidates = self._build_candidates(
            context,
            historical_ranked=historical_ranked,
        )

        decision = self.router.decide(
            context=context,
            candidates=candidates,
            constraints=RoutingConstraints(),
            default_strategy=default_strategy,
        )

        return context, decision

    def _execute_once(
        self,
        *,
        problem: Problem,
        plan: Plan,
        provider_name: str,
        model: str,
        memory_context: str,
        evidence_context: str,
        strategy: str,
        route: str,
    ) -> BrainResult:
        return self.executor.execute(
            problem=problem,
            plan=plan,
            provider_name=provider_name,
            model=model,
            memory_context=memory_context,
            evidence_context=evidence_context,
            strategy=strategy,
            route=route,
        )

    def execute(
        self,
        *,
        problem: Problem,
        plan: Plan,
        provider_name: str,
        model: str,
        memory_context: str,
        evidence_context: str,
        historical_ranked: list[Any] | None = None,
        default_strategy: str = "direct",
    ) -> AdaptiveExecutionResult:
        context, decision = self.route(
            problem.original,
            historical_ranked=historical_ranked,
            default_strategy=default_strategy,
        )

        state = ExecutionState(
            strategy=decision.strategy,
            route=decision.route,
            problem_type=context.problem_type,
            total_steps=max(
                1,
                len(plan.steps),
            ),
            metadata={
                "stage": 45,
                "route_score": decision.score,
                "route_confidence": decision.confidence,
                "route_fallback": decision.fallback_used,
            },
        )

        controller = AdaptiveExecutionController(
            state
        )

        trace = AdaptiveExecutionTrace()

        trace.execution_created(state)
        controller.start()
        trace.execution_started(state)

        monitor = self.monitor
        monitor.reset(state.execution_id)

        result: BrainResult | None = None
        failed = False

        try:
            controller.update(
                progress=0.10,
                confidence=decision.confidence,
                completed_steps=0,
            )
            trace.progress_updated(state)

            result = self._execute_once(
                problem=problem,
                plan=plan,
                provider_name=provider_name,
                model=model,
                memory_context=memory_context,
                evidence_context=evidence_context,
                strategy=state.strategy,
                route=state.route,
            )

            assessment = self.evaluator.evaluate(
                result=result.answer,
                objective=problem.objective,
            )

            state.intermediate_score = assessment.score
            state.confidence = assessment.confidence

            controller.update(
                progress=0.80,
                intermediate_score=assessment.score,
                confidence=assessment.confidence,
                completed_steps=max(
                    1,
                    len(plan.steps),
                ),
            )

            trace.result_evaluated(state)

            progress_assessment = monitor.assess(
                execution_id=state.execution_id,
                progress=state.progress,
                intermediate_score=assessment.score,
                confidence=assessment.confidence,
                status=state.status,
            )

            if (
                not assessment.needs_reassessment
                and not progress_assessment.needs_reassessment
            ):
                controller.complete()
                trace.execution_completed(state)

                result.execution_trace.extend(
                    trace.export()
                )

                return AdaptiveExecutionResult(
                    result=result,
                    state=state,
                    trace=trace.export(),
                )

            switch_decision = self.switcher.evaluate(
                controller=controller,
                result=result.answer,
                objective=problem.objective,
                strategy_candidates=[
                    item["strategy"]
                    for item in decision.ranked_strategies
                    if item["strategy"] != state.strategy
                ],
            )

            if switch_decision.switch:
                self.switcher.apply(
                    controller,
                    switch_decision,
                )

                trace.strategy_switched(state)

                result = self._execute_once(
                    problem=problem,
                    plan=plan,
                    provider_name=provider_name,
                    model=model,
                    memory_context=memory_context,
                    evidence_context=evidence_context,
                    strategy=state.strategy,
                    route=state.route,
                )

                assessment = self.evaluator.evaluate(
                    result=result.answer,
                    objective=problem.objective,
                )

                controller.update(
                    progress=0.90,
                    intermediate_score=assessment.score,
                    confidence=assessment.confidence,
                    completed_steps=max(
                        1,
                        len(plan.steps),
                    ),
                )

                trace.result_evaluated(state)

            if result is None:
                raise RuntimeError(
                    "Adaptive execution produced no result."
                )

            controller.complete()
            trace.execution_completed(state)

            result.execution_trace.extend(
                trace.export()
            )

            return AdaptiveExecutionResult(
                result=result,
                state=state,
                trace=trace.export(),
            )

        except Exception as exc:
            failed = True

            failure_type = "provider_error"

            decision_recovery = self.recovery.decide(
                state,
                failure_type,
                reason=str(exc),
            )

            trace.recovery_started(
                state,
                reason=decision_recovery.reason,
            )

            recovery_snapshot = self.recovery.recover(
                controller,
                decision_recovery,
                recovery_reason=decision_recovery.reason,
            )

            trace.recovery_applied(
                state,
                action=decision_recovery.action.value,
            )

            if (
                decision_recovery.recoverable
                and decision_recovery.action.value == "switch_strategy"
                and not state.is_terminal
            ):
                try:
                    result = self._execute_once(
                        problem=problem,
                        plan=plan,
                        provider_name=provider_name,
                        model=model,
                        memory_context=memory_context,
                        evidence_context=evidence_context,
                        strategy=state.strategy,
                        route=state.route,
                    )

                    controller.complete()
                    trace.execution_completed(state)

                    result.execution_trace.extend(
                        trace.export()
                    )

                    return AdaptiveExecutionResult(
                        result=result,
                        state=state,
                        trace=trace.export(),
                    )

                except Exception as recovery_exc:
                    controller.fail(
                        str(recovery_exc)
                    )

                    trace.execution_failed(
                        state,
                        reason=str(recovery_exc),
                    )

            elif not decision_recovery.recoverable:
                trace.execution_failed(
                    state,
                    reason=decision_recovery.reason,
                )

            else:
                trace.execution_failed(
                    state,
                    reason=str(exc),
                )

            raise

        finally:
            if failed:
                monitor.reset(state.execution_id)
