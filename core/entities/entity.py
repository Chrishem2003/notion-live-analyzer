from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from ..geometry import (
    BoundingBox2,
    Circle2,
    LineSegment2,
    Point2,
    Vector2,
)


@dataclass(kw_only=True)
class Entity:

    entity_id: UUID = field(default_factory=uuid4)
    layer: str = "default"
    visible: bool = True
    selected: bool = False

    @property
    def id(self) -> UUID:
        return self.entity_id

    @property
    def entity_type(self) -> str:
        return type(self).__name__.replace("Entity", "").lower()

    def select(self) -> None:
        self.selected = True

    def deselect(self) -> None:
        self.selected = False

    def is_selected(self) -> bool:
        return self.selected

    def set_layer(self, layer: str) -> None:
        self.layer = layer.strip()

    def geometry(self):
        raise NotImplementedError

    def bounding_box(self) -> BoundingBox2:
        raise NotImplementedError

    def clone(self):
        raise NotImplementedError

    def translate(self, dx: float, dy: float) -> None:
        """Move this entity in place by (dx, dy). Mutates the entity's own
        geometry fields (entities aren't frozen dataclasses) rather than
        replacing it in the registry, so selection/entity_id survive a
        move intact - subclasses implement this since each stores its
        geometry differently (endpoints vs center+radius vs corners)."""
        raise NotImplementedError


@dataclass
class LineEntity(Entity):

    start: Point2 = field(
        default_factory=lambda: Point2(0.0, 0.0)
    )

    end: Point2 = field(
        default_factory=lambda: Point2(1.0, 0.0)
    )

    def geometry(self) -> LineSegment2:
        return LineSegment2(
            self.start,
            self.end,
        )

    @property
    def length(self) -> float:
        return self.start.distance_to(self.end)

    def bounding_box(self) -> BoundingBox2:
        return BoundingBox2.from_points(
            [
                self.start,
                self.end,
            ]
        )

    def translate(self, dx: float, dy: float) -> None:
        v = Vector2(dx, dy)
        self.start = self.start + v
        self.end = self.end + v

    def clone(self) -> "LineEntity":
        return LineEntity(
            self.start,
            self.end,
            entity_id=self.entity_id,
            layer=self.layer,
            visible=self.visible,
            selected=self.selected,
        )


@dataclass
class CircleEntity(Entity):

    center: Point2 = field(
        default_factory=lambda: Point2(0.0, 0.0)
    )

    radius: float = 1.0

    def geometry(self) -> Circle2:
        return Circle2(
            self.center,
            self.radius,
        )

    def bounding_box(self) -> BoundingBox2:
        return BoundingBox2(
            self.center.x - self.radius,
            self.center.y - self.radius,
            self.center.x + self.radius,
            self.center.y + self.radius,
        )

    def translate(self, dx: float, dy: float) -> None:
        self.center = self.center + Vector2(dx, dy)

    def clone(self) -> "CircleEntity":
        return CircleEntity(
            self.center,
            self.radius,
            entity_id=self.entity_id,
            layer=self.layer,
            visible=self.visible,
            selected=self.selected,
        )


@dataclass
class RectangleEntity(Entity):
    """Axis-aligned rectangle defined by two opposite corners - the most
    common missing basic shape in a minimal CAD tool. Stored as two
    corners (not width/height) so it stays correct under arbitrary
    corner order, matching how a user actually drags a rectangle."""

    corner1: Point2 = field(
        default_factory=lambda: Point2(0.0, 0.0)
    )

    corner2: Point2 = field(
        default_factory=lambda: Point2(1.0, 1.0)
    )

    @property
    def min_corner(self) -> Point2:
        return Point2(min(self.corner1.x, self.corner2.x), min(self.corner1.y, self.corner2.y))

    @property
    def max_corner(self) -> Point2:
        return Point2(max(self.corner1.x, self.corner2.x), max(self.corner1.y, self.corner2.y))

    @property
    def width(self) -> float:
        return abs(self.corner2.x - self.corner1.x)

    @property
    def height(self) -> float:
        return abs(self.corner2.y - self.corner1.y)

    def geometry(self) -> tuple[LineSegment2, LineSegment2, LineSegment2, LineSegment2]:
        c1, c3 = self.min_corner, self.max_corner
        c2 = Point2(c3.x, c1.y)
        c4 = Point2(c1.x, c3.y)
        return (
            LineSegment2(c1, c2),
            LineSegment2(c2, c3),
            LineSegment2(c3, c4),
            LineSegment2(c4, c1),
        )

    def bounding_box(self) -> BoundingBox2:
        return BoundingBox2(self.min_corner.x, self.min_corner.y, self.max_corner.x, self.max_corner.y)

    def translate(self, dx: float, dy: float) -> None:
        v = Vector2(dx, dy)
        self.corner1 = self.corner1 + v
        self.corner2 = self.corner2 + v

    def clone(self) -> "RectangleEntity":
        return RectangleEntity(
            self.corner1,
            self.corner2,
            entity_id=self.entity_id,
            layer=self.layer,
            visible=self.visible,
            selected=self.selected,
        )


