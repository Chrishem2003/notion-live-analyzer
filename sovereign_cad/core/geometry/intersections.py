from __future__ import annotations

from math import sqrt

from .primitives import (
    DEFAULT_TOLERANCE,
    Circle2,
    LineSegment2,
    Point2,
)


def line_line_intersection(
    first: LineSegment2,
    second: LineSegment2,
    tolerance: float = DEFAULT_TOLERANCE,
) -> Point2 | None:

    p = first.start
    r = first.direction

    q = second.start
    s = second.direction

    denominator = r.cross(s)

    if abs(denominator) <= tolerance:
        return None

    q_minus_p = q - p

    t = q_minus_p.cross(s) / denominator
    u = q_minus_p.cross(r) / denominator

    if (
        -tolerance <= t <= 1.0 + tolerance
        and
        -tolerance <= u <= 1.0 + tolerance
    ):
        return first.point_at(t)

    return None


def line_circle_intersections(
    line: LineSegment2,
    circle: Circle2,
    tolerance: float = DEFAULT_TOLERANCE,
) -> list[Point2]:

    direction = line.direction
    offset = line.start - circle.center

    a = direction.dot(direction)

    if a <= tolerance:
        return (
            [line.start]
            if abs(line.start.distance_to(circle.center) - circle.radius)
            <= tolerance
            else []
        )

    b = 2.0 * offset.dot(direction)
    c = offset.dot(offset) - circle.radius * circle.radius

    discriminant = b * b - 4.0 * a * c

    if discriminant < -tolerance:
        return []

    if abs(discriminant) <= tolerance:
        discriminant = 0.0

    root = sqrt(discriminant)

    t1 = (-b - root) / (2.0 * a)
    t2 = (-b + root) / (2.0 * a)

    result = []

    for t in (t1, t2):

        if -tolerance <= t <= 1.0 + tolerance:

            point = line.point_at(t)

            if not any(point.almost_equal(existing, tolerance) for existing in result):
                result.append(point)

    return result
