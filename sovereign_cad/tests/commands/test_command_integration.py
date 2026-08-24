from sovereign_cad.core.commands import (
    ChangeLayerCommand,
    CommandManager,
    CreateEntityCommand,
)
from sovereign_cad.core.document import Document
from sovereign_cad.core.entities import LineEntity
from sovereign_cad.core.geometry import Point2


def test_full_command_workflow():

    document = Document()
    manager = CommandManager()

    line = LineEntity(
        Point2(0, 0),
        Point2(100, 0),
    )

    manager.execute(
        CreateEntityCommand(
            document,
            line,
        )
    )

    assert document.entity_count == 1

    manager.execute(
        ChangeLayerCommand(
            document,
            line.entity_id,
            "WALLS",
        )
    )

    assert line.layer == "WALLS"

    manager.undo()

    assert line.layer == "0"

    manager.undo()

    assert document.entity_count == 0

    manager.redo()

    assert document.entity_count == 1

    manager.redo()

    assert line.layer == "WALLS"
