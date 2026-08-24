from math import pi

from sovereign_cad.core.geometry import (
    BoundingBox2,
    Circle2,
    LineSegment2,
    Point2,
    Vector2,
    line_circle_intersections,
    line_line_intersection,
)


def test_vector_length():
    vector = Vector2(3, 4)

    assert vector.length() == 5


def test_vector_dot_product():
    first = Vector2(1, 2)
    second = Vector2(3, 4)

    assert first.dot(second) == 11


def test_point_distance():
    first = Point2(0, 0)
    second = Point2(3, 4)

    assert first.distance_to(second) == 5


def test_line_length():
    line = LineSegment2(
        Point2(0, 0),
        Point2(3, 4),
    )

    assert line.length == 5


def test_line_midpoint():
    line = LineSegment2(
        Point2(0, 0),
        Point2(10, 10),
    )

    assert line.midpoint.almost_equal(
        Point2(5, 5)
    )


def test_closest_point():
    line = LineSegment2(
        Point2(0, 0),
        Point2(10, 0),
    )

    closest = line.closest_point(
        Point2(4, 5)
    )

    assert closest.almost_equal(
        Point2(4, 0)
    )


def test_circle_point():
    circle = Circle2(
        Point2(0, 0),
        10,
    )

    point = circle.point_at(0)

    assert point.almost_equal(
        Point2(10, 0)
    )


def test_line_line_intersection():
    first = LineSegment2(
        Point2(0, 0),
        Point2(10, 10),
    )

    second = LineSegment2(
        Point2(0, 10),
        Point2(10, 0),
    )

    result = line_line_intersection(
        first,
        second,
    )

    assert result is not None

    assert result.almost_equal(
        Point2(5, 5)
    )


def test_line_circle_intersection():
    line = LineSegment2(
        Point2(-10, 0),
        Point2(10, 0),
    )

    circle = Circle2(
        Point2(0, 0),
        5,
    )

    result = line_circle_intersections(
        line,
        circle,
    )

    assert len(result) == 2

    assert result[0].almost_equal(
        Point2(-5, 0)
    )

    assert result[1].almost_equal(
        Point2(5, 0)
    )


def test_bounding_box():
    box = BoundingBox2.from_points(
        [
            Point2(2, 3),
            Point2(-1, 8),
            Point2(4, -2),
        ]
    )

    assert box.min_x == -1
    assert box.max_x == 4
    assert box.min_y == -2
    assert box.max_y == 8
    assert box.width == 5
    assert box.height == 10
