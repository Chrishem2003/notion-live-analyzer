from sovereign_cad.core.commands import (
    ChangeLayerCommand,
    CommandManager,
    CreateEntityCommand,
    DeleteEntityCommand,
)
from sovereign_cad.core.document import Document
from sovereign_cad.core.entities import LineEntity
from sovereign_cad.core.geometry import Point2


def make_line():

    return LineEntity(
        Point2(0, 0),
        Point2(10, 0),
    )


def test_create_command():

    document = Document()
    entity = make_line()

    command = CreateEntityCommand(
        document,
        entity,
    )

    command.execute()

    assert document.entity_count == 1
    assert document.get_entity(entity.entity_id) is entity

    command.undo()

    assert document.entity_count == 0


def test_delete_command():

    document = Document()
    entity = make_line()

    document.add_entity(entity)

    command = DeleteEntityCommand(
        document,
        entity.entity_id,
    )

    command.execute()

    assert document.entity_count == 0

    command.undo()

    assert document.entity_count == 1
    assert document.get_entity(entity.entity_id) is entity


def test_change_layer():

    document = Document()

    entity = make_line()

    document.add_entity(entity)

    command = ChangeLayerCommand(
        document,
        entity.entity_id,
        "WALLS",
    )

    command.execute()

    assert entity.layer == "WALLS"

    command.undo()

    assert entity.layer == "0"


def test_manager_undo():

    document = Document()

    entity = make_line()

    manager = CommandManager()

    manager.execute(
        CreateEntityCommand(
            document,
            entity,
        )
    )

    assert document.entity_count == 1
    assert manager.can_undo
    assert not manager.can_redo

    assert manager.undo()

    assert document.entity_count == 0
    assert manager.can_redo


def test_manager_redo():

    document = Document()

    entity = make_line()

    manager = CommandManager()

    manager.execute(
        CreateEntityCommand(
            document,
            entity,
        )
    )

    manager.undo()

    assert document.entity_count == 0

    assert manager.redo()

    assert document.entity_count == 1


def test_new_command_clears_redo():

    document = Document()

    first = make_line()
    second = make_line()

    manager = CommandManager()

    manager.execute(
        CreateEntityCommand(
            document,
            first,
        )
    )

    manager.undo()

    assert manager.can_redo

    manager.execute(
        CreateEntityCommand(
            document,
            second,
        )
    )

    assert not manager.can_redo
    assert document.entity_count == 1


def test_multiple_undo_redo():

    document = Document()

    first = make_line()
    second = make_line()
    third = make_line()

    manager = CommandManager()

    manager.execute(
        CreateEntityCommand(document, first)
    )

    manager.execute(
        CreateEntityCommand(document, second)
    )

    manager.execute(
        CreateEntityCommand(document, third)
    )

    assert document.entity_count == 3

    manager.undo()
    manager.undo()

    assert document.entity_count == 1

    manager.redo()

    assert document.entity_count == 2

    manager.redo()

    assert document.entity_count == 3
