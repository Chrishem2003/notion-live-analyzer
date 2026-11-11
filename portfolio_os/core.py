"""Pure, testable decision logic for the Portfolio Intelligence OS.

Scores are prioritization aids, not claims that a market is validated. Inputs
must be supported by evidence and the recommendation must be tested with users.
"""
from __future__ import annotations

from math import ceil
from typing import Any, Mapping

DIMENSION_WEIGHTS: dict[str, int] = {
    "impact": 20,
    "urgency": 15,
    "feasibility": 15,
    "willingness_to_pay": 20,
    "strategic_fit": 10,
    "evidence_quality": 10,
    "time_to_value": 10,
}
RISK_PENALTY_MAX = 15


def _rating(values: Mapping[str, Any], key: str) -> float:
    try:
        value = float(values[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"{key} must be a rating from 0 to 5") from exc
    if not 0 <= value <= 5:
        raise ValueError(f"{key} must be a rating from 0 to 5")
    return value


def score_opportunity(values: Mapping[str, Any]) -> dict[str, Any]:
    """Return an explainable 0–100 score, risk penalty, and next-step advice.

    All positive dimensions use 0–5 ratings. Risk is also 0–5, where 5 means
    high delivery, legal, safety, adoption, or capital risk.
    """
    contributions = {
        key: round((_rating(values, key) / 5) * weight, 2)
        for key, weight in DIMENSION_WEIGHTS.items()
    }
    risk = _rating(values, "risk")
    penalty = round((risk / 5) * RISK_PENALTY_MAX, 2)
    score = round(max(0.0, min(100.0, sum(contributions.values()) - penalty)))
    evidence = _rating(values, "evidence_quality")
    willingness = _rating(values, "willingness_to_pay")

    if score >= 75 and evidence >= 3 and willingness >= 3 and risk <= 3:
        recommendation = "Pilot with real users"
    elif score >= 60:
        recommendation = "Run a focused validation experiment"
    elif score >= 45:
        recommendation = "Collect stronger evidence before building"
    else:
        recommendation = "Park or reframe the opportunity"

    return {
        "score": score,
        "positive_contributions": contributions,
        "risk_penalty": penalty,
        "recommendation": recommendation,
        "evidence_gate_passed": evidence >= 3,
        "payment_signal_gate_passed": willingness >= 3,
        "note": "A high score is a prioritization signal, not proof of demand or revenue.",
    }


def unit_economics(monthly_price: float, variable_cost: float, monthly_fixed_cost: float) -> dict[str, Any]:
    """Calculate simple per-customer contribution and monthly break-even."""
    price, variable, fixed = float(monthly_price), float(variable_cost), float(monthly_fixed_cost)
    if min(price, variable, fixed) < 0:
        raise ValueError("Price and costs cannot be negative")
    contribution = round(price - variable, 2)
    gross_margin_pct = round((contribution / price) * 100, 2) if price > 0 else None
    break_even_customers = ceil(fixed / contribution) if contribution > 0 and fixed > 0 else (0 if fixed == 0 else None)
    return {
        "monthly_price": round(price, 2),
        "variable_cost": round(variable, 2),
        "contribution_per_customer": contribution,
        "gross_margin_pct": gross_margin_pct,
        "monthly_fixed_cost": round(fixed, 2),
        "break_even_customers": break_even_customers,
        "viable_unit_contribution": contribution > 0,
    }
