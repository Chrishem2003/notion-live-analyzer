from __future__ import annotations

from uuid import UUID

from .entity import (
    Entity,
    LineEntity,
    CircleEntity,
)

from .entity_id import (
    create_entity_id,
    is_valid_entity_id,
)


class EntityRegistry:

    def __init__(self):
        self._entities: dict[UUID, Entity] = {}

    def add(self, entity: Entity) -> UUID:

        if entity.entity_id in self._entities:
            raise ValueError(
                f"Entity {entity.entity_id} already exists."
            )

        self._entities[entity.entity_id] = entity

        return entity.entity_id

    def remove(self, entity_id: UUID) -> Entity:

        if entity_id not in self._entities:
            raise KeyError(
                f"Entity {entity_id} does not exist."
            )

        return self._entities.pop(entity_id)

    def get(self, entity_id: UUID) -> Entity | None:
        return self._entities.get(entity_id)

    def all(self) -> list[Entity]:
        return list(self._entities.values())

    def visible(self) -> list[Entity]:
        return [
            entity
            for entity in self._entities.values()
            if entity.visible
        ]

    def selected(self) -> list[Entity]:
        return [
            entity
            for entity in self._entities.values()
            if entity.selected
        ]

    def clear_selection(self) -> None:
        for entity in self._entities.values():
            entity.selected = False

    def select(self, entity_id: UUID) -> None:

        entity = self.get(entity_id)

        if entity is None:
            raise KeyError(
                f"Entity {entity_id} does not exist."
            )

        entity.selected = True

    def deselect(self, entity_id: UUID) -> None:

        entity = self.get(entity_id)

        if entity is None:
            raise KeyError(
                f"Entity {entity_id} does not exist."
            )

        entity.selected = False

    def __len__(self) -> int:
        return len(self._entities)

    def __iter__(self):
        return iter(self._entities.values())


__all__ = [
    "Entity",
    "LineEntity",
    "CircleEntity",
    "EntityRegistry",
    "create_entity_id",
    "is_valid_entity_id",
]
