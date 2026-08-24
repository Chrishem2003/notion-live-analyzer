from __future__ import annotations

from dataclasses import dataclass, field
from math import hypot

from ..geometry import BoundingBox2, LineSegment2, Point2
from .entity import Entity


@dataclass
class LineEntity(Entity):
    start: Point2 = field(
        default_factory=lambda: Point2(0.0, 0.0)
    )
    end: Point2 = field(
        default_factory=lambda: Point2(1.0, 0.0)
    )

    @property
    def entity_type(self) -> str:
        return "LINE"

    @property
    def length(self) -> float:
        return hypot(
            self.end.x - self.start.x,
            self.end.y - self.start.y,
        )

    def geometry(self) -> LineSegment2:
        return LineSegment2(
            self.start,
            self.end,
        )

    def bounding_box(self) -> BoundingBox2:
        return BoundingBox2(
            min_x=min(self.start.x, self.end.x),
            min_y=min(self.start.y, self.end.y),
            max_x=max(self.start.x, self.end.x),
            max_y=max(self.start.y, self.end.y),
        )

    def clone(self) -> LineEntity:
        return LineEntity(
            start=self.start,
            end=self.end,
            entity_id=self.entity_id,
            layer=self.layer,
            visible=self.visible,
            selected=self.selected,
        )
