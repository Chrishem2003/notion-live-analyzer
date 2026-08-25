﻿from __future__ import annotations

from dataclasses import dataclass
from math import atan2, cos, hypot, isclose, sin, sqrt
from typing import Iterable


DEFAULT_TOLERANCE = 1e-9


@dataclass(frozen=True, slots=True)
class Vector2:
    x: float
    y: float

    def __add__(self, other: Vector2) -> Vector2:
        return Vector2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vector2) -> Vector2:
        return Vector2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Vector2:
        return Vector2(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: float) -> Vector2:
        return self * scalar

    def __truediv__(self, scalar: float) -> Vector2:
        if isclose(scalar, 0.0, abs_tol=DEFAULT_TOLERANCE):
            raise ZeroDivisionError("Cannot divide vector by zero.")
        return Vector2(self.x / scalar, self.y / scalar)

    def dot(self, other: Vector2) -> float:
        return self.x * other.x + self.y * other.y

    def cross(self, other: Vector2) -> float:
        return self.x * other.y - self.y * other.x

    def length_squared(self) -> float:
        return self.x * self.x + self.y * self.y

    def length(self) -> float:
        return hypot(self.x, self.y)

    def normalized(self) -> Vector2:
        length = self.length()

        if length <= DEFAULT_TOLERANCE:
            raise ValueError("Cannot normalize a zero-length vector.")

        return self / length

    def perpendicular(self) -> Vector2:
        return Vector2(-self.y, self.x)

    def angle(self) -> float:
        return atan2(self.y, self.x)


@dataclass(frozen=True, slots=True)
class Point2:
    x: float
    y: float

    def __add__(self, vector: Vector2) -> Point2:
        return Point2(self.x + vector.x, self.y + vector.y)

    def __sub__(self, other):
        if isinstance(other, Point2):
            return Vector2(self.x - other.x, self.y - other.y)

        if isinstance(other, Vector2):
            return Point2(self.x - other.x, self.y - other.y)

        return NotImplemented

    def distance_to(self, other: Point2) -> float:
        return hypot(self.x - other.x, self.y - other.y)

    def almost_equal(
        self,
        other: Point2,
        tolerance: float = DEFAULT_TOLERANCE,
    ) -> bool:
        return (
            abs(self.x - other.x) <= tolerance
            and abs(self.y - other.y) <= tolerance
        )


@dataclass(frozen=True, slots=True)
class LineSegment2:
    start: Point2
    end: Point2

    @property
    def direction(self) -> Vector2:
        return self.end - self.start

    @property
    def length(self) -> float:
        return self.start.distance_to(self.end)

    @property
    def midpoint(self) -> Point2:
        return Point2(
            (self.start.x + self.end.x) / 2.0,
            (self.start.y + self.end.y) / 2.0,
        )

    def point_at(self, t: float) -> Point2:
        direction = self.direction

        return Point2(
            self.start.x + direction.x * t,
            self.start.y + direction.y * t,
        )

    def closest_point(self, point: Point2) -> Point2:
        direction = self.direction
        length_squared = direction.length_squared()

        if length_squared <= DEFAULT_TOLERANCE:
            return self.start

        relative = point - self.start

        t = relative.dot(direction) / length_squared

        t = max(0.0, min(1.0, t))

        return self.point_at(t)

    def distance_to(self, point: Point2) -> float:
        return self.closest_point(point).distance_to(point)

    def contains_point(
        self,
        point: Point2,
        tolerance: float = DEFAULT_TOLERANCE,
    ) -> bool:
        if self.distance_to(point) > tolerance:
            return False

        direction = self.direction

        if direction.length_squared() <= tolerance:
            return self.start.almost_equal(point, tolerance)

        relative = point - self.start

        projection = relative.dot(direction)

        return (
            projection >= -tolerance
            and projection <= direction.length_squared() + tolerance
        )


@dataclass(frozen=True, slots=True)
class Circle2:
    center: Point2
    radius: float

    def __post_init__(self):
        if self.radius < 0:
            raise ValueError("Circle radius cannot be negative.")

    def point_at(self, angle: float) -> Point2:
        return Point2(
            self.center.x + self.radius * cos(angle),
            self.center.y + self.radius * sin(angle),
        )

    def contains_point(
        self,
        point: Point2,
        tolerance: float = DEFAULT_TOLERANCE,
    ) -> bool:
        return abs(
            self.center.distance_to(point) - self.radius
        ) <= tolerance


@dataclass(frozen=True, slots=True)
class BoundingBox2:
    min_x: float
    min_y: float
    max_x: float
    max_y: float

    @classmethod
    def from_points(cls, points: Iterable[Point2]) -> BoundingBox2:
        points = list(points)

        if not points:
            raise ValueError("Cannot create bounding box from no points.")

        return cls(
            min(point.x for point in points),
            min(point.y for point in points),
            max(point.x for point in points),
            max(point.y for point in points),
        )

    @property
    def width(self) -> float:
        return self.max_x - self.min_x

    @property
    def height(self) -> float:
        return self.max_y - self.min_y

    def contains(
        self,
        point: Point2,
        tolerance: float = DEFAULT_TOLERANCE,
    ) -> bool:
        return (
            self.min_x - tolerance <= point.x <= self.max_x + tolerance
            and
            self.min_y - tolerance <= point.y <= self.max_y + tolerance
        )

    def intersects(self, other: BoundingBox2) -> bool:
        return not (
            self.max_x < other.min_x
            or self.min_x > other.max_x
            or self.max_y < other.min_y
            or self.min_y > other.max_y
        )
