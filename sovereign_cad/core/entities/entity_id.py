from __future__ import annotations

from uuid import UUID, uuid4


def create_entity_id() -> UUID:
    return uuid4()


def is_valid_entity_id(value) -> bool:
    if isinstance(value, UUID):
        return True

    if not isinstance(value, str):
        return False

    try:
        UUID(value)
        return True
    except (ValueError, TypeError, AttributeError):
        return False


__all__ = [
    "create_entity_id",
    "is_valid_entity_id",
]
