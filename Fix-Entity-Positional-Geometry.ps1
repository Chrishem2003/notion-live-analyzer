$ErrorActionPreference = "Stop"

$Root = (Get-Location).Path
$EntityDir = Join-Path $Root "sovereign_cad\core\entities"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "     SOVEREIGNCAD ENTITY CONSTRUCTOR FIX" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/4] Updating entity constructors..." -ForegroundColor Yellow

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


@dataclass
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
            self.start,
            self.end,
            entity_id=self.entity_id,
            layer=self.layer,
            visible=self.visible,
            selected=self.selected,
        )


@dataclass
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
            self.center,
            self.radius,
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
'@ | Set-Content `
    -LiteralPath (Join-Path $EntityDir "entity.py") `
    -Encoding UTF8

Write-Host "ENTITY.PY: FIXED" -ForegroundColor Green


Write-Host "[2/4] Clearing Python caches..." -ForegroundColor Yellow

Get-ChildItem `
    -Path $Root `
    -Recurse `
    -Directory `
    -Filter "__pycache__" `
    -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "CACHE: CLEARED" -ForegroundColor Green


Write-Host "[3/4] Testing entity constructors..." -ForegroundColor Yellow

$Python = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    $Python = "python"
}

& $Python -c "from sovereign_cad.core.entities import LineEntity, CircleEntity; from sovereign_cad.core.geometry import Point2; line=LineEntity(Point2(0,0),Point2(10,0)); circle=CircleEntity(Point2(5,5),10); assert line.length == 10; assert circle.radius == 10; print('CONSTRUCTORS: OK'); print('LINE LENGTH:', line.length); print('CIRCLE RADIUS:', circle.radius)"

if ($LASTEXITCODE -ne 0) {
    throw "Entity constructor verification failed."
}

Write-Host "CONSTRUCTORS: OK" -ForegroundColor Green


Write-Host "[4/4] Running complete SovereignCAD test suite..." -ForegroundColor Yellow

& $Python -m pytest sovereign_cad/tests -q

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "TESTS STILL HAVE FAILURES." -ForegroundColor Red
    Write-Host "The constructor problem is fixed; remaining failures will now be isolated." -ForegroundColor Yellow
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "       SOVEREIGNCAD: ALL TESTS PASSED" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "ENTITY ENGINE: ONLINE" -ForegroundColor Green
Write-Host "COMMAND ENGINE: ONLINE" -ForegroundColor Green
Write-Host "DOCUMENT ENGINE: ONLINE" -ForegroundColor Green
Write-Host "SPATIAL ENGINE: ONLINE" -ForegroundColor Green
Write-Host "SELECTION ENGINE: ONLINE" -ForegroundColor Green
Write-Host ""
Write-Host "READY FOR NEXT STAGE." -ForegroundColor Cyan