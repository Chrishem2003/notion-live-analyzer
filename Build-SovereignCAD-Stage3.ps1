[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

# ============================================================
# SOVEREIGNCAD BUILD SYSTEM
# Stage 3: Command Engine + Undo/Redo
# ============================================================

$Root = (Get-Location).Path

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "             SOVEREIGNCAD BUILD SYSTEM" -ForegroundColor Cyan
Write-Host "             STAGE 3 - COMMAND ENGINE" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Project: $Root" -ForegroundColor Gray
Write-Host ""

# ------------------------------------------------------------
# Python
# ------------------------------------------------------------

Write-Host "[1/10] Checking Python..." -ForegroundColor Yellow

$Python = Get-Command python -ErrorAction SilentlyContinue

if (-not $Python) {
    throw "Python was not found. Activate the .venv first."
}

Write-Host "Python: $($Python.Source)" -ForegroundColor Green
Write-Host "Version: $(python --version)" -ForegroundColor Green

# ------------------------------------------------------------
# Verify Stage 2
# ------------------------------------------------------------

Write-Host "[2/10] Verifying Stage 2..." -ForegroundColor Yellow

python -c "from sovereign_cad.core.document import Document; from sovereign_cad.core.entities import LineEntity, CircleEntity; print('STAGE 2: OK')"

if ($LASTEXITCODE -ne 0) {
    throw "Stage 2 Entity + Document Engine is unavailable."
}

# ------------------------------------------------------------
# Create command directories
# ------------------------------------------------------------

Write-Host "[3/10] Creating command architecture..." -ForegroundColor Yellow

$Directories = @(
    "sovereign_cad\core\commands",
    "sovereign_cad\tests\commands"
)

foreach ($Directory in $Directories) {

    $Path = Join-Path $Root $Directory

    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
        Write-Host "CREATE: $Directory" -ForegroundColor DarkGreen
    }
}

# ------------------------------------------------------------
# Base Command
# ------------------------------------------------------------

Write-Host "[4/10] Building command abstraction..." -ForegroundColor Yellow

$CommandFile = Join-Path `
    $Root `
    "sovereign_cad\core\commands\command.py"

@'
from __future__ import annotations

from abc import ABC, abstractmethod


