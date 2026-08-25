from __future__ import annotations

from uuid import UUID

from sovereign_cad.core.entities import Entity
from sovereign_cad.core.document.layer import Layer


class Document:
    """
    CAD document containing entities and layers.
    """

    def __init__(self) -> None:

        self.entities: dict[UUID, Entity] = {}

        self.layers: dict[str, Layer] = {
            "0": Layer("0")
        }

        self.active_layer = "0"

    # --------------------------------------------------------
    # Layers
    # --------------------------------------------------------

    def add_layer(self, name: str) -> Layer:

        if not name:
            raise ValueError("Layer name cannot be empty.")

        if name in self.layers:
            raise ValueError(f"Layer already exists: {name}")

        layer = Layer(name)

        self.layers[name] = layer

        return layer

    def remove_layer(self, name: str) -> None:

        if name == "0":
            raise ValueError("Default layer cannot be removed.")

        if name not in self.layers:
            raise KeyError(name)

        if any(entity.layer == name for entity in self.entities.values()):
            raise ValueError(
                f"Cannot remove layer '{name}' because it contains entities."
            )

        del self.layers[name]

        if self.active_layer == name:
            self.active_layer = "0"

    def set_active_layer(self, name: str) -> None:

        if name not in self.layers:
            raise KeyError(name)

        if not self.layers[name].visible:
            raise ValueError(
                f"Cannot activate hidden layer: {name}"
            )

        self.active_layer = name

    # --------------------------------------------------------
    # Entities
    # --------------------------------------------------------

    def add_entity(self, entity: Entity) -> UUID:

        if entity.entity_id in self.entities:
            raise ValueError(
                f"Entity already exists: {entity.entity_id}"
            )

        if entity.layer not in self.layers:
            self.layers[entity.layer] = Layer(entity.layer)

        self.entities[entity.entity_id] = entity

        return entity.entity_id

    def remove_entity(self, entity_id: UUID) -> Entity:

        if entity_id not in self.entities:
            raise KeyError(entity_id)

        return self.entities.pop(entity_id)

    def get_entity(self, entity_id: UUID) -> Entity | None:

        return self.entities.get(entity_id)

    def clear(self) -> None:

        self.entities.clear()

    # --------------------------------------------------------
    # Selection
    # --------------------------------------------------------

    def select_entity(self, entity_id: UUID) -> None:

        entity = self.get_entity(entity_id)

        if entity is None:
            raise KeyError(entity_id)

        entity.select()

    def deselect_all(self) -> None:

        for entity in self.entities.values():
            entity.deselect()

    def selected_entities(self) -> list[Entity]:

        return [
            entity
            for entity in self.entities.values()
            if entity.selected
        ]

    # --------------------------------------------------------
    # Queries
    # --------------------------------------------------------

    @property
    def entity_count(self) -> int:
        return len(self.entities)

    @property
    def layer_count(self) -> int:
        return len(self.layers)
