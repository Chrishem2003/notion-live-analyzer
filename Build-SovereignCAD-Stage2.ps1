[CmdletBinding()]
param(
    [switch]$RunTests
)

$ErrorActionPreference = "Stop"

# ============================================================
# SOVEREIGNCAD BUILD SYSTEM
# Stage 2: Entity + Document Engine
# ============================================================

$Root = (Get-Location).Path

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "             SOVEREIGNCAD BUILD SYSTEM" -ForegroundColor Cyan
Write-Host "             STAGE 2 - ENTITY + DOCUMENT ENGINE" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Project: $Root" -ForegroundColor Gray
Write-Host ""

# ------------------------------------------------------------
# Verify Python
# ------------------------------------------------------------

Write-Host "[1/9] Checking Python..." -ForegroundColor Yellow

$Python = Get-Command python -ErrorAction SilentlyContinue

if (-not $Python) {
    throw "Python was not found. Activate the .venv first."
}

Write-Host "Python: $($Python.Source)" -ForegroundColor Green
Write-Host "Version: $(python --version)" -ForegroundColor Green

# ------------------------------------------------------------
# Verify Stage 1 geometry kernel
# ------------------------------------------------------------

Write-Host "[2/9] Verifying geometry kernel..." -ForegroundColor Yellow

python -c "from sovereign_cad.core.geometry import Point2, Vector2, LineSegment2, Circle2, BoundingBox2; print('GEOMETRY KERNEL: OK')"

if ($LASTEXITCODE -ne 0) {
    throw "Stage 1 geometry kernel is not available."
}

# ------------------------------------------------------------
# Create Stage 2 directories
# ------------------------------------------------------------

Write-Host "[3/9] Creating entity/document architecture..." -ForegroundColor Yellow

$Directories = @(
    "sovereign_cad\core\entities",
    "sovereign_cad\core\document",
    "sovereign_cad\tests\entities",
    "sovereign_cad\tests\document"
)

foreach ($Directory in $Directories) {

    $Path = Join-Path -Path $Root -ChildPath $Directory

    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
        Write-Host "CREATE: $Directory" -ForegroundColor DarkGreen
    }
}

# ------------------------------------------------------------
# Entity ID
# ------------------------------------------------------------

Write-Host "[4/9] Building entity identity system..." -ForegroundColor Yellow

$EntityIdFile = Join-Path `
    -Path $Root `
    -ChildPath "sovereign_cad\core\entities\entity_id.py"

@'
from __future__ import annotations

from uuid import UUID, uuid4


def new_entity_id() -> UUID:
    """
    Create a globally unique entity identifier.
    """
    return uuid4()


def is_valid_entity_id(value: object) -> bool:
    """
    Return True when value is a UUID.
    """
    return isinstance(value, UUID)
'@ | Set-Content -LiteralPath $EntityIdFile -Encoding UTF8

Write-Host "CREATE: sovereign_cad\core\entities\entity_id.py" -ForegroundColor Green

# ------------------------------------------------------------
# Base Entity
# ------------------------------------------------------------

$EntityFile = Join-Path `
    -Path $Root `
    -ChildPath "sovereign_cad\core\entities\entity.py"

@'
from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from .entity_id import new_entity_id


class Entity(ABC):
    """
    Base class for every CAD entity.

    Entities have:
    - a stable unique ID
    - a layer
    - visibility state
    - selection state
    """

    def __init__(
        self,
        *,
        entity_id: UUID | None = None,
        layer: str = "0",
        visible: bool = True,
    ) -> None:

        self.entity_id = entity_id or new_entity_id()
        self.layer = layer
        self.visible = visible
        self.selected = False

    @property
    @abstractmethod
    def entity_type(self) -> str:
        """
        Human-readable entity type.
        """
        raise NotImplementedError

    @abstractmethod
    def bounding_box(self):
        """
        Return the geometric bounding box.
        """
        raise NotImplementedError

    def select(self) -> None:
        self.selected = True

    def deselect(self) -> None:
        self.selected = False

    def set_layer(self, layer: str) -> None:

        if not layer:
            raise ValueError("Layer name cannot be empty.")

        self.layer = layer

    def set_visible(self, visible: bool) -> None:
        self.visible = bool(visible)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"id={self.entity_id}, "
            f"layer={self.layer!r}, "
            f"visible={self.visible})"
        )
'@ | Set-Content -LiteralPath $EntityFile -Encoding UTF8

Write-Host "CREATE: sovereign_cad\core\entities\entity.py" -ForegroundColor Green

# ------------------------------------------------------------
# Line Entity
# ------------------------------------------------------------

$LineEntityFile = Join-Path `
    -Path $Root `
    -ChildPath "sovereign_cad\core\entities\line.py"

@'
from __future__ import annotations

from sovereign_cad.core.geometry import (
    BoundingBox2,
    LineSegment2,
    Point2,
)

from .entity import Entity


