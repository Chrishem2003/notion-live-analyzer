"""Sovereign Intelligence package.

Keep lightweight models/providers importable from the API container without
eagerly importing the full orchestration, retrieval, and scientific stack.
The public SovereignBrain symbol remains available through lazy import.
"""
from __future__ import annotations

__all__ = ["SovereignBrain"]
__version__ = "0.1.0"


def __getattr__(name: str):
    if name == "SovereignBrain":
        from .orchestrator import SovereignBrain
        return SovereignBrain
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
