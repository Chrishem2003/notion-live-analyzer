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

        # Stage 41: optional strategy-learning subsystem.
        # The existing brain remains fully functional when learning
        # is not enabled or becomes unavailable.
        self.learning: BrainLearningAdapter | None = None

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
    ):
        """Record a completed brain result in the optional learning layer."""

        if self.learning is None:
            return None

        return self.learning.record_brain_result(
            result=result,
            problem_type=problem_type,
            metadata=metadata,
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

            result = self.executor.execute(
                problem=problem,
                plan=plan,
                provider_name=selected_provider,
                model=selected_model,
                memory_context=memory_context,
                evidence_context=evidence_context,
            )

            result.sources = [
                {
                    "id": candidate.id,
                    "score": candidate.fused_score,
                    "metadata": candidate.metadata,
                }
                for candidate
                in evidence_result.candidates
            ]

            if self.config.enable_verification:

                verification = self.verifier.evaluate(
                    result.answer
                )

                result.verification = verification

            self.memory.save_interaction(
                prompt,
                result.answer,
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
                    "sources": len(
                        result.sources
                    ),
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
