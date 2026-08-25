from __future__ import annotations

from uuid import UUID

from ..entities import Entity
from ..geometry import BoundingBox2, Point2


class SpatialIndex:

    def __init__(self) -> None:
        self._boxes: dict[UUID, BoundingBox2] = {}

    def clear(self) -> None:
        self._boxes.clear()

    def insert(self, entity: Entity) -> None:
        self._boxes[entity.entity_id] = entity.bounding_box()

    def remove(self, entity_id: UUID) -> None:
        self._boxes.pop(entity_id, None)

    def update(self, entity: Entity) -> None:
        self.insert(entity)

    def rebuild(self, entities) -> None:

        self.clear()

        if hasattr(entities, "all"):
            entities = entities.all()

        elif hasattr(entities, "values"):
            entities = entities.values()

        for entity in entities:
            self.insert(entity)

    def get_box(
        self,
        entity_id: UUID,
    ) -> BoundingBox2 | None:

        return self._boxes.get(entity_id)

    def query_box(
        self,
        box: BoundingBox2,
    ) -> list[UUID]:

        return [
            entity_id
            for entity_id, entity_box in self._boxes.items()
            if entity_box.intersects(box)
        ]

    def query_point(
        self,
        point: Point2,
    ) -> list[UUID]:

        return [
            entity_id
            for entity_id, entity_box in self._boxes.items()
            if entity_box.contains(point)
        ]

    def __len__(self) -> int:
        return len(self._boxes)
