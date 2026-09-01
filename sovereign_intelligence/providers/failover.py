from __future__ import annotations

from typing import Callable

from .routing_models import (
    ProviderAttempt,
    ProviderCandidate,
    RoutingResult,
)
from .router import ProviderRouter


class ProviderFailover:

    def __init__(
        self,
        providers: dict[str, object],
        candidates: list[ProviderCandidate],
    ):

        self.providers = providers

        self.router = ProviderRouter(
            candidates
        )

    def execute(
        self,
        request,
        required_capabilities=None,
        preferred_provider=None,
        preferred_model=None,
    ):

        decision = self.router.route(
            required_capabilities=(
                required_capabilities
            ),
            preferred_provider=(
                preferred_provider
            ),
            preferred_model=(
                preferred_model
            ),
        )

        ordered = list(
            self.router.candidates
        )

        selected_index = next(
            (
                index
                for index, candidate
                in enumerate(ordered)
                if (
                    candidate.name
                    == decision.provider
                    and candidate.model
                    == decision.model
                )
            ),
            0,
        )

        ordered = ordered[
            selected_index:
        ]

        attempts = []

        for candidate in ordered:

            if not (
                (
                    required_capabilities
                    or set()
                ).issubset(
                    candidate.capabilities
                )
            ):
                continue

            provider = self.providers.get(
                candidate.name
            )

            if provider is None:

                attempts.append(
                    ProviderAttempt(
                        provider=candidate.name,
                        model=candidate.model,
                        success=False,
                        error=(
                            "Provider is not "
                            "configured."
                        ),
                    )
                )

                continue

            try:

                response = provider.generate(
                    request
                )

                attempts.append(
                    ProviderAttempt(
                        provider=candidate.name,
                        model=candidate.model,
                        success=True,
                        response=response,
                    )
                )

                return RoutingResult(
                    decision=decision,
                    attempts=attempts,
                )

            except Exception as exc:

                attempts.append(
                    ProviderAttempt(
                        provider=candidate.name,
                        model=candidate.model,
                        success=False,
                        error=str(exc),
                    )
                )

        raise RuntimeError(
            "All eligible AI providers failed."
        )
