"""Security helpers for OAuth profile validation."""
from __future__ import annotations
from typing import Any


def verified_google_profile(data: dict[str, Any]) -> dict[str, str | None]:
    """Return a usable Google profile only when Google confirms email ownership."""
    if data.get("email_verified") is not True:
        return {"email": None, "name": None, "provider_id": data.get("sub")}
    email = data.get("email")
    if not isinstance(email, str) or not email.strip():
        return {"email": None, "name": None, "provider_id": data.get("sub")}
    return {
        "email": email.strip().lower(),
        "name": data.get("name") or email.split("@")[0],
        "provider_id": data.get("sub"),
    }


def verified_github_email(entries: Any) -> str | None:
    """Select only GitHub's explicitly primary and verified email address."""
    if not isinstance(entries, list):
        return None
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("primary") is not True or entry.get("verified") is not True:
            continue
        email = entry.get("email")
        if isinstance(email, str) and email.strip():
            return email.strip().lower()
    return None
