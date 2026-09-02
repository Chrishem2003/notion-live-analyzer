from __future__ import annotations

from uuid import UUID

from .entity import (
    Entity,
    LineEntity,
    CircleEntity,
    RectangleEntity,
    ArcEntity,
    PolylineEntity,
)

from .entity_id import (
    create_entity_id,
    is_valid_entity_id,
)


class EntityRegistry:

    def __init__(self):
        self._entities: dict[UUID, Entity] = {}
        # Layers a user has explicitly created, even if currently empty -
        # so a newly-made layer shows up in the UI before anything's been
        # drawn on it yet, and a layer isn't silently forgotten once its
        # last entity is deleted.
        self._known_layers: set[str] = {"default"}
        self._hidden_layers: set[str] = set()

    def add(self, entity: Entity) -> UUID:

        if entity.entity_id in self._entities:
            raise ValueError(
                f"Entity {entity.entity_id} already exists."
            )

        self._entities[entity.entity_id] = entity
        self._known_layers.add(entity.layer)
        if entity.layer in self._hidden_layers:
            entity.visible = False

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
            entity.deselect()

    def select(self, entity_id: UUID) -> None:
        entity = self.get(entity_id)
        if entity is None:
            raise KeyError(f"Entity {entity_id} does not exist.")
        entity.select()

    def deselect(self, entity_id: UUID) -> None:
        entity = self.get(entity_id)
        if entity is None:
            raise KeyError(f"Entity {entity_id} does not exist.")
        entity.deselect()

    # ------------------------------------------------------------------
    # Layers
    # ------------------------------------------------------------------

    def create_layer(self, name: str) -> None:
        name = name.strip()
        if name:
            self._known_layers.add(name)

    def layers(self) -> list[str]:
        """All layer names that exist, whether or not anything is
        currently drawn on them - sorted, 'default' always first."""
        names = sorted(self._known_layers | {e.layer for e in self._entities.values()})
        if "default" in names:
            names.remove("default")
            names.insert(0, "default")
        return names

    def entities_on_layer(self, layer_name: str) -> list[Entity]:
        return [e for e in self._entities.values() if e.layer == layer_name]

    def rename_layer(self, old_name: str, new_name: str) -> int:
        """Renames a layer, including reassigning every entity currently
        on it. Returns the number of entities moved."""
        new_name = new_name.strip()
        if not new_name:
            raise ValueError("New layer name can't be empty.")
        moved = 0
        for entity in self._entities.values():
            if entity.layer == old_name:
                entity.set_layer(new_name)
                moved += 1
        self._known_layers.discard(old_name)
        self._known_layers.add(new_name)
        if old_name in self._hidden_layers:
            self._hidden_layers.discard(old_name)
            self._hidden_layers.add(new_name)
        return moved

    def set_layer_visibility(self, layer_name: str, visible: bool) -> int:
        """Shows/hides every entity on a layer at once. Returns the count
        of entities affected. The hidden/visible state is remembered per
        layer even when empty, so a newly-added entity on a hidden layer
        starts hidden too (handled in add() above)."""
        if visible:
            self._hidden_layers.discard(layer_name)
        else:
            self._hidden_layers.add(layer_name)
        count = 0
        for entity in self._entities.values():
            if entity.layer == layer_name:
                entity.visible = visible
                count += 1
        return count

    def is_layer_visible(self, layer_name: str) -> bool:
        return layer_name not in self._hidden_layers

    def delete_layer(self, layer_name: str, reassign_to: str = "default") -> int:
        """Deletes a layer, moving any entities on it to reassign_to
        (never silently deletes entities just because their layer went
        away). Returns the count of entities reassigned."""
        if layer_name == "default":
            raise ValueError("Can't delete the default layer.")
        moved = 0
        for entity in self._entities.values():
            if entity.layer == layer_name:
                entity.set_layer(reassign_to)
                moved += 1
        self._known_layers.discard(layer_name)
        self._hidden_layers.discard(layer_name)
        return moved

    def __len__(self) -> int:
        return len(self._entities)

    def __iter__(self):
        return iter(self._entities.values())


__all__ = [
    "Entity",
    "LineEntity",
    "CircleEntity",
    "RectangleEntity",
    "ArcEntity",
    "PolylineEntity",
    "EntityRegistry",
    "create_entity_id",
    "is_valid_entity_id",
]
