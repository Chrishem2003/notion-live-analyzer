from sovereign_cad.core.entities import (
    CircleEntity,
    EntityRegistry,
    LineEntity,
)

from sovereign_cad.core.geometry import (
    BoundingBox2,
    Point2,
)

from sovereign_cad.core.spatial import SpatialIndex


def create_scene():

    registry = EntityRegistry()

    line = LineEntity(
        start=Point2(0, 0),
        end=Point2(10, 0),
    )

    circle = CircleEntity(
        center=Point2(20, 20),
        radius=5,
    )

    registry.add(line)
    registry.add(circle)

    return registry, line, circle


def test_insert():

    registry, line, circle = create_scene()

    index = SpatialIndex()

    index.rebuild(registry)

    assert len(index) == 2


def test_point_query():

    registry, line, circle = create_scene()

    index = SpatialIndex()

    index.rebuild(registry)

    result = index.query_point(Point2(5, 0))

    assert line.id in result
    assert circle.id not in result


def test_box_query():

    registry, line, circle = create_scene()

    index = SpatialIndex()

    index.rebuild(registry)

    box = BoundingBox2(-1, -1, 11, 1)

    result = index.query_box(box)

    assert line.id in result
    assert circle.id not in result


def test_remove():

    registry, line, circle = create_scene()

    index = SpatialIndex()

    index.rebuild(registry)

    index.remove(line.id)

    assert len(index) == 1
