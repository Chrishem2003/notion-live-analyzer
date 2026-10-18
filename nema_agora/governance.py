"""Pilot governance configuration and validation.

This is a local policy gate for the student pilot; it is not legal, regulatory,
or institutional approval.
"""
from __future__ import annotations
from typing import Mapping

DEFAULT_SCOPE = {
    "allowed_categories": (
        "Solid waste / illegal dumping","Water pollution",
        "Wetland or land disturbance","Biodiversity / wildlife observation",
        "Air / noise pollution","Other environmental observation",
    ),
    "required_consent": True,
    "allow_personal_data": False,
    "allow_urgent_incidents": False,
    "official_integration_enabled": False,
}

def validate_governance(policy: Mapping[str, object]) -> list[str]:
    errors=[]
    for key in ("required_consent","allow_personal_data","allow_urgent_incidents","official_integration_enabled"):
        if not isinstance(policy.get(key), bool):
            errors.append(f"{key} must be explicitly true or false.")
    cats=policy.get("allowed_categories")
    if not isinstance(cats,(list,tuple)) or not cats:
        errors.append("allowed_categories must contain at least one category.")
    elif any(not isinstance(x,str) or not x.strip() for x in cats):
        errors.append("allowed_categories must contain non-empty names.")
    if policy.get("allow_personal_data") is True:
        errors.append("Personal-data collection is blocked by the pilot governance baseline.")
    if policy.get("allow_urgent_incidents") is True:
        errors.append("Urgent incident intake is outside the current pilot scope.")
    if policy.get("official_integration_enabled") is True:
        errors.append("Official integrations require separate written authorization and implementation.")
    return errors

def policy_from_secrets(secrets: Mapping[str, object]) -> dict:
    section=secrets.get("nema_agora",{})
    if not isinstance(section,Mapping):
        return dict(DEFAULT_SCOPE)
    result=dict(DEFAULT_SCOPE)
    if isinstance(section.get("allowed_categories"),(list,tuple)):
        result["allowed_categories"]=tuple(section["allowed_categories"])
    for key in ("required_consent","allow_personal_data","allow_urgent_incidents","official_integration_enabled"):
        if key in section:
            result[key]=section[key]
    return result
