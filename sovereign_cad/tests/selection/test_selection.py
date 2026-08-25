﻿from sovereign_cad.core.entities import (
    CircleEntity,
    EntityRegistry,
    LineEntity,
)

from sovereign_cad.core.geometry import (
    BoundingBox2,
    Point2,
)

from sovereign_cad.core.selection import SelectionEngine
from sovereign_cad.core.spatial import SpatialIndex


def create_selection_engine():

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

    spatial = SpatialIndex()

    spatial.rebuild(registry)

    selection = SelectionEngine(
        registry,
        spatial,
    )

    return selection, line, circle


def test_pick():

    selection, line, circle = create_selection_engine()

    result = selection.pick(Point2(5, 0))

    assert line in result
    assert circle not in result


def test_crossing_window():

    selection, line, circle = create_selection_engine()

    box = BoundingBox2(-1, -1, 11, 1)

    result = selection.window_select(
        box,
        crossing=True,
    )

    assert line in result
    assert circle not in result


def test_contained_window():

    selection, line, circle = create_selection_engine()

    box = BoundingBox2(-1, -1, 11, 1)

    result = selection.window_select(
        box,
        crossing=False,
    )

    assert line in result
    assert circle not in result


def test_apply_selection():

    selection, line, circle = create_selection_engine()

    selection.apply_selection([line])

    assert line.selected
    assert not circle.selected


def test_additive_selection():

    selection, line, circle = create_selection_engine()

    selection.apply_selection([line])

    selection.apply_selection(
        [circle],
        additive=True,
    )

    assert line.selected
    assert circle.selected


def test_clear_selection():

    selection, line, circle = create_selection_engine()

    selection.apply_selection([line, circle])

    selection.clear()

    assert not line.selected
    assert not circle.selected