class Command(ABC):
    """
    Base class for every document-changing operation.

    A command must be reversible.

    execute()
        Apply the operation.

    undo()
        Reverse the operation.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def execute(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def undo(self) -> None:
        raise NotImplementedError
'@ | Set-Content -LiteralPath $CommandFile -Encoding UTF8

Write-Host "CREATE: command.py" -ForegroundColor Green

# ------------------------------------------------------------
# Create Entity Command
# ------------------------------------------------------------

Write-Host "[5/10] Building entity creation commands..." -ForegroundColor Yellow

$CreateEntityFile = Join-Path `
    $Root `
    "sovereign_cad\core\commands\create_entity.py"

@'
from __future__ import annotations

from sovereign_cad.core.document import Document
from sovereign_cad.core.entities import Entity

from .command import Command


class CreateEntityCommand(Command):
    """
    Adds an entity to a document.

    Undo removes the entity.
    Redo adds the same entity again.
    """

    def __init__(
        self,
        document: Document,
        entity: Entity,
    ) -> None:

        self.document = document
        self.entity = entity
        self._executed = False

    @property
    def name(self) -> str:
        return f"Create {self.entity.entity_type}"

    def execute(self) -> None:

        if self._executed:
            return

        self.document.add_entity(self.entity)

        self._executed = True

    def undo(self) -> None:

        if not self._executed:
            return

        self.document.remove_entity(
            self.entity.entity_id
        )

        self._executed = False
'@ | Set-Content -LiteralPath $CreateEntityFile -Encoding UTF8

Write-Host "CREATE: create_entity.py" -ForegroundColor Green

# ------------------------------------------------------------
# Delete Entity Command
# ------------------------------------------------------------

$DeleteEntityFile = Join-Path `
    $Root `
    "sovereign_cad\core\commands\delete_entity.py"

@'
from __future__ import annotations

from uuid import UUID

from sovereign_cad.core.document import Document
from sovereign_cad.core.entities import Entity

from .command import Command


class DeleteEntityCommand(Command):
    """
    Removes an entity from a document.

    Undo restores the exact same entity.
    """

    def __init__(
        self,
        document: Document,
        entity_id: UUID,
    ) -> None:

        self.document = document
        self.entity_id = entity_id
        self._entity: Entity | None = None
        self._executed = False

    @property
    def name(self) -> str:
        return "Delete Entity"

    def execute(self) -> None:

        if self._executed:
            return

        self._entity = self.document.remove_entity(
            self.entity_id
        )

        self._executed = True

    def undo(self) -> None:

        if not self._executed:
            return

        if self._entity is None:
            raise RuntimeError(
                "Cannot undo deletion without stored entity."
            )

        self.document.add_entity(self._entity)

        self._executed = False
'@ | Set-Content -LiteralPath $DeleteEntityFile -Encoding UTF8

Write-Host "CREATE: delete_entity.py" -ForegroundColor Green

# ------------------------------------------------------------
# Change Layer Command
# ------------------------------------------------------------

$LayerCommandFile = Join-Path `
    $Root `
    "sovereign_cad\core\commands\change_layer.py"

@'
from __future__ import annotations

from uuid import UUID

from sovereign_cad.core.document import Document

from .command import Command


class ChangeLayerCommand(Command):
    """
    Moves an entity between layers.
    """

    def __init__(
        self,
        document: Document,
        entity_id: UUID,
        new_layer: str,
    ) -> None:

        self.document = document
        self.entity_id = entity_id
        self.new_layer = new_layer

        self.old_layer: str | None = None
        self._executed = False

    @property
    def name(self) -> str:
        return "Change Layer"

    def execute(self) -> None:

        if self._executed:
            return

        entity = self.document.get_entity(
            self.entity_id
        )

        if entity is None:
            raise KeyError(self.entity_id)

        self.old_layer = entity.layer

        if self.new_layer not in self.document.layers:
            self.document.add_layer(self.new_layer)

        entity.set_layer(self.new_layer)

        self._executed = True

    def undo(self) -> None:

        if not self._executed:
            return

        entity = self.document.get_entity(
            self.entity_id
        )

        if entity is None:
            raise KeyError(self.entity_id)

        if self.old_layer is None:
            raise RuntimeError(
                "Original layer was not recorded."
            )

        entity.set_layer(self.old_layer)

        self._executed = False
'@ | Set-Content -LiteralPath $LayerCommandFile -Encoding UTF8

Write-Host "CREATE: change_layer.py" -ForegroundColor Green

# ------------------------------------------------------------
# Command Manager
# ------------------------------------------------------------

Write-Host "[6/10] Building undo/redo manager..." -ForegroundColor Yellow

$ManagerFile = Join-Path `
    $Root `
    "sovereign_cad\core\commands\command_manager.py"

@'
from __future__ import annotations

from .command import Command


class CommandManager:
    """
    Manages command execution and history.

    History model:

        execute
           |
           v
        undo stack
           |
        undo()
           |
           v
        redo stack
           |
        redo()
    """

    def __init__(self) -> None:

        self._undo_stack: list[Command] = []
        self._redo_stack: list[Command] = []

    # --------------------------------------------------------
    # Execute
    # --------------------------------------------------------

    def execute(self, command: Command) -> None:

        command.execute()

        self._undo_stack.append(command)

        # Any new operation invalidates redo history.
        self._redo_stack.clear()

    # --------------------------------------------------------
    # Undo
    # --------------------------------------------------------

    def undo(self) -> bool:

        if not self._undo_stack:
            return False

        command = self._undo_stack.pop()

        command.undo()

        self._redo_stack.append(command)

        return True

    # --------------------------------------------------------
    # Redo
    # --------------------------------------------------------

    def redo(self) -> bool:

        if not self._redo_stack:
            return False

        command = self._redo_stack.pop()

        command.execute()

        self._undo_stack.append(command)

        return True

    # --------------------------------------------------------
    # State
    # --------------------------------------------------------

    @property
    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    @property
    def undo_count(self) -> int:
        return len(self._undo_stack)

    @property
    def redo_count(self) -> int:
        return len(self._redo_stack)

    def clear(self) -> None:

        self._undo_stack.clear()
        self._redo_stack.clear()

    @property
    def undo_history(self) -> tuple[Command, ...]:
        return tuple(self._undo_stack)

    @property
    def redo_history(self) -> tuple[Command, ...]:
        return tuple(self._redo_stack)
'@ | Set-Content -LiteralPath $ManagerFile -Encoding UTF8

Write-Host "CREATE: command_manager.py" -ForegroundColor Green

# ------------------------------------------------------------
# Command exports
# ------------------------------------------------------------

$CommandsInit = Join-Path `
    $Root `
    "sovereign_cad\core\commands\__init__.py"

@'
from .command import Command
from .command_manager import CommandManager
from .create_entity import CreateEntityCommand
from .delete_entity import DeleteEntityCommand
from .change_layer import ChangeLayerCommand

__all__ = [
    "Command",
    "CommandManager",
    "CreateEntityCommand",
    "DeleteEntityCommand",
    "ChangeLayerCommand",
]
'@ | Set-Content -LiteralPath $CommandsInit -Encoding UTF8

# ------------------------------------------------------------
# Tests
# ------------------------------------------------------------

Write-Host "[7/10] Creating command tests..." -ForegroundColor Yellow

$CommandTestFile = Join-Path `
    $Root `
    "sovereign_cad\tests\commands\test_commands.py"

@'
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
'@ | Set-Content -LiteralPath $CommandTestFile -Encoding UTF8

# ------------------------------------------------------------
# Integration test
# ------------------------------------------------------------

$IntegrationTestFile = Join-Path `
    $Root `
    "sovereign_cad\tests\commands\test_command_integration.py"

@'
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
'@ | Set-Content -LiteralPath $IntegrationTestFile -Encoding UTF8

Write-Host "CREATE: command tests" -ForegroundColor Green

# ------------------------------------------------------------
# Compile
# ------------------------------------------------------------

Write-Host "[8/10] Running Python syntax verification..." -ForegroundColor Yellow

python -m compileall -q sovereign_cad

if ($LASTEXITCODE -ne 0) {
    throw "Python syntax verification failed."
}

Write-Host "PYTHON SYNTAX: OK" -ForegroundColor Green

# ------------------------------------------------------------
# Import verification
# ------------------------------------------------------------

Write-Host "[9/10] Verifying command imports..." -ForegroundColor Yellow

python -c "from sovereign_cad.core.commands import Command, CommandManager, CreateEntityCommand, DeleteEntityCommand, ChangeLayerCommand; print('COMMAND ENGINE: OK')"

if ($LASTEXITCODE -ne 0) {
    throw "Command engine import failed."
}

# ------------------------------------------------------------
# Tests
# ------------------------------------------------------------

Write-Host "[10/10] Running complete SovereignCAD test suite..." -ForegroundColor Yellow

$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"

python -m pytest `
    .\sovereign_cad\tests\test_geometry.py `
    .\sovereign_cad\tests\entities `
    .\sovereign_cad\tests\document `
    .\sovereign_cad\tests\commands `
    -q

if ($LASTEXITCODE -ne 0) {
    throw "Stage 3 tests failed."
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "             SOVEREIGNCAD STAGE 3: SUCCESS" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Geometry Kernel       : ONLINE" -ForegroundColor Green
Write-Host "Entity Engine         : ONLINE" -ForegroundColor Green
Write-Host "Document Engine       : ONLINE" -ForegroundColor Green
Write-Host "Command Engine        : ONLINE" -ForegroundColor Green
Write-Host "Undo System           : ONLINE" -ForegroundColor Green
Write-Host "Redo System           : ONLINE" -ForegroundColor Green
Write-Host "Integration Tests     : PASSED" -ForegroundColor Green
Write-Host ""
Write-Host "Next stage:" -ForegroundColor Cyan
Write-Host "Transforms + Spatial Index + Selection Engine" -ForegroundColor Cyan
Write-Host ""