from __future__ import annotations

from .config import BrainConfig
from .models import Problem, BrainResult
from .providers.registry import ProviderRegistry
from .agents.registry import AgentRegistry
from .memory import MemoryStore, MemoryManager
from .execution import Planner, ExecutionEngine
from .verification import Verifier
from .safety.audit import AuditLogger
from .knowledge import KnowledgeEngine
from .integration.brain_learning import BrainLearningAdapter
from .integration.adaptive_brain import AdaptiveBrainExecutionAdapter
from .integration.research_brain import BrainResearchAdapter


class SovereignBrain:

    def __init__(
        self,
        config: BrainConfig | None = None,
    ):

        self.config = (
            config
            or BrainConfig.from_env()
        )

        self.providers = ProviderRegistry.default()

        self.agents = AgentRegistry()

        self.memory_store = MemoryStore(
            self.config.memory_path
        )

        self.memory = MemoryManager(
            self.memory_store
        )

        self.planner = Planner()

        self.executor = ExecutionEngine(
            self.providers,
            self.agents,
        )

        self.verifier = Verifier()

        self.audit = AuditLogger(
            self.config.audit_path
        )

        self.knowledge = KnowledgeEngine()

        # Stage 46: Evidence & Research Intelligence.
        # Thin adapter over the existing KnowledgeEngine.
        self.research = BrainResearchAdapter()

        # Stage 41: optional strategy-learning subsystem.
        # The existing brain remains fully functional when learning
        # is not enabled or becomes unavailable.
        self.learning: BrainLearningAdapter | None = None

        # Stage 45: optional adaptive execution orchestration.
        # The existing ExecutionEngine remains the underlying executor.
        self.adaptive_execution: AdaptiveBrainExecutionAdapter | None = None

        if self.config.enable_adaptive_execution:
            self.adaptive_execution = AdaptiveBrainExecutionAdapter(
                executor=self.executor,
                max_recovery_attempts=self.config.max_iterations,
            )

    def enable_learning(
        self,
        database_path: str,
    ) -> BrainLearningAdapter:
        """Enable the optional Stage 41 strategy-learning subsystem."""

        if not database_path or not database_path.strip():
            raise ValueError(
                "database_path cannot be empty."
            )

        self.learning = BrainLearningAdapter(
            database_path=database_path,
        )

        return self.learning

    def choose_learning_strategy(
        self,
        problem_type: str = "general",
        default_strategy: str = "direct",
    ):
        """Choose a learned strategy without altering core execution."""

        if self.learning is None:
            return {
                "strategy": default_strategy,
                "problem_type": problem_type,
                "confidence": 0.0,
                "reason": "Learning subsystem is not enabled.",
                "learning_available": False,
            }

        decision = self.learning.choose_strategy(
            problem_type=problem_type,
        )

        return {
            "strategy": decision.strategy,
            "problem_type": decision.problem_type,
            "confidence": decision.confidence,
            "reason": decision.reason,
            "learning_available": decision.metadata.get(
                "learning_available",
                False,
            ),
        }

    def record_learning_result(
        self,
        result: BrainResult,
        problem_type: str = "general",
        metadata: dict | None = None,
        strategy: str | None = None,
    ):
        """Record a completed brain result in the optional learning layer."""

        if self.learning is None:
            return None

        return self.learning.record_brain_result(
            result=result,
            problem_type=problem_type,
            metadata=metadata,
            strategy=strategy,
        )

    def add_knowledge(
        self,
        document_id: str,
        content: str,
        metadata: dict | None = None,
    ):

        self.knowledge.add_document(
            document_id=document_id,
            content=content,
            metadata=metadata,
        )

    def add_knowledge_file(
        self,
        path: str,
        document_id: str | None = None,
    ):

        self.knowledge.add_file(
            path=path,
            document_id=document_id,
        )

    def solve(
        self,
        prompt: str,
        provider: str | None = None,
        model: str | None = None,
    ) -> BrainResult:

        if not prompt.strip():
            raise ValueError(
                "Problem prompt cannot be empty."
            )

        selected_provider = (
            provider
            or self.config.default_provider
        )

        selected_model = (
            model
            or self.config.default_model
        )

        problem = Problem(
            original=prompt,
            objective=prompt,
        )

        memory_context = self.memory.context()

        plan = self.planner.build(problem)

        self.audit.record(
            "problem_started",
            {
                "prompt": prompt,
                "provider": selected_provider,
                "model": selected_model,
            },
        )

        try:

            evidence_result, evidence_context = (
                self.knowledge.context(
                    query=prompt,
                    top_k=5,
                    max_characters=12000,
                )
            )

            # Stage 46: Evidence & Research Intelligence.
            # Existing KnowledgeEngine retrieval remains unchanged.
            research_result = self.research.process(
                query=prompt,
                retrieval_result=evidence_result,
                max_results=5,
            )

            self.audit.record(
                "research_evidence_processed",
                {
                    "query": prompt,
                    "count": len(research_result.evidence),
                    "total_candidates": research_result.total_candidates,
                    "duplicates_removed": research_result.duplicates_removed,
                    "sources": research_result.sources,
                },
            )

            self.audit.record(
                "knowledge_retrieved",
                {
                    "query": prompt,
                    "count": len(
                        evidence_result.candidates
                    ),
                    "strategy": (
                        evidence_result.strategy
                    ),
                },
            )

            # Stage 45: adaptive execution orchestration.
            #
            # The existing ExecutionEngine remains the underlying
            # executor. Adaptive orchestration adds routing,
            # evaluation, recovery, and strategy tracing around it.
            #
            # If adaptive execution is disabled or unavailable,
            # the original execution path remains available.

            adaptive_result = None
            adaptive_strategy = None
            adaptive_trace = []
            historical_ranked = None

            if self.learning is not None:
                try:
                    historical_ranked = self.learning.ranked_strategies(
                        problem_type="general",
                    )
                except Exception:
                    historical_ranked = None

            if self.adaptive_execution is not None:
                try:
                    adaptive_result = self.adaptive_execution.execute(
                        problem=problem,
                        plan=plan,
                        provider_name=selected_provider,
                        model=selected_model,
                        memory_context=memory_context,
                        evidence_context=evidence_context,
                        historical_ranked=historical_ranked,
                    )

                    result = adaptive_result.result

                    adaptive_strategy = getattr(
                        adaptive_result.state,
                        "strategy",
                        None,
                    )

                    adaptive_trace = list(
                        getattr(
                            adaptive_result,
                            "trace",
                            [],
                        )
                        or []
                    )

                    if adaptive_trace:
                        existing_trace = list(
                            getattr(
                                result,
                                "execution_trace",
                                [],
                            )
                            or []
                        )

                        result.execution_trace = (
                            existing_trace + adaptive_trace
                        )

                    self.audit.record(
                        "adaptive_execution_completed",
                        {
                            "strategy": adaptive_strategy,
                            "route": getattr(
                                adaptive_result.state,
                                "route",
                                None,
                            ),
                            "status": getattr(
                                adaptive_result.state,
                                "status",
                                None,
                            ),
                            "trace_events": len(adaptive_trace),
                        },
                    )

                except Exception as adaptive_exc:
                    self.audit.record(
                        "adaptive_execution_fallback",
                        {
                            "error": str(adaptive_exc),
                        },
                    )

                    result = self.executor.execute(
                        problem=problem,
                        plan=plan,
                        provider_name=selected_provider,
                        model=selected_model,
                        memory_context=memory_context,
                        evidence_context=evidence_context,
                    )

            else:
                result = self.executor.execute(
                    problem=problem,
                    plan=plan,
                    provider_name=selected_provider,
                    model=selected_model,
                    memory_context=memory_context,
                    evidence_context=evidence_context,
                )

            # Stage 46: expose research-ranked evidence through
            # the existing BrainResult.sources field.
            research_sources = self.research.source_records(
                research_result
            )

            if research_sources:
                result.sources = research_sources

            if self.config.enable_verification:

                verification = self.verifier.evaluate(
                    result.answer
                )

                result.verification = verification

            self.memory.save_interaction(
                prompt,
                result.answer,
            )

            # Stage 41/45: persist the actual strategy when
            # the optional learning subsystem is enabled.
            if self.learning is not None:
                try:
                    self.record_learning_result(
                        result=result,
                        problem_type="general",
                        metadata={
                            "adaptive_execution": (
                                self.adaptive_execution is not None
                            ),
                        },
                        strategy=adaptive_strategy,
                    )
                except Exception as learning_exc:
                    self.audit.record(
                        "learning_record_failed",
                        {
                            "error": str(learning_exc),
                        },
                    )

            self.audit.record(
                "problem_completed",
                {
                    "provider": result.provider,
                    "model": result.model,
                    "verified": (
                        result.verification.passed
                        if result.verification
                        else None
                    ),
                    "sources": len(result.sources),
                    "adaptive_execution": (
                        self.adaptive_execution is not None
                    ),
                    "adaptive_strategy": adaptive_strategy,
                },
            )

            return result

        except Exception as exc:

            self.audit.record(
                "problem_failed",
                {
                    "error": str(exc),
                },
            )

            raise
