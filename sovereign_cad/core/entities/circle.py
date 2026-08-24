from __future__ import annotations

from dataclasses import dataclass, field

from ..geometry import BoundingBox2, Circle2, Point2
from .entity import Entity


@dataclass
class CircleEntity(Entity):
    center: Point2 = field(
        default_factory=lambda: Point2(0.0, 0.0)
    )
    radius: float = 1.0

    @property
    def entity_type(self) -> str:
        return "CIRCLE"

    def __post_init__(self) -> None:
        if self.radius <= 0:
            raise ValueError(
                "Circle radius must be greater than zero."
            )

    def geometry(self) -> Circle2:
        return Circle2(
            self.center,
            self.radius,
        )

    def bounding_box(self) -> BoundingBox2:
        return BoundingBox2(
            min_x=self.center.x - self.radius,
            min_y=self.center.y - self.radius,
            max_x=self.center.x + self.radius,
            max_y=self.center.y + self.radius,
        )

    def clone(self) -> CircleEntity:
        return CircleEntity(
            center=self.center,
            radius=self.radius,
            entity_id=self.entity_id,
            layer=self.layer,
            visible=self.visible,
            selected=self.selected,
        )
