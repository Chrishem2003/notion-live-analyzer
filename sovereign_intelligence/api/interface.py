from __future__ import annotations

from ..orchestrator import SovereignBrain


_brain: SovereignBrain | None = None


def get_brain() -> SovereignBrain:

    global _brain

    if _brain is None:
        _brain = SovereignBrain()

    return _brain


def solve(
    prompt: str,
    provider: str | None = None,
    model: str | None = None,
):

    return get_brain().solve(
        prompt,
        provider=provider,
        model=model,
    )