"""Pure helpers for the NEMA-AGORA pilot workflow.

No Streamlit dependency: validation can be tested independently.
"""
from __future__ import annotations

from datetime import date
import uuid

STATUSES = ("Received", "Under review", "Referred", "Action recorded", "Closed")
CATEGORIES = (
    "Solid waste / illegal dumping",
    "Water pollution",
    "Wetland or land disturbance",
    "Biodiversity / wildlife observation",
    "Air / noise pollution",
    "Other environmental observation",
)
SEVERITIES = ("Low", "Moderate", "High", "Urgent")


def validate_observation(*, site: str, description: str, consent_confirmed: bool) -> list[str]:
    """Return actionable validation errors without raising for ordinary user input."""
    errors: list[str] = []
    if not site or not site.strip():
        errors.append("A district or site label is required.")
    if not description or not description.strip():
        errors.append("An observation description is required.")
    if len(description or "") > 1500:
        errors.append("The observation description must be 1,500 characters or fewer.")
    if not consent_confirmed:
        errors.append("Permission and data minimisation must be confirmed.")
    return errors


def new_case_id() -> str:
    """Create a short, human-readable case identifier."""
    return f"NA-{uuid.uuid4().hex[:8].upper()}"


def normalise_coordinates(latitude: float, longitude: float) -> tuple[float, float] | None:
    """Return valid non-default coordinates, or None when the UI's zero pair means omitted."""
    if not (-90 <= latitude <= 90):
        raise ValueError("Latitude must be between -90 and 90.")
    if not (-180 <= longitude <= 180):
        raise ValueError("Longitude must be between -180 and 180.")
    if latitude == 0.0 and longitude == 0.0:
        return None
    return float(latitude), float(longitude)


def make_observation(
    *,
    observation_date: date,
    category: str,
    severity: str,
    site: str,
    description: str,
    latitude: float,
    longitude: float,
    consent_confirmed: bool,
    created_at: str,
    evidence_reference: str = "",
) -> dict:
    """Validate and construct a session-level pilot observation record."""
    errors = validate_observation(
        site=site, description=description, consent_confirmed=consent_confirmed
    )
    if errors:
        raise ValueError(" ".join(errors))
    if category not in CATEGORIES:
        raise ValueError("Unknown observation category.")
    if severity not in SEVERITIES:
        raise ValueError("Unknown severity.")
    coordinates = normalise_coordinates(latitude, longitude)
    return {
        "case_id": new_case_id(),
        "created_at": created_at,
        "observation_date": observation_date.isoformat(),
        "category": category,
        "severity": severity,
        "district_or_site": site.strip(),
        "description": description.strip(),
        "latitude": coordinates[0] if coordinates else "",
        "longitude": coordinates[1] if coordinates else "",
        "status": "Received",
        "review_notes": "",
        "evidence_reference": (evidence_reference or "").strip(),
    }
