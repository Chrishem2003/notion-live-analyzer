import pytest

from sovereign_cad.core.document import Document
from sovereign_cad.core.entities import CircleEntity, LineEntity
from sovereign_cad.core.geometry import Point2


def test_document_starts_empty():

    document = Document()

    assert document.entity_count == 0
    assert document.layer_count == 1
    assert document.active_layer == "0"


def test_add_line():

    document = Document()

    entity = LineEntity(
        Point2(0, 0),
        Point2(10, 0),
    )

    entity_id = document.add_entity(entity)

    assert document.entity_count == 1
    assert document.get_entity(entity_id) is entity


def test_add_circle():

    document = Document()

    entity = CircleEntity(
        Point2(5, 5),
        3,
    )

    document.add_entity(entity)

    assert document.entity_count == 1


def test_add_layer():

    document = Document()

    layer = document.add_layer("WALLS")

    assert layer.name == "WALLS"
    assert "WALLS" in document.layers


def test_active_layer():

    document = Document()

    document.add_layer("WALLS")
    document.set_active_layer("WALLS")

    assert document.active_layer == "WALLS"


def test_entity_selection():

    document = Document()

    entity = LineEntity(
        Point2(0, 0),
        Point2(10, 0),
    )

    entity_id = document.add_entity(entity)

    document.select_entity(entity_id)

    selected = document.selected_entities()

    assert len(selected) == 1
    assert selected[0] is entity

    document.deselect_all()

    assert document.selected_entities() == []


def test_remove_entity():

    document = Document()

    entity = LineEntity(
        Point2(0, 0),
        Point2(10, 0),
    )

    entity_id = document.add_entity(entity)

    removed = document.remove_entity(entity_id)

    assert removed is entity
    assert document.entity_count == 0


def test_layer_removal_protection():

    document = Document()

    document.add_layer("WALLS")
    document.set_active_layer("WALLS")

    entity = LineEntity(
        Point2(0, 0),
        Point2(10, 0),
        layer="WALLS",
    )

    document.add_entity(entity)

    with pytest.raises(ValueError):
        document.remove_layer("WALLS")


def test_default_layer_cannot_be_removed():

    document = Document()

    with pytest.raises(ValueError):
        document.remove_layer("0")
