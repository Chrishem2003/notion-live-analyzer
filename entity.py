from __future__ import annotations

from dataclasses import dataclass, field
from math import hypot
from typing import Optional
from uuid import UUID, uuid4

from sovereign_cad.core.geometry import Point2, BoundingBox2


def new_entity_id() -> UUID:
    """Create a new unique entity ID."""
    return uuid4()


def is_valid_entity_id(value) -> bool:
    """Return True when value is a valid UUID entity ID."""
    return isinstance(value, UUID)


@dataclass
class Entity:
    """Base class for all CAD entities."""

    entity_id: UUID = field(default_factory=new_entity_id)
    layer: str = "0"
    visible: bool = True
    selected: bool = False

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


@dataclass
class LineEntity(Entity):
    """2D line entity."""

    start: Point2 = field(default_factory=lambda: Point2(0.0, 0.0))
    end: Point2 = field(default_factory=lambda: Point2(1.0, 0.0))

    @property
    def entity_type(self) -> str:
        return "LINE"

    @property
    def length(self) -> float:
        return hypot(
            self.end.x - self.start.x,
            self.end.y - self.start.y,
        )

    def bounding_box(self) -> BoundingBox2:
        return BoundingBox2(
            min_x=min(self.start.x, self.end.x),
            min_y=min(self.start.y, self.end.y),
            max_x=max(self.start.x, self.end.x),
            max_y=max(self.start.y, self.end.y),
        )


@dataclass
class CircleEntity(Entity):
    """2D circle entity."""

    center: Point2 = field(default_factory=lambda: Point2(0.0, 0.0))
    radius: float = 1.0

    @property
    def entity_type(self) -> str:
        return "CIRCLE"

    def __post_init__(self) -> None:
        if self.radius <= 0:
            raise ValueError("Circle radius must be greater than zero.")

    def bounding_box(self) -> BoundingBox2:
        return BoundingBox2(
            min_x=self.center.x - self.radius,
            min_y=self.center.y - self.radius,
            max_x=self.center.x + self.radius,
            max_y=self.center.y + self.radius,
        )


class EntityRegistry:
    """Registry for managing entities by UUID."""

    def __init__(self) -> None:
        self._entities: dict[UUID, Entity] = {}

    def add(self, entity: Entity) -> UUID:
        self._entities[entity.entity_id] = entity
        return entity.entity_id

    def remove(self, entity_id: UUID) -> Optional[Entity]:
        return self._entities.pop(entity_id, None)

    def get(self, entity_id: UUID) -> Optional[Entity]:
        return self._entities.get(entity_id)

    def clear(self) -> None:
        self._entities.clear()

    def __len__(self) -> int:
        return len(self._entities)

    def values(self):
        return self._entities.values()

    def items(self):
        return self._entities.items()