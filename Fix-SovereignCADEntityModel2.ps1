$ErrorActionPreference = "Stop"

$Root = (Get-Location).Path
$EntityDir = Join-Path $Root "sovereign_cad\core\entities"
$BackupDir = Join-Path $Root "sovereign_cad\_backup_entity_fix"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "       SOVEREIGNCAD ENTITY MODEL REPAIR 2" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

New-Item -ItemType Directory -Force -Path $EntityDir | Out-Null
New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null

Write-Host "[1/6] Backing up entity files..." -ForegroundColor Yellow

foreach ($file in @(
    "entity.py",
    "line.py",
    "circle.py",
    "entity_id.py",
    "registry.py",
    "__init__.py"
)) {
    $source = Join-Path $EntityDir $file

    if (Test-Path $source) {
        Copy-Item $source (Join-Path $BackupDir $file) -Force
    }
}

Write-Host "BACKUP: OK" -ForegroundColor Green


Write-Host "[2/6] Writing entity_id.py..." -ForegroundColor Yellow

@'
from __future__ import annotations

from uuid import UUID, uuid4


def create_entity_id() -> UUID:
    return uuid4()


def is_valid_entity_id(value) -> bool:
    if isinstance(value, UUID):
        return True

    if not isinstance(value, str):
        return False

    try:
        UUID(value)
        return True
    except (ValueError, TypeError, AttributeError):
        return False


__all__ = [
    "create_entity_id",
    "is_valid_entity_id",
]
'@ | Set-Content (Join-Path $EntityDir "entity_id.py") -Encoding UTF8


Write-Host "[3/6] Writing canonical entity.py..." -ForegroundColor Yellow

@'
from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from ..geometry import (
    BoundingBox2,
    Circle2,
    LineSegment2,
    Point2,
)


@dataclass(kw_only=True)
class Entity:

    entity_id: UUID = field(default_factory=uuid4)

    layer: str = "0"

    visible: bool = True

    selected: bool = False

    @property
    def id(self) -> UUID:
        return self.entity_id

    @property
    def entity_type(self) -> str:
        return self.__class__.__name__.replace("Entity", "").upper()

    def set_layer(self, layer: str) -> None:
        if not isinstance(layer, str) or not layer.strip():
            raise ValueError("Layer must be a non-empty string.")

        self.layer = layer.strip()

    def bounding_box(self) -> BoundingBox2:
        raise NotImplementedError

    def clone(self):
        raise NotImplementedError


@dataclass(kw_only=True)
class LineEntity(Entity):

    start: Point2 = field(
        default_factory=lambda: Point2(0.0, 0.0)
    )

    end: Point2 = field(
        default_factory=lambda: Point2(1.0, 0.0)
    )

    def geometry(self) -> LineSegment2:
        return LineSegment2(
            self.start,
            self.end,
        )

    @property
    def length(self) -> float:
        return self.start.distance_to(self.end)

    def bounding_box(self) -> BoundingBox2:
        return BoundingBox2.from_points(
            [
                self.start,
                self.end,
            ]
        )

    def clone(self) -> "LineEntity":
        return LineEntity(
            start=self.start,
            end=self.end,
            entity_id=self.entity_id,
            layer=self.layer,
            visible=self.visible,
            selected=self.selected,
        )


@dataclass(kw_only=True)
class CircleEntity(Entity):

    center: Point2 = field(
        default_factory=lambda: Point2(0.0, 0.0)
    )

    radius: float = 1.0

    def geometry(self) -> Circle2:
        return Circle2(
            self.center,
            self.radius,
        )

    def bounding_box(self) -> BoundingBox2:
        return BoundingBox2(
            self.center.x - self.radius,
            self.center.y - self.radius,
            self.center.x + self.radius,
            self.center.y + self.radius,
        )

    def clone(self) -> "CircleEntity":
        return CircleEntity(
            center=self.center,
            radius=self.radius,
            entity_id=self.entity_id,
            layer=self.layer,
            visible=self.visible,
            selected=self.selected,
        )


__all__ = [
    "Entity",
    "LineEntity",
    "CircleEntity",
]
'@ | Set-Content (Join-Path $EntityDir "entity.py") -Encoding UTF8


Write-Host "[4/6] Repairing entity exports..." -ForegroundColor Yellow

@'
from .entity import Entity, LineEntity

__all__ = [
    "Entity",
    "LineEntity",
]
'@ | Set-Content (Join-Path $EntityDir "line.py") -Encoding UTF8


@'
from .entity import Entity, CircleEntity

__all__ = [
    "Entity",
    "CircleEntity",
]
'@ | Set-Content (Join-Path $EntityDir "circle.py") -Encoding UTF8


@'
from __future__ import annotations

from uuid import UUID

