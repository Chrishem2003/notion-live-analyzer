from __future__ import annotations

from .routing_models import (
    ProviderCandidate,
    RoutingDecision,
)


class ProviderRouter:

    def __init__(
        self,
        candidates: list[ProviderCandidate],
    ):

        self.candidates = sorted(
            candidates,
            key=lambda item: item.priority,
        )

    def route(
        self,
        required_capabilities: set[str] | None = None,
        preferred_provider: str | None = None,
        preferred_model: str | None = None,
    ) -> RoutingDecision:

        required = (
            required_capabilities
            or set()
        )

        candidates = self.candidates

        if preferred_provider:

            preferred = [
                candidate
                for candidate in candidates
                if candidate.name
                == preferred_provider
            ]

            others = [
                candidate
                for candidate in candidates
                if candidate.name
                != preferred_provider
            ]

            candidates = preferred + others

        for candidate in candidates:

            if not required.issubset(
                candidate.capabilities
            ):
                continue

            model = (
                preferred_model
                if (
                    preferred_model
                    and candidate.name
                    == preferred_provider
                )
                else candidate.model
            )

            return RoutingDecision(
                provider=candidate.name,
                model=model,
                reason=(
                    "Selected the highest-priority "
                    "provider satisfying the "
                    "requested capabilities."
                ),
            )

        raise RuntimeError(
            "No configured provider satisfies "
            "the requested capabilities."
        )
