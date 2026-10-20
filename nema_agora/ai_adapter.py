"""Provider-neutral advisory model adapter contract for NEMA-AGORA.

No provider SDK is imported here. Implementations may wrap a local or external
model later, but every result must pass the Phase 9 safety contract first.
"""
from __future__ import annotations

from typing import Any, Protocol

from nema_agora.evaluation import validate_advisory_output


class AdvisoryModelAdapter(Protocol):
    def analyse(self, record: dict[str, Any]) -> dict[str, Any]:
        """Return an advisory result containing source_case_id and human review."""


def validate_model_result(record: dict[str, Any], output: dict[str, Any]) -> dict[str, Any]:
    errors = validate_advisory_output(output)
    if output.get("source_case_id") != record.get("case_id"):
        errors.append("source_case_id must match the analysed record")
    if errors:
        raise ValueError("; ".join(errors))
    return output