from .entity import (
    Entity,
    LineEntity,
    CircleEntity,
)

from .entity_id import (
    create_entity_id,
    is_valid_entity_id,
)


class EntityRegistry:

    def __init__(self):
        self._entities: dict[UUID, Entity] = {}

    def add(self, entity: Entity) -> UUID:

        if entity.entity_id in self._entities:
            raise ValueError(
                f"Entity {entity.entity_id} already exists."
            )

        self._entities[entity.entity_id] = entity

        return entity.entity_id

    def remove(self, entity_id: UUID) -> Entity:

        if entity_id not in self._entities:
            raise KeyError(
                f"Entity {entity_id} does not exist."
            )

        return self._entities.pop(entity_id)

    def get(self, entity_id: UUID) -> Entity | None:
        return self._entities.get(entity_id)

    def all(self) -> list[Entity]:
        return list(self._entities.values())

    def visible(self) -> list[Entity]:
        return [
            entity
            for entity in self._entities.values()
            if entity.visible
        ]

    def selected(self) -> list[Entity]:
        return [
            entity
            for entity in self._entities.values()
            if entity.selected
        ]

    def clear_selection(self) -> None:
        for entity in self._entities.values():
            entity.selected = False

    def select(self, entity_id: UUID) -> None:

        entity = self.get(entity_id)

        if entity is None:
            raise KeyError(
                f"Entity {entity_id} does not exist."
            )

        entity.selected = True

    def deselect(self, entity_id: UUID) -> None:

        entity = self.get(entity_id)

        if entity is None:
            raise KeyError(
                f"Entity {entity_id} does not exist."
            )

        entity.selected = False

    def __len__(self) -> int:
        return len(self._entities)

    def __iter__(self):
        return iter(self._entities.values())


__all__ = [
    "Entity",
    "LineEntity",
    "CircleEntity",
    "EntityRegistry",
    "create_entity_id",
    "is_valid_entity_id",
]
'@ | Set-Content (Join-Path $EntityDir "__init__.py") -Encoding UTF8


Write-Host "[5/6] Clearing Python cache..." -ForegroundColor Yellow

Get-ChildItem `
    -Path $Root `
    -Recurse `
    -Directory `
    -Filter "__pycache__" `
    -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "CACHE: CLEARED" -ForegroundColor Green


Write-Host "[6/6] Running entity verification..." -ForegroundColor Yellow

$VerifyFile = Join-Path $Root "_verify_entity_model.py"

@'
from sovereign_cad.core.entities import (
    Entity,
    LineEntity,
    CircleEntity,
    EntityRegistry,
    is_valid_entity_id,
)

from sovereign_cad.core.geometry import Point2


line = LineEntity(
    Point2(0, 0),
    Point2(10, 0),
)

assert line.start == Point2(0, 0)
assert line.end == Point2(10, 0)
assert line.length == 10
assert line.entity_type == "LINE"

circle = CircleEntity(
    Point2(5, 5),
    10,
)

assert circle.center == Point2(5, 5)
assert circle.radius == 10
assert circle.entity_type == "CIRCLE"

assert line.entity_id != circle.entity_id

assert is_valid_entity_id(line.entity_id)
assert is_valid_entity_id(circle.entity_id)

line.set_layer("WALLS")

assert line.layer == "WALLS"

line_box = line.bounding_box()

assert line_box.min_x == 0
assert line_box.min_y == 0
assert line_box.max_x == 10
assert line_box.max_y == 0

circle_box = circle.bounding_box()

assert circle_box.min_x == -5
assert circle_box.min_y == -5
assert circle_box.max_x == 15
assert circle_box.max_y == 15

registry = EntityRegistry()

registry.add(line)
registry.add(circle)

assert len(registry) == 2

print("ENTITY MODEL: OK")
print("LINE: OK")
print("CIRCLE: OK")
print("ENTITY IDs: OK")
print("LAYER: OK")
print("REGISTRY: OK")
'@ | Set-Content $VerifyFile -Encoding UTF8

$Python = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    $Python = "python"
}

& $Python $VerifyFile

$verifyExit = $LASTEXITCODE

Remove-Item $VerifyFile -Force -ErrorAction SilentlyContinue

if ($verifyExit -ne 0) {
    Write-Host ""
    Write-Host "ENTITY VERIFICATION FAILED." -ForegroundColor Red
    exit $verifyExit
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "       ENTITY MODEL REPAIR: SUCCESS" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""

Write-Host "Running full SovereignCAD tests..." -ForegroundColor Cyan

& $Python -m pytest sovereign_cad/tests -q

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Some tests still fail." -ForegroundColor Yellow
    Write-Host "The entity constructor problem has been repaired." -ForegroundColor Yellow
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "       SOVEREIGNCAD: ALL TESTS PASSED" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green