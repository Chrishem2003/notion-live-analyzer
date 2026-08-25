﻿from sovereign_cad.core.entities import (
    CircleEntity,
    LineEntity,
    is_valid_entity_id,
)
from sovereign_cad.core.geometry import Point2


def test_line_entity():

    entity = LineEntity(
        Point2(0, 0),
        Point2(10, 0),
    )

    assert entity.entity_type == "LINE"
    assert entity.length == 10
    assert is_valid_entity_id(entity.entity_id)


def test_circle_entity():

    entity = CircleEntity(
        Point2(5, 5),
        10,
    )

    assert entity.entity_type == "CIRCLE"
    assert entity.radius == 10
    assert is_valid_entity_id(entity.entity_id)


def test_entity_selection():

    entity = LineEntity(
        Point2(0, 0),
        Point2(1, 1),
    )

    assert entity.selected is False

    entity.select()

    assert entity.selected is True

    entity.deselect()

    assert entity.selected is False


def test_entity_layer():

    entity = LineEntity(
        Point2(0, 0),
        Point2(1, 1),
        layer="WALLS",
    )

    assert entity.layer == "WALLS"

    entity.set_layer("DIMENSIONS")

    assert entity.layer == "DIMENSIONS"


def test_line_bounding_box():

    entity = LineEntity(
        Point2(-2, -3),
        Point2(8, 7),
    )

    box = entity.bounding_box()

    assert box.min_x == -2
    assert box.max_x == 8
    assert box.min_y == -3
    assert box.max_y == 7


def test_circle_bounding_box():

    entity = CircleEntity(
        Point2(10, 20),
        5,
    )

    box = entity.bounding_box()

    assert box.min_x == 5
    assert box.max_x == 15
    assert box.min_y == 15
    assert box.max_y == 25
