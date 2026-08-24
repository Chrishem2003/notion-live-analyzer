from __future__ import annotations

from uuid import UUID, uuid4


def new_entity_id() -> UUID:
    """Create a new unique entity ID."""
    return uuid4()


def is_valid_entity_id(value) -> bool:
    """Return True when value is a valid UUID entity ID."""
    if isinstance(value, UUID):
        return True

    if not isinstance(value, str):
        return False

    try:
        UUID(value)
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def normalize_entity_id(value) -> UUID:
    """Convert a UUID/string into a UUID object."""
    if isinstance(value, UUID):
        return value

    if isinstance(value, str):
        try:
            return UUID(value)
        except ValueError as exc:
            raise ValueError(f"Invalid entity ID: {value}") from exc

    raise TypeError("Entity ID must be a UUID or UUID string.")
