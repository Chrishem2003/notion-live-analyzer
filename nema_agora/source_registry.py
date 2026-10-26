"""Registry of real-world environmental information sources for NEMA-AGORA.

This is a source catalogue, not a live integration. Entries describe authoritative
public pages or portals discovered during project research; no source is marked
as connected until an actual adapter, permission basis, and refresh verification
exist. Keep source provenance explicit so public references are not mistaken for
machine-ingested data.
"""
from __future__ import annotations

from typing import Any

POLICY_VERSION = "source-registry-v1"

SOURCES: tuple[dict[str, Any], ...] = (
    {
        "source_id": "UG-NEMA-ACT-CAP181",
        "title": "National Environment Act, Cap. 181",
        "publisher": "Uganda Legal Resources Centre",
        "url": "https://publications.ulrc.go.ug/laws-of-uganda/31/acts/294",
        "source_type": "legislation_reference",
        "intended_use": "Policy and workflow design reference; legal text must be reviewed in its current official form.",
        "integration_status": "reference_only",
        "machine_endpoint_verified": False,
        "automated_ingestion_enabled": False,
        "limitations": ["Not legal advice", "No live legislative change monitoring"],
    },
    {
        "source_id": "UG-NEMA-NERA-2024-2029",
        "title": "National Environment Research Agenda 2024/25–2028/29",
        "publisher": "National Environment Management Authority",
        "url": "https://www.nema.go.ug/en/research/",
        "source_type": "research_priority_reference",
        "intended_use": "Align research and evidence workflows to published national environmental research priorities.",
        "integration_status": "reference_only",
        "machine_endpoint_verified": False,
        "automated_ingestion_enabled": False,
        "limitations": ["Public page reference only", "No structured API confirmed"],
    },
    {
        "source_id": "UG-NEMA-NSOER-2024",
        "title": "National State of the Environment Report 2024",
        "publisher": "National Environment Management Authority",
        "url": "https://www.nema.go.ug/en/wp-content/uploads/2025/10/National-Status-of-the-Environment-Report-NSOER-2024.pdf",
        "source_type": "environmental_baseline_report",
        "intended_use": "Contextual baseline and research reference; statistics must retain report year and method.",
        "integration_status": "reference_only",
        "machine_endpoint_verified": False,
        "automated_ingestion_enabled": False,
        "limitations": ["Report values are not live observations", "Comparisons require matching definitions and periods"],
    },
    {
        "source_id": "UG-MWE-WEIS-WETLANDS",
        "title": "Water and Environment Information System / National Wetland Information",
        "publisher": "Uganda Ministry of Water and Environment",
        "url": "https://weis.mwe.go.ug/",
        "source_type": "government_geospatial_portal",
        "intended_use": "Potential reference for wetland inventory and monitoring context; obtain permission and confirm data access terms before integration.",
        "integration_status": "reference_only",
        "machine_endpoint_verified": False,
        "automated_ingestion_enabled": False,
        "limitations": ["Portal availability does not establish an API", "No automated download or data licence has been verified"],
    },
    {
        "source_id": "COPERNICUS-SENTINEL-2",
        "title": "Copernicus Data Space Ecosystem",
        "publisher": "European Union / Copernicus",
        "url": "https://dataspace.copernicus.eu/",
        "source_type": "satellite_data_catalogue",
        "intended_use": "Potential source for Sentinel-2 imagery after acquisition method, credentials, licensing, scene metadata, cloud quality and reproducibility are implemented.",
        "integration_status": "reference_only",
        "machine_endpoint_verified": False,
        "automated_ingestion_enabled": False,
        "limitations": ["No live imagery acquisition is claimed by this registry", "Satellite indicators are not by themselves proof of a violation"],
    },
)

_REQUIRED = (
    "source_id", "title", "publisher", "url", "source_type",
    "intended_use", "integration_status", "machine_endpoint_verified",
    "automated_ingestion_enabled", "limitations",
)


def validate_source_registry(sources: Any = SOURCES) -> dict[str, Any]:
    """Validate source catalogue shape and prevent unsupported connected claims."""
    findings: list[dict[str, str]] = []
    if not isinstance(sources, (tuple, list)):
        return {"policy_version": POLICY_VERSION, "state": "CONTROL_REQUIRED",
                "findings": [{"code": "INVALID_SOURCE_COLLECTION"}]}
    seen: set[str] = set()
    for index, source in enumerate(sources):
        prefix = f"SOURCE_{index}"
        if not isinstance(source, dict):
            findings.append({"code": f"{prefix}_NOT_AN_OBJECT"})
            continue
        for field in _REQUIRED:
            if field not in source:
                findings.append({"code": f"{prefix}_MISSING_{field.upper()}"})
        source_id = source.get("source_id")
        if not isinstance(source_id, str) or not source_id.strip():
            findings.append({"code": f"{prefix}_INVALID_ID"})
        elif source_id in seen:
            findings.append({"code": f"{prefix}_DUPLICATE_ID"})
        else:
            seen.add(source_id)
        url = source.get("url")
        if not isinstance(url, str) or not url.startswith("https://"):
            findings.append({"code": f"{prefix}_URL_NOT_HTTPS"})
        if source.get("integration_status") != "reference_only":
            findings.append({"code": f"{prefix}_UNVERIFIED_INTEGRATION_STATUS"})
        if source.get("machine_endpoint_verified") is not False:
            findings.append({"code": f"{prefix}_UNVERIFIED_ENDPOINT_CLAIM"})
        if source.get("automated_ingestion_enabled") is not False:
            findings.append({"code": f"{prefix}_UNVERIFIED_INGESTION_CLAIM"})
        if not isinstance(source.get("limitations"), list) or not source.get("limitations"):
            findings.append({"code": f"{prefix}_LIMITATIONS_REQUIRED"})
    return {
        "policy_version": POLICY_VERSION,
        "state": "VALID" if not findings else "CONTROL_REQUIRED",
        "source_count": len(sources),
        "findings": findings,
    }


def list_sources(*, source_type: str | None = None) -> list[dict[str, Any]]:
    """Return copies of catalogue entries, optionally filtered by source type."""
    return [
        dict(source, limitations=list(source["limitations"]))
        for source in SOURCES
        if source_type is None or source.get("source_type") == source_type
    ]
