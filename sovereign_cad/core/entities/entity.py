from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from sovereign_cad.core.geometry import BoundingBox2


def new_entity_id() -> UUID:
    return uuid4()


def is_valid_entity_id(value) -> bool:
    return isinstance(value, UUID)


@dataclass
class Entity:
    """
    Base class for all SovereignCAD entities.

    entity_id is the canonical identity field.
    id is retained as a compatibility alias.
    """

    entity_id: UUID = field(default_factory=new_entity_id)
    layer: str = "0"
    visible: bool = True
    selected: bool = False

    @property
    def id(self) -> UUID:
        """
        Backward-compatible alias for entity_id.
        """
        return self.entity_id

    @property
    def entity_type(self) -> str:
        return "ENTITY"

    def select(self) -> None:
        self.selected = True

    def deselect(self) -> None:
        self.selected = False

    def set_layer(self, layer: str) -> None:
        if not isinstance(layer, str) or not layer.strip():
            raise ValueError("Layer must be a non-empty string.")

        self.layer = layer

    def bounding_box(self) -> BoundingBox2:
        raise NotImplementedError

    def clone(self):
        raise NotImplementedError
