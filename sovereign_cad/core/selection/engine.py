﻿from __future__ import annotations

from ..entities import EntityRegistry
from ..geometry import BoundingBox2, Point2
from ..spatial import SpatialIndex


class SelectionEngine:

    def __init__(
        self,
        registry: EntityRegistry,
        spatial_index: SpatialIndex,
    ):

        self.registry = registry
        self.spatial_index = spatial_index

    def clear(self) -> None:
        self.registry.clear_selection()

    def select(self, entity_id) -> None:
        self.registry.select(entity_id)

    def deselect(self, entity_id) -> None:
        self.registry.deselect(entity_id)

    def selected(self):
        return self.registry.selected()

    def pick(self, point: Point2) -> list:

        ids = self.spatial_index.query_point(point)

        entities = []

        for entity_id in ids:

            entity = self.registry.get(entity_id)

            if entity is not None and entity.visible:
                entities.append(entity)

        return entities

    def window_select(
        self,
        box: BoundingBox2,
        crossing: bool = True,
    ) -> list:

        if crossing:

            ids = self.spatial_index.query_box(box)

        else:

            ids = []

            for entity in self.registry.visible():

                entity_box = entity.bounding_box()

                if (
                    entity_box.min_x >= box.min_x
                    and entity_box.max_x <= box.max_x
                    and entity_box.min_y >= box.min_y
                    and entity_box.max_y <= box.max_y
                ):
                    ids.append(entity.entity_id)

        return [
            self.registry.get(entity_id)
            for entity_id in ids
            if self.registry.get(entity_id) is not None
        ]

    def apply_selection(
        self,
        entities,
        additive: bool = False,
    ) -> None:

        if not additive:
            self.clear()

        for entity in entities:
            entity.selected = True