class LineEntity(Entity):

    def __init__(
        self,
        start: Point2,
        end: Point2,
        *,
        layer: str = "0",
    ) -> None:

        super().__init__(layer=layer)

        self.geometry = LineSegment2(start, end)

    @property
    def entity_type(self) -> str:
        return "LINE"

    @property
    def start(self) -> Point2:
        return self.geometry.start

    @property
    def end(self) -> Point2:
        return self.geometry.end

    @property
    def length(self) -> float:
        return self.geometry.length

    def bounding_box(self) -> BoundingBox2:

        return BoundingBox2.from_points(
            [
                self.start,
                self.end,
            ]
        )
'@ | Set-Content -LiteralPath $LineEntityFile -Encoding UTF8

Write-Host "CREATE: sovereign_cad\core\entities\line.py" -ForegroundColor Green

# ------------------------------------------------------------
# Circle Entity
# ------------------------------------------------------------

$CircleEntityFile = Join-Path `
    -Path $Root `
    -ChildPath "sovereign_cad\core\entities\circle.py"

@'
from __future__ import annotations

from sovereign_cad.core.geometry import (
    BoundingBox2,
    Circle2,
    Point2,
)

from .entity import Entity


class CircleEntity(Entity):

    def __init__(
        self,
        center: Point2,
        radius: float,
        *,
        layer: str = "0",
    ) -> None:

        super().__init__(layer=layer)

        self.geometry = Circle2(center, radius)

    @property
    def entity_type(self) -> str:
        return "CIRCLE"

    @property
    def center(self) -> Point2:
        return self.geometry.center

    @property
    def radius(self) -> float:
        return self.geometry.radius

    def bounding_box(self) -> BoundingBox2:

        center = self.center
        radius = self.radius

        return BoundingBox2(
            center.x - radius,
            center.y - radius,
            center.x + radius,
            center.y + radius,
        )
'@ | Set-Content -LiteralPath $CircleEntityFile -Encoding UTF8

Write-Host "CREATE: sovereign_cad\core\entities\circle.py" -ForegroundColor Green

# ------------------------------------------------------------
# Entity exports
# ------------------------------------------------------------

$EntitiesInit = Join-Path `
    -Path $Root `
    -ChildPath "sovereign_cad\core\entities\__init__.py"

@'
from .entity import Entity
from .entity_id import is_valid_entity_id, new_entity_id
from .line import LineEntity
from .circle import CircleEntity

__all__ = [
    "Entity",
    "LineEntity",
    "CircleEntity",
    "new_entity_id",
    "is_valid_entity_id",
]
'@ | Set-Content -LiteralPath $EntitiesInit -Encoding UTF8

Write-Host "CREATE: entity exports" -ForegroundColor Green

# ------------------------------------------------------------
# Layer
# ------------------------------------------------------------

Write-Host "[5/9] Building layer system..." -ForegroundColor Yellow

$LayerFile = Join-Path `
    -Path $Root `
    -ChildPath "sovereign_cad\core\document\layer.py"

@'
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Layer:
    """
    CAD drawing layer.
    """

    name: str
    visible: bool = True
    locked: bool = False

    def __post_init__(self) -> None:

        if not self.name:
            raise ValueError("Layer name cannot be empty.")

    def show(self) -> None:
        self.visible = True

    def hide(self) -> None:
        self.visible = False

    def lock(self) -> None:
        self.locked = True

    def unlock(self) -> None:
        self.locked = False
'@ | Set-Content -LiteralPath $LayerFile -Encoding UTF8

Write-Host "CREATE: sovereign_cad\core\document\layer.py" -ForegroundColor Green

# ------------------------------------------------------------
# Document
# ------------------------------------------------------------

Write-Host "[6/9] Building document engine..." -ForegroundColor Yellow

$DocumentFile = Join-Path `
    -Path $Root `
    -ChildPath "sovereign_cad\core\document\document.py"

@'
from __future__ import annotations

from uuid import UUID

from sovereign_cad.core.entities import Entity
from sovereign_cad.core.document.layer import Layer


