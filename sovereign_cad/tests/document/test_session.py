﻿from sovereign_cad.commands import Command, CommandResult
from sovereign_cad.document import DocumentSession


class SessionCommand(Command):

    name = "SessionCommand"

    def execute(self, context):
        context.active_tool = "test"

        return CommandResult(success=True)

    def undo(self, context):
        context.active_tool = None

        return CommandResult(success=True)


def test_document_session():
    session = DocumentSession()

    assert session.command_manager is not None
    assert session.active_tool is None


def test_document_command_execution():
    session = DocumentSession()

    result = session.execute(SessionCommand())

    assert result.success
    assert session.active_tool == "test"


def test_document_undo():
    session = DocumentSession()

    session.execute(SessionCommand())
    result = session.undo()

    assert result.success
    assert session.active_tool is None


def test_document_redo():
    session = DocumentSession()

    session.execute(SessionCommand())
    session.undo()

    result = session.redo()

    assert result.success
    assert session.active_tool == "test"


def test_tool_selection():
    session = DocumentSession()

    session.set_tool("select")

    assert session.active_tool == "select"

    session.clear_tool()

    assert session.active_tool is None
