from sovereign_cad.commands import (
    Command,
    CommandManager,
    CommandResult,
)


class CounterCommand(Command):

    name = "Counter"

    def execute(self, context):
        context["value"] += 1

        return CommandResult(
            success=True,
            message="incremented",
        )

    def undo(self, context):
        context["value"] -= 1

        return CommandResult(
            success=True,
            message="decremented",
        )


def test_command_execution():
    context = {"value": 0}
    manager = CommandManager(context=context)

    result = manager.execute(CounterCommand())

    assert result.success
    assert context["value"] == 1
    assert manager.can_undo
    assert not manager.can_redo


def test_command_undo():
    context = {"value": 0}
    manager = CommandManager(context=context)

    manager.execute(CounterCommand())
    result = manager.undo()

    assert result.success
    assert context["value"] == 0
    assert not manager.can_undo
    assert manager.can_redo


def test_command_redo():
    context = {"value": 0}
    manager = CommandManager(context=context)

    manager.execute(CounterCommand())
    manager.undo()
    result = manager.redo()

    assert result.success
    assert context["value"] == 1
    assert manager.can_undo
    assert not manager.can_redo


def test_empty_undo():
    manager = CommandManager(context={})

    result = manager.undo()

    assert not result.success


def test_empty_redo():
    manager = CommandManager(context={})

    result = manager.redo()

    assert not result.success