class Document:
    """
    CAD document containing entities and layers.
    """

    def __init__(self) -> None:

        self.entities: dict[UUID, Entity] = {}

        self.layers: dict[str, Layer] = {
            "0": Layer("0")
        }

        self.active_layer = "0"

    # --------------------------------------------------------
    # Layers
    # --------------------------------------------------------

    def add_layer(self, name: str) -> Layer:

        if not name:
            raise ValueError("Layer name cannot be empty.")

        if name in self.layers:
            raise ValueError(f"Layer already exists: {name}")

        layer = Layer(name)

        self.layers[name] = layer

        return layer

    def remove_layer(self, name: str) -> None:

        if name == "0":
            raise ValueError("Default layer cannot be removed.")

        if name not in self.layers:
            raise KeyError(name)

        if any(entity.layer == name for entity in self.entities.values()):
            raise ValueError(
                f"Cannot remove layer '{name}' because it contains entities."
            )

        del self.layers[name]

        if self.active_layer == name:
            self.active_layer = "0"

    def set_active_layer(self, name: str) -> None:

        if name not in self.layers:
            raise KeyError(name)

        if not self.layers[name].visible:
            raise ValueError(
                f"Cannot activate hidden layer: {name}"
            )

        self.active_layer = name

    # --------------------------------------------------------
    # Entities
    # --------------------------------------------------------

    def add_entity(self, entity: Entity) -> UUID:

        if entity.entity_id in self.entities:
            raise ValueError(
                f"Entity already exists: {entity.entity_id}"
            )

        if entity.layer not in self.layers:
            self.layers[entity.layer] = Layer(entity.layer)

        self.entities[entity.entity_id] = entity

        return entity.entity_id

    def remove_entity(self, entity_id: UUID) -> Entity:

        if entity_id not in self.entities:
            raise KeyError(entity_id)

        return self.entities.pop(entity_id)

    def get_entity(self, entity_id: UUID) -> Entity | None:

        return self.entities.get(entity_id)

    def clear(self) -> None:

        self.entities.clear()

    # --------------------------------------------------------
    # Selection
    # --------------------------------------------------------

    def select_entity(self, entity_id: UUID) -> None:

        entity = self.get_entity(entity_id)

        if entity is None:
            raise KeyError(entity_id)

        entity.select()

    def deselect_all(self) -> None:

        for entity in self.entities.values():
            entity.deselect()

    def selected_entities(self) -> list[Entity]:

        return [
            entity
            for entity in self.entities.values()
            if entity.selected
        ]

    # --------------------------------------------------------
    # Queries
    # --------------------------------------------------------

    @property
    def entity_count(self) -> int:
        return len(self.entities)

    @property
    def layer_count(self) -> int:
        return len(self.layers)
'@ | Set-Content -LiteralPath $DocumentFile -Encoding UTF8

Write-Host "CREATE: sovereign_cad\core\document\document.py" -ForegroundColor Green

# ------------------------------------------------------------
# Document exports
# ------------------------------------------------------------

$DocumentInit = Join-Path `
    -Path $Root `
    -ChildPath "sovereign_cad\core\document\__init__.py"

@'
from .document import Document
from .layer import Layer

__all__ = [
    "Document",
    "Layer",
]
'@ | Set-Content -LiteralPath $DocumentInit -Encoding UTF8

Write-Host "CREATE: document exports" -ForegroundColor Green

# ------------------------------------------------------------
# Entity tests
# ------------------------------------------------------------

Write-Host "[7/9] Creating entity tests..." -ForegroundColor Yellow

$EntityTestFile = Join-Path `
    -Path $Root `
    -ChildPath "sovereign_cad\tests\entities\test_entities.py"

@'
from sovereign_cad.core.entities import (
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
'@ | Set-Content -LiteralPath $EntityTestFile -Encoding UTF8

# ------------------------------------------------------------
# Document tests
# ------------------------------------------------------------

$DocumentTestFile = Join-Path `
    -Path $Root `
    -ChildPath "sovereign_cad\tests\document\test_document.py"

@'
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
'@ | Set-Content -LiteralPath $DocumentTestFile -Encoding UTF8

Write-Host "CREATE: Stage 2 tests" -ForegroundColor Green

# ------------------------------------------------------------
# Verification
# ------------------------------------------------------------

Write-Host "[8/9] Verifying Stage 2 imports..." -ForegroundColor Yellow

python -c "from sovereign_cad.core.entities import Entity, LineEntity, CircleEntity; from sovereign_cad.core.document import Document, Layer; print('ENTITY + DOCUMENT ENGINE IMPORT: OK')"

if ($LASTEXITCODE -ne 0) {
    throw "Stage 2 import verification failed."
}

# ------------------------------------------------------------
# Compile
# ------------------------------------------------------------

Write-Host "[9/9] Running syntax checks and tests..." -ForegroundColor Yellow

python -m compileall -q sovereign_cad

if ($LASTEXITCODE -ne 0) {
    throw "Python syntax verification failed."
}

# Disable third-party pytest plugin autoload.
# This prevents unrelated environment plugins from
# interfering with SovereignCAD tests.

$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"

python -m pytest `
    .\sovereign_cad\tests\test_geometry.py `
    .\sovereign_cad\tests\entities\test_entities.py `
    .\sovereign_cad\tests\document\test_document.py `
    -q

if ($LASTEXITCODE -ne 0) {
    throw "SovereignCAD Stage 2 tests failed."
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "       SOVEREIGNCAD STAGE 2: SUCCESS" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Geometry Kernel       : ONLINE" -ForegroundColor Green
Write-Host "Entity Engine         : ONLINE" -ForegroundColor Green
Write-Host "Document Engine       : ONLINE" -ForegroundColor Green
Write-Host "Layer System          : ONLINE" -ForegroundColor Green
Write-Host "Selection System      : ONLINE" -ForegroundColor Green
Write-Host "Tests                 : PASSED" -ForegroundColor Green
Write-Host ""
Write-Host "Next stage:" -ForegroundColor Cyan
Write-Host "Command Engine + Undo/Redo" -ForegroundColor Cyan
Write-Host ""