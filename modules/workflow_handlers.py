"""Allow-listed, deterministic handlers for the local workflow runtime.

These handlers are real, bounded computations. They do not claim to be an LLM,
a literature database, or an external service; callers can later register approved
connectors behind the same explicit task interface.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, Mapping

from modules.workflow_contract import WorkflowContractError
from modules.fasta_validation import validate_fasta
from modules.research_qc_gate import evaluate_research_gate


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WorkflowContractError(f"{field} must be non-empty text")
    return value.strip()


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise WorkflowContractError(f"{field} must be a finite number")
    return float(value)


def research_problem_triage(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Turn a problem statement into an actionable, explicitly unverified work brief."""
    question = _text(payload.get("problem"), "problem")
    context = payload.get("context", "")
    if not isinstance(context, str):
        raise WorkflowContractError("context must be text")
    context = context.strip()
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", question)
    if len(words) < 3:
        raise WorkflowContractError("problem must contain at least three words")
    lowered = question.lower()
    evidence = ["Original problem statement and acceptance criteria"]
    actions = [
        "Clarify the desired outcome and measurable success criteria",
        "Collect relevant inputs, constraints, and source evidence",
        "Choose a method appropriate to the evidence and risk level",
        "Run the method and record parameters, outputs, and limitations",
        "Check the result against the acceptance criteria before marking complete",
    ]
    if any(term in lowered for term in ("data", "dataset", "csv", "measurement", "experiment")):
        evidence.extend(["Dataset or raw measurements", "Variable definitions, units, and missing-data conventions"])
        actions.insert(2, "Profile missing values, duplicates, types, ranges, and unit consistency")
    if any(term in lowered for term in ("literature", "paper", "publication", "citation", "study")):
        evidence.extend(["Verifiable bibliographic records", "Relevant primary sources and publication dates"])
        actions.insert(2, "Search and screen relevant sources; verify each citation against the original record")
    if any(term in lowered for term in ("safety", "clinical", "patient", "hazard", "compliance", "legal")):
        evidence.extend(["Applicable safety/compliance requirements", "Qualified human review for high-impact decisions"])
        actions.insert(0, "Classify risk and identify decisions that require qualified human approval")
    return {
        "problem": question,
        "context": context,
        "interpretation": "Initial triage only; assumptions and source evidence still require review.",
        "suggested_workflow": actions,
        "evidence_needed": list(dict.fromkeys(evidence)),
        "acceptance_checks": [
            "Outputs are traceable to inputs and cited evidence",
            "Assumptions, uncertainty, and limitations are recorded",
            "A test or independent check supports the proposed result",
            "Human approval is obtained where risk or policy requires it",
        ],
        "human_review_required": True,
    }


def numeric_summary(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Compute transparent descriptive statistics for a bounded numeric sequence."""
    values = payload.get("values")
    if not isinstance(values, list) or not values:
        raise WorkflowContractError("values must be a non-empty list of numbers")
    if len(values) > 100000:
        raise WorkflowContractError("values cannot exceed 100000 items per run")
    numbers = [_number(value, f"values[{index}]") for index, value in enumerate(values)]
    ordered = sorted(numbers)
    n = len(ordered)
    median = (ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2)
    mean = sum(numbers) / n
    variance = sum((value - mean) ** 2 for value in numbers) / (n - 1) if n > 1 else 0.0
    return {
        "n": n,
        "mean": mean,
        "median": median,
        "minimum": ordered[0],
        "maximum": ordered[-1],
        "range": ordered[-1] - ordered[0],
        "sample_standard_deviation": math.sqrt(variance),
        "standard_deviation_note": "Sample standard deviation uses n-1; reported as 0 for a single observation.",
    }


def data_quality_profile(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Profile in-memory row records for missingness, duplicates, and basic types."""
    rows = payload.get("rows")
    if not isinstance(rows, list) or not rows:
        raise WorkflowContractError("rows must be a non-empty list of objects")
    if len(rows) > 50000:
        raise WorkflowContractError("rows cannot exceed 50000 per run")
    if any(not isinstance(row, dict) for row in rows):
        raise WorkflowContractError("every row must be an object")
    columns = sorted({key for row in rows for key in row.keys()})
    if not columns:
        raise WorkflowContractError("rows must contain at least one column")
    missing = {}
    types = {}
    for column in columns:
        column_values = [row.get(column) for row in rows]
        missing[column] = sum(value is None or (isinstance(value, str) and not value.strip()) for value in column_values)
        observed = [value for value in column_values if value is not None and not (isinstance(value, str) and not value.strip())]
        types[column] = sorted({type(value).__name__ for value in observed}) or ["all_missing"]
    canonical = [tuple((column, row.get(column)) for column in columns) for row in rows]
    try:
        duplicate_rows = len(canonical) - len(set(canonical))
    except TypeError:
        encoded = [repr(row) for row in canonical]
        duplicate_rows = len(encoded) - len(set(encoded))
    return {
        "row_count": len(rows),
        "column_count": len(columns),
        "columns": columns,
        "missing_values_by_column": missing,
        "observed_python_types_by_column": types,
        "duplicate_row_count": duplicate_rows,
        "limitations": [
            "No domain-specific validity rules, units, outlier policy, or causal claims are inferred.",
            "Observed Python types are a basic screening signal, not a complete schema contract.",
        ],
    }


def default_handlers() -> dict[str, Any]:
    """Return the built-in trusted handler allow-list."""
    return {
        "research_problem_triage": research_problem_triage,
        "numeric_summary": numeric_summary,
        "data_quality_profile": data_quality_profile,
        "fasta_validate": validate_fasta,
        "research_qc_gate": evaluate_research_gate,
    }
