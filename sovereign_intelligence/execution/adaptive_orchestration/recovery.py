from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Mapping

from .state import ExecutionState, ExecutionStatus


class RecoveryAction(str, Enum):
    RETRY = "retry"
    SWITCH_STRATEGY = "switch_strategy"
    FAIL = "fail"


@dataclass(frozen=True)
class RecoveryDecision:
    recoverable: bool
    action: RecoveryAction
    reason: str
    failure_type: str
    attempt: int
    max_attempts: int
    fallback_strategy: str | None = None
    metadata: dict[str, Any] | None = None


class ExecutionRecoveryPolicy:
    """
    Deterministic policy for recovering failed adaptive executions.

    The policy decides what should happen. It does not perform the
    recovery itself. State transitions remain owned by the execution
    controller/state model.
    """

    DEFAULT_RECOVERABLE_FAILURES = frozenset(
        {
            "timeout",
            "transient",
            "temporary",
            "provider_error",
            "rate_limit",
            "resource_error",
            "strategy_failure",
        }
    )

    DEFAULT_SWITCH_FAILURES = frozenset(
        {
            "strategy_failure",
            "provider_error",
        }
    )

    DEFAULT_NON_RECOVERABLE_FAILURES = frozenset(
        {
            "invalid_request",
            "invalid_input",
            "permission_denied",
            "authentication",
            "authorization",
            "configuration",
            "unsupported",
            "cancelled",
        }
    )

    def __init__(
        self,
        *,
        max_attempts: int = 3,
        recoverable_failures: Iterable[str] | None = None,
        switch_failures: Iterable[str] | None = None,
        non_recoverable_failures: Iterable[str] | None = None,
        fallback_strategies: Mapping[str, str] | None = None,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")

        self.max_attempts = int(max_attempts)

        self.recoverable_failures = {
            self._normalize_failure(value)
            for value in (
                recoverable_failures
                if recoverable_failures is not None
                else self.DEFAULT_RECOVERABLE_FAILURES
            )
        }

        self.switch_failures = {
            self._normalize_failure(value)
            for value in (
                switch_failures
                if switch_failures is not None
                else self.DEFAULT_SWITCH_FAILURES
            )
        }

        self.non_recoverable_failures = {
            self._normalize_failure(value)
            for value in (
                non_recoverable_failures
                if non_recoverable_failures is not None
                else self.DEFAULT_NON_RECOVERABLE_FAILURES
            )
        }

        self.fallback_strategies = {
            self._normalize_failure(key): value
            for key, value in (
                fallback_strategies.items()
                if fallback_strategies is not None
                else {
                    "strategy_failure": "deep",
                    "provider_error": "verify",
                }.items()
            )
        }

    @staticmethod
    def _normalize_failure(value: str) -> str:
        return str(value).strip().lower().replace(" ", "_")

    @staticmethod
    def _normalize_status(status: Any) -> ExecutionStatus | None:
        if isinstance(status, ExecutionStatus):
            return status

        try:
            return ExecutionStatus(str(status).lower())
        except ValueError:
            return None

    def classify_failure(self, failure_type: str) -> str:
        normalized = self._normalize_failure(failure_type)

        if normalized in self.non_recoverable_failures:
            return "non_recoverable"

        if normalized in self.switch_failures:
            return "switchable"

        if normalized in self.recoverable_failures:
            return "retryable"

        return "unknown"

    def decide(
        self,
        state: ExecutionState,
        failure_type: str,
        *,
        reason: str | None = None,
        fallback_strategy: str | None = None,
    ) -> RecoveryDecision:
        normalized_failure = self._normalize_failure(failure_type)
        status = self._normalize_status(state.status)
        classification = self.classify_failure(normalized_failure)

        base_reason = reason or f"Execution failure classified as '{normalized_failure}'."

        metadata = {
            "execution_id": state.execution_id,
            "status": state.status.value
            if isinstance(state.status, ExecutionStatus)
            else str(state.status),
            "classification": classification,
            "strategy": state.strategy,
            "route": state.route,
        }

        if status in {
            ExecutionStatus.COMPLETED,
            ExecutionStatus.CANCELLED,
        }:
            return RecoveryDecision(
                recoverable=False,
                action=RecoveryAction.FAIL,
                reason=(
                    "Execution is already terminal and cannot enter recovery."
                ),
                failure_type=normalized_failure,
                attempt=state.attempt,
                max_attempts=self.max_attempts,
                metadata=metadata,
            )

        if status not in {
            ExecutionStatus.RUNNING,
            ExecutionStatus.FAILED,
            ExecutionStatus.RECOVERING,
            ExecutionStatus.CREATED,
        }:
            return RecoveryDecision(
                recoverable=False,
                action=RecoveryAction.FAIL,
                reason=f"Execution status '{status}' does not permit recovery.",
                failure_type=normalized_failure,
                attempt=state.attempt,
                max_attempts=self.max_attempts,
                metadata=metadata,
            )

        if classification in {"non_recoverable", "unknown"}:
            return RecoveryDecision(
                recoverable=False,
                action=RecoveryAction.FAIL,
                reason=(
                    f"{base_reason} Automatic recovery is disabled for "
                    f"{classification} failures."
                ),
                failure_type=normalized_failure,
                attempt=state.attempt,
                max_attempts=self.max_attempts,
                metadata=metadata,
            )

        if state.attempt >= self.max_attempts:
            return RecoveryDecision(
                recoverable=False,
                action=RecoveryAction.FAIL,
                reason=(
                    f"{base_reason} Maximum recovery attempts "
                    f"({self.max_attempts}) have been reached."
                ),
                failure_type=normalized_failure,
                attempt=state.attempt,
                max_attempts=self.max_attempts,
                metadata=metadata,
            )

        if classification == "switchable":
            selected_strategy = (
                fallback_strategy
                or self.fallback_strategies.get(normalized_failure)
            )

            if not selected_strategy:
                return RecoveryDecision(
                    recoverable=False,
                    action=RecoveryAction.FAIL,
                    reason=(
                        f"{base_reason} Failure is switchable, but no "
                        "safe fallback strategy is configured."
                    ),
                    failure_type=normalized_failure,
                    attempt=state.attempt,
                    max_attempts=self.max_attempts,
                    metadata=metadata,
                )

            if selected_strategy == state.strategy:
                return RecoveryDecision(
                    recoverable=False,
                    action=RecoveryAction.FAIL,
                    reason=(
                        f"{base_reason} The configured fallback strategy "
                        "matches the current strategy."
                    ),
                    failure_type=normalized_failure,
                    attempt=state.attempt,
                    max_attempts=self.max_attempts,
                    fallback_strategy=selected_strategy,
                    metadata=metadata,
                )

            metadata["fallback_strategy"] = selected_strategy

            return RecoveryDecision(
                recoverable=True,
                action=RecoveryAction.SWITCH_STRATEGY,
                reason=(
                    f"{base_reason} A configured fallback strategy "
                    f"'{selected_strategy}' is available."
                ),
                failure_type=normalized_failure,
                attempt=state.attempt,
                max_attempts=self.max_attempts,
                fallback_strategy=selected_strategy,
                metadata=metadata,
            )

        return RecoveryDecision(
            recoverable=True,
            action=RecoveryAction.RETRY,
            reason=(
                f"{base_reason} The failure is transient/retryable and "
                "recovery attempts remain."
            ),
            failure_type=normalized_failure,
            attempt=state.attempt,
            max_attempts=self.max_attempts,
            metadata=metadata,
        )

    def recover(
        self,
        controller: Any,
        decision: RecoveryDecision,
        *,
        recovery_reason: str | None = None,
    ) -> dict[str, Any]:
        """
        Apply the state transition implied by a recovery decision.

        This method deliberately performs only state-machine operations.
        Provider execution remains outside the recovery policy.
        """

        if not decision.recoverable:
            controller.fail(
                recovery_reason
                or decision.reason
            )
            return controller.snapshot()

        controller.begin_recovery(
            recovery_reason
            or decision.reason
        )

        if decision.action == RecoveryAction.SWITCH_STRATEGY:
            if not decision.fallback_strategy:
                controller.fail(
                    "Recovery requested strategy switching without a fallback strategy."
                )
                return controller.snapshot()

            route_map = {
                "direct": "standard_execution",
                "deep": "deep_reasoning_execution",
                "verify": "verified_execution",
                "research": "research_execution",
                "analysis": "analytical_execution",
                "debug": "debug_execution",
                "plan": "planning_execution",
            }

            route = route_map.get(decision.fallback_strategy)

            if route is None:
                controller.fail(
                    f"No execution route is configured for "
                    f"fallback strategy '{decision.fallback_strategy}'."
                )
                return controller.snapshot()

            controller.switch_strategy(
                decision.fallback_strategy,
                route,
            )

            return controller.snapshot()

        if decision.action == RecoveryAction.RETRY:
            controller.resume_after_recovery()
            return controller.snapshot()

        controller.fail(
            recovery_reason
            or decision.reason
        )

        return controller.snapshot()
