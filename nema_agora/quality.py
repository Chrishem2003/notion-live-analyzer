"""Deterministic data-quality checks for NEMA-AGORA observations.

Quality flags are advisory workflow signals. They never establish that an
environmental incident is true, illegal, urgent, or regulatorily confirmed.
"""
from __future__ import annotations

import math
from datetime import date

from nema_agora.core import CATEGORIES, SEVERITIES, STATUSES
from collections.abc import Mapping, Sequence
from typing import Any

REQUIRED_FIELDS = (
    "case_id", "observation_date", "category", "severity",
    "district_or_site", "description", "status",
)
QUALITY_FLAGS = (
    "VALID", "INCOMPLETE", "INVALID_COORDINATES", "MISSING_DESCRIPTION",
    "MISSING_CONSENT", "INVALID_DATE", "INVALID_CATEGORY", "INVALID_SEVERITY",
    "INVALID_STATUS", "DUPLICATE_SUSPECTED", "NEEDS_REVIEW",
)


def _text(value: Any) -> str:
    """Normalise text without treating None as the literal word 'None'."""
    return value.strip() if isinstance(value, str) else ""


def _coordinate_pair(record: Mapping[str, Any]) -> tuple[float, float] | None:
    lat, lon = record.get("latitude", ""), record.get("longitude", "")
    if lat in ("", None) and lon in ("", None):
        return None
    if isinstance(lat, bool) or isinstance(lon, bool):
        return (math.nan, math.nan)
    try:
        latitude, longitude = float(lat), float(lon)
    except (TypeError, ValueError, OverflowError):
        return (math.nan, math.nan)
    return latitude, longitude


def assess_observation(
    record: Mapping[str, Any],
    *,
    peer_records: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return stable quality flags; malformed top-level inputs fail closed.

    Coordinates may be omitted as a pair, but partial, non-finite, or
    out-of-range coordinates are flagged. Quality PASS is not an environmental
    finding and does not waive human review.
    """
    if not isinstance(record, Mapping):
        raise ValueError("record must be a mapping")
    if peer_records is not None and (
        not isinstance(peer_records, Sequence)
        or isinstance(peer_records, (str, bytes))
        or any(not isinstance(peer, Mapping) for peer in peer_records)
    ):
        raise ValueError("peer_records must be a sequence of mappings")

    flags: list[str] = []
    missing = [
        field for field in REQUIRED_FIELDS
        if not _text(record.get(field))
    ]
    if missing:
        flags.append("INCOMPLETE")
    if not _text(record.get("description")):
        flags.append("MISSING_DESCRIPTION")
    if record.get("consent_confirmed") is not True:
        flags.append("MISSING_CONSENT")

    raw_date = _text(record.get("observation_date"))
    try:
        parsed_date = date.fromisoformat(raw_date)
        if parsed_date.isoformat() != raw_date:
            raise ValueError("date must use YYYY-MM-DD")
    except (TypeError, ValueError):
        flags.append("INVALID_DATE")
    if _text(record.get("category")) not in CATEGORIES:
        flags.append("INVALID_CATEGORY")
    if _text(record.get("severity")) not in SEVERITIES:
        flags.append("INVALID_SEVERITY")
    if _text(record.get("status")) not in STATUSES:
        flags.append("INVALID_STATUS")

    coordinates = _coordinate_pair(record)
    if coordinates is not None:
        latitude, longitude = coordinates
        if not (
            math.isfinite(latitude) and math.isfinite(longitude)
            and -90 <= latitude <= 90 and -180 <= longitude <= 180
        ):
            flags.append("INVALID_COORDINATES")

    if peer_records and _duplicate_suspected(record, peer_records):
        flags.append("DUPLICATE_SUSPECTED")

    if record.get("status") == "Received":
        flags.append("NEEDS_REVIEW")

    if not flags:
        flags.append("VALID")
    return {
        "quality_status": "PASS" if flags == ["VALID"] else "REVIEW",
        "flags": flags,
        "human_review_required": True,
        "environmental_truth_claim": False,
        "regulatory_conclusion": False,
        "automatic_enforcement": False,
    }


def _duplicate_suspected(
    record: Mapping[str, Any],
    peers: Sequence[Mapping[str, Any]],
) -> bool:
    site = _text(record.get("district_or_site")).casefold()
    category = record.get("category")
    observation_date = record.get("observation_date")
    description = _text(record.get("description")).casefold()
    if not site or not description:
        return False

    for peer in peers:
        if peer.get("case_id") == record.get("case_id"):
            continue
        if (
            _text(peer.get("district_or_site")).casefold() != site
            or peer.get("category") != category
            or peer.get("observation_date") != observation_date
        ):
            continue
        other_description = _text(peer.get("description")).casefold()
        if other_description and (
            description == other_description
            or _token_overlap(description, other_description) >= 0.8
        ):
            return True
    return False


def _token_overlap(a: str, b: str) -> float:
    left, right = set(a.split()), set(b.split())
    if not left or not right:
        return 0.0
    return len(left & right) / min(len(left), len(right))