@dataclass
class ArcEntity(Entity):
    """Circular arc from start_angle to end_angle (radians, CCW), center
    + radius like CircleEntity so it shares the same mental model."""

    center: Point2 = field(
        default_factory=lambda: Point2(0.0, 0.0)
    )

    radius: float = 1.0

    start_angle: float = 0.0

    end_angle: float = 1.5707963267948966

    def geometry(self) -> Circle2:
        return Circle2(self.center, self.radius)

    @property
    def sweep_angle(self) -> float:
        import math
        sweep = self.end_angle - self.start_angle
        while sweep <= 0:
            sweep += 2 * math.pi
        return sweep

    def endpoint_start(self) -> Point2:
        import math
        return Point2(
            self.center.x + self.radius * math.cos(self.start_angle),
            self.center.y + self.radius * math.sin(self.start_angle),
        )

    def endpoint_end(self) -> Point2:
        import math
        return Point2(
            self.center.x + self.radius * math.cos(self.end_angle),
            self.center.y + self.radius * math.sin(self.end_angle),
        )

    def bounding_box(self) -> BoundingBox2:
        return BoundingBox2(
            self.center.x - self.radius, self.center.y - self.radius,
            self.center.x + self.radius, self.center.y + self.radius,
        )

    def translate(self, dx: float, dy: float) -> None:
        self.center = self.center + Vector2(dx, dy)

    def clone(self) -> "ArcEntity":
        return ArcEntity(
            self.center, self.radius, self.start_angle, self.end_angle,
            entity_id=self.entity_id,
            layer=self.layer,
            visible=self.visible,
            selected=self.selected,
        )


@dataclass
class PolylineEntity(Entity):
    """Connected sequence of line segments through 2+ points - the
    fundamental shape for real drafting (outlines, paths, floor plans)
    that a CAD tool with only line/circle/rectangle/arc can't express
    without manually placing dozens of separate line entities."""

    points: list[Point2] = field(default_factory=list)

    closed: bool = False

    def __post_init__(self):
        if len(self.points) < 2:
            raise ValueError("PolylineEntity needs at least 2 points.")

    def geometry(self) -> list:
        segs = [
            LineSegment2(self.points[i], self.points[i + 1])
            for i in range(len(self.points) - 1)
        ]
        if self.closed and len(self.points) > 2:
            segs.append(LineSegment2(self.points[-1], self.points[0]))
        return segs

    @property
    def total_length(self) -> float:
        return sum(seg.length for seg in self.geometry())

    def bounding_box(self) -> BoundingBox2:
        return BoundingBox2.from_points(self.points)

    def translate(self, dx: float, dy: float) -> None:
        v = Vector2(dx, dy)
        self.points = [p + v for p in self.points]

    def add_point(self, point: Point2) -> None:
        self.points.append(point)

    def clone(self) -> "PolylineEntity":
        return PolylineEntity(
            list(self.points),
            self.closed,
            entity_id=self.entity_id,
            layer=self.layer,
            visible=self.visible,
            selected=self.selected,
        )


__all__ = [
    "Entity",
    "LineEntity",
    "CircleEntity",
    "RectangleEntity",
    "ArcEntity",
    "PolylineEntity",
]
