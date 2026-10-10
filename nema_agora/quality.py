"""Deterministic data-quality checks for NEMA-AGORA observations.

Quality flags are advisory workflow signals. They never establish that an
environmental incident is true, illegal, urgent, or regulatorily confirmed.
"""
from __future__ import annotations

from datetime import date

REQUIRED_FIELDS = ("case_id","observation_date","category","severity","district_or_site","description","status")
QUALITY_FLAGS = (
    "VALID","INCOMPLETE","INVALID_COORDINATES","MISSING_DESCRIPTION",
    "MISSING_CONSENT","DUPLICATE_SUSPECTED","NEEDS_REVIEW",
)

def assess_observation(record: dict, *, peer_records: list[dict] | None = None) -> dict:
    flags: list[str] = []
    missing = [field for field in REQUIRED_FIELDS if not str(record.get(field, "")).strip()]
    if missing:
        flags.append("INCOMPLETE")
    if not str(record.get("description", "")).strip():
        flags.append("MISSING_DESCRIPTION")
    if record.get("consent_confirmed") is not True:
        flags.append("MISSING_CONSENT")

    lat, lon = record.get("latitude", ""), record.get("longitude", "")
    if lat != "" or lon != "":
        try:
            valid = -90 <= float(lat) <= 90 and -180 <= float(lon) <= 180
        except (TypeError, ValueError):
            valid = False
        if not valid:
            flags.append("INVALID_COORDINATES")

    if peer_records:
        if _duplicate_suspected(record, peer_records):
            flags.append("DUPLICATE_SUSPECTED")

    if record.get("status") == "Received":
        flags.append("NEEDS_REVIEW")

    if not flags:
        flags.append("VALID")
    return {"quality_status": "PASS" if flags == ["VALID"] else "REVIEW", "flags": flags}

def _duplicate_suspected(record: dict, peers: list[dict]) -> bool:
    for peer in peers:
        if peer.get("case_id") == record.get("case_id"):
            continue
        if (peer.get("district_or_site","").strip().casefold() != record.get("district_or_site","").strip().casefold()
            or peer.get("category") != record.get("category")
            or peer.get("observation_date") != record.get("observation_date")):
            continue
        a = str(record.get("description","")).strip().casefold()
        b = str(peer.get("description","")).strip().casefold()
        if a and b and (a == b or _token_overlap(a,b) >= 0.8):
            return True
    return False

def _token_overlap(a: str, b: str) -> float:
    left, right = set(a.split()), set(b.split())
    if not left or not right:
        return 0.0
    return len(left & right) / max(1, min(len(left), len(right)))
