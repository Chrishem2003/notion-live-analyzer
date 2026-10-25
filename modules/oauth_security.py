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
