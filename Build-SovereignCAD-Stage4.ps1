[CmdletBinding()]
param(
    [switch]$RunTests
)

$ErrorActionPreference = "Stop"

# ============================================================
# SOVEREIGNCAD BUILD SYSTEM
# STAGE 4 - TRANSFORMS + SPATIAL + SELECTION
# ============================================================

$Root = (Get-Location).Path

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "             SOVEREIGNCAD BUILD SYSTEM" -ForegroundColor Cyan
Write-Host "             STAGE 4 - SPATIAL CORE" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Project: $Root" -ForegroundColor Gray
Write-Host ""

# ============================================================
# 1. PYTHON
# ============================================================

Write-Host "[1/10] Checking Python..." -ForegroundColor Yellow

$Python = Get-Command python -ErrorAction SilentlyContinue

if (-not $Python) {
    throw "Python was not found. Activate the .venv first."
}

Write-Host "Python: $($Python.Source)" -ForegroundColor Green
Write-Host "Version: $(python --version)" -ForegroundColor Green

# ============================================================
# 2. VERIFY PREVIOUS STAGES
# ============================================================

Write-Host "[2/10] Verifying previous stages..." -ForegroundColor Yellow

$env:PYTHONPATH = $Root
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"

python -c "from sovereign_cad.core.geometry import Point2, BoundingBox2; from sovereign_cad.core.entities import Entity, LineEntity, CircleEntity, EntityRegistry; from sovereign_cad.core.document import Document; from sovereign_cad.core.commands import CommandManager; print('PREVIOUS STAGES: OK')"

if ($LASTEXITCODE -ne 0) {
    throw "Previous SovereignCAD stages could not be imported."
}

# ============================================================
# 3. CREATE DIRECTORIES
# ============================================================

Write-Host "[3/10] Creating Stage 4 architecture..." -ForegroundColor Yellow

$Directories = @(
    "sovereign_cad\core\transforms",
    "sovereign_cad\core\spatial",
    "sovereign_cad\core\selection",
    "sovereign_cad\tests\transforms",
    "sovereign_cad\tests\spatial",
    "sovereign_cad\tests\selection"
)

foreach ($Directory in $Directories) {

    $Path = Join-Path $Root $Directory

    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

# ============================================================
# 4. TRANSFORM ENGINE
# ============================================================

Write-Host "[4/10] Building transform engine..." -ForegroundColor Yellow

$TransformFile = Join-Path `
    $Root `
    "sovereign_cad\core\transforms\transform2d.py"

@'
from __future__ import annotations

from dataclasses import dataclass
from math import cos, sin

from ..geometry import Point2, Vector2


@dataclass(frozen=True, slots=True)
class Transform2D:
    """
    2D affine transformation.

    x' = a*x + c*y + tx
    y' = b*x + d*y + ty
    """

    a: float = 1.0
    b: float = 0.0
    c: float = 0.0
    d: float = 1.0
    tx: float = 0.0
    ty: float = 0.0

    @classmethod
    def identity(cls) -> Transform2D:
        return cls()

    @classmethod
    def translation(
        cls,
        x: float,
        y: float,
    ) -> Transform2D:

        return cls(
            tx=x,
            ty=y,
        )

    @classmethod
    def rotation(
        cls,
        angle: float,
    ) -> Transform2D:

        c = cos(angle)
        s = sin(angle)

        return cls(
            a=c,
            b=s,
            c=-s,
            d=c,
        )

    @classmethod
    def scaling(
        cls,
        x: float,
        y: float | None = None,
    ) -> Transform2D:

        if y is None:
            y = x

        return cls(
            a=x,
            d=y,
        )

    def apply_point(
        self,
        point: Point2,
    ) -> Point2:

        return Point2(
            self.a * point.x
            + self.c * point.y
            + self.tx,

            self.b * point.x
            + self.d * point.y
            + self.ty,
        )

    def apply_vector(
        self,
        vector: Vector2,
    ) -> Vector2:

        return Vector2(
            self.a * vector.x
            + self.c * vector.y,

            self.b * vector.x
            + self.d * vector.y,
        )

    def then(
        self,
        other: Transform2D,
    ) -> Transform2D:

        """
        Apply this transform first,
        then the other transform.
        """

        return Transform2D(
            a=other.a * self.a + other.c * self.b,
            b=other.b * self.a + other.d * self.b,
            c=other.a * self.c + other.c * self.d,
            d=other.b * self.c + other.d * self.d,

            tx=(
                other.a * self.tx
                + other.c * self.ty
                + other.tx
            ),

            ty=(
                other.b * self.tx
                + other.d * self.ty
                + other.ty
            ),
        )

    def __matmul__(
        self,
        other: Transform2D,
    ) -> Transform2D:

        return self.then(other)
'@ | Set-Content `
    -LiteralPath $TransformFile `
    -Encoding UTF8

$TransformInit = Join-Path `
    $Root `
    "sovereign_cad\core\transforms\__init__.py"

@'
from .transform2d import Transform2D

__all__ = [
    "Transform2D",
]
'@ | Set-Content `
    -LiteralPath $TransformInit `
    -Encoding UTF8

Write-Host "CREATE: transform engine" -ForegroundColor Green

# ============================================================
# 5. SPATIAL INDEX
# ============================================================

Write-Host "[5/10] Building spatial index..." -ForegroundColor Yellow

$SpatialFile = Join-Path `
    $Root `
    "sovereign_cad\core\spatial\index.py"

@'
from __future__ import annotations

from uuid import UUID

from ..entities import Entity
from ..geometry import BoundingBox2, Point2


class SpatialIndex:
    """
    Stage 4 spatial index.

    Uses bounding boxes for deterministic spatial queries.

    The interface is intentionally independent from the
    underlying implementation so it can later be upgraded
    to an R-tree or other acceleration structure.
    """

    def __init__(self):

        self._boxes: dict[UUID, BoundingBox2] = {}

    def clear(self) -> None:

        self._boxes.clear()

    def insert(
        self,
        entity: Entity,
    ) -> None:

        self._boxes[entity.id] = entity.bounding_box()

    def remove(
        self,
        entity_id: UUID,
    ) -> None:

        self._boxes.pop(
            entity_id,
            None,
        )

    def update(
        self,
        entity: Entity,
    ) -> None:

        self.insert(entity)

    def rebuild(
        self,
        entities,
    ) -> None:

        self.clear()

        for entity in entities:
            self.insert(entity)

    def get_box(
        self,
        entity_id: UUID,
    ) -> BoundingBox2 | None:

        return self._boxes.get(entity_id)

    def query_box(
        self,
        box: BoundingBox2,
    ) -> list[UUID]:

        return [
            entity_id
            for entity_id, entity_box
            in self._boxes.items()
            if entity_box.intersects(box)
        ]

    def query_point(
        self,
        point: Point2,
    ) -> list[UUID]:

        return [
            entity_id
            for entity_id, box
            in self._boxes.items()
            if box.contains(point)
        ]

    def __len__(self) -> int:

        return len(self._boxes)
'@ | Set-Content `
    -LiteralPath $SpatialFile `
    -Encoding UTF8

$SpatialInit = Join-Path `
    $Root `
    "sovereign_cad\core\spatial\__init__.py"

@'
from .index import SpatialIndex

__all__ = [
    "SpatialIndex",
]
'@ | Set-Content `
    -LiteralPath $SpatialInit `
    -Encoding UTF8

Write-Host "CREATE: spatial index" -ForegroundColor Green

# ============================================================
# 6. SELECTION ENGINE
# ============================================================

Write-Host "[6/10] Building selection engine..." -ForegroundColor Yellow

$SelectionFile = Join-Path `
    $Root `
    "sovereign_cad\core\selection\engine.py"

@'
from __future__ import annotations

from ..entities import EntityRegistry
from ..geometry import BoundingBox2, Point2
from ..spatial import SpatialIndex


class SelectionEngine:

    def __init__(
        self,
        registry: EntityRegistry,
        spatial_index: SpatialIndex,
    ):

        self.registry = registry
        self.spatial_index = spatial_index

    def clear(self) -> None:

        self.registry.clear_selection()

    def select(
        self,
        entity_id,
    ) -> None:

        self.registry.select(entity_id)

    def deselect(
        self,
        entity_id,
    ) -> None:

        self.registry.deselect(entity_id)

    def selected(self):

        return self.registry.selected()

    def pick(
        self,
        point: Point2,
    ) -> list:

        ids = self.spatial_index.query_point(
            point
        )

        entities = []

        for entity_id in ids:

            entity = self.registry.get(
                entity_id
            )

            if (
                entity is not None
                and entity.visible
            ):
                entities.append(entity)

        return entities

    def window_select(
        self,
        box: BoundingBox2,
        crossing: bool = True,
    ) -> list:

        if crossing:

            ids = self.spatial_index.query_box(
                box
            )

        else:

            ids = []

            for entity in self.registry.visible():

                entity_box = entity.bounding_box()

                if (
                    entity_box.min_x >= box.min_x
                    and entity_box.max_x <= box.max_x
                    and entity_box.min_y >= box.min_y
                    and entity_box.max_y <= box.max_y
                ):

                    ids.append(entity.id)

        return [
            self.registry.get(entity_id)
            for entity_id in ids
            if self.registry.get(entity_id) is not None
        ]

    def apply_selection(
        self,
        entities,
        additive: bool = False,
    ) -> None:

        if not additive:
            self.clear()

        for entity in entities:

            entity.selected = True
'@ | Set-Content `
    -LiteralPath $SelectionFile `
    -Encoding UTF8

$SelectionInit = Join-Path `
    $Root `
    "sovereign_cad\core\selection\__init__.py"

@'
from .engine import SelectionEngine

__all__ = [
    "SelectionEngine",
]
'@ | Set-Content `
    -LiteralPath $SelectionInit `
    -Encoding UTF8

Write-Host "CREATE: selection engine" -ForegroundColor Green

# ============================================================
# 7. TRANSFORM TESTS
# ============================================================

Write-Host "[7/10] Creating Stage 4 tests..." -ForegroundColor Yellow

$TransformTest = Join-Path `
    $Root `
    "sovereign_cad\tests\transforms\test_transform2d.py"

@'
from math import pi

from sovereign_cad.core.geometry import Point2, Vector2
from sovereign_cad.core.transforms import Transform2D


def test_identity():

    transform = Transform2D.identity()

    result = transform.apply_point(
        Point2(3, 4)
    )

    assert result.almost_equal(
        Point2(3, 4)
    )


def test_translation():

    transform = Transform2D.translation(
        10,
        20,
    )

    result = transform.apply_point(
        Point2(1, 2)
    )

    assert result.almost_equal(
        Point2(11, 22)
    )


def test_rotation():

    transform = Transform2D.rotation(
        pi / 2
    )

    result = transform.apply_point(
        Point2(1, 0)
    )

    assert result.almost_equal(
        Point2(0, 1)
    )


def test_scaling():

    transform = Transform2D.scaling(
        2,
        3,
    )

    result = transform.apply_point(
        Point2(4, 5)
    )

    assert result.almost_equal(
        Point2(8, 15)
    )


def test_vector_ignores_translation():

    transform = Transform2D.translation(
        100,
        100,
    )

    result = transform.apply_vector(
        Vector2(2, 3)
    )

    assert result == Vector2(
        2,
        3,
    )


def test_composition():

    scale = Transform2D.scaling(2)

    move = Transform2D.translation(
        10,
        0,
    )

    combined = scale.then(move)

    result = combined.apply_point(
        Point2(1, 0)
    )

    assert result.almost_equal(
        Point2(12, 0)
    )
'@ | Set-Content `
    -LiteralPath $TransformTest `
    -Encoding UTF8

# ============================================================
# 8. SPATIAL TESTS
# ============================================================

$SpatialTest = Join-Path `
    $Root `
    "sovereign_cad\tests\spatial\test_spatial_index.py"

@'
from sovereign_cad.core.entities import (
    CircleEntity,
    EntityRegistry,
    LineEntity,
)

from sovereign_cad.core.geometry import (
    BoundingBox2,
    Point2,
)

from sovereign_cad.core.spatial import SpatialIndex


def create_scene():

    registry = EntityRegistry()

    line = LineEntity(
        start=Point2(0, 0),
        end=Point2(10, 0),
    )

    circle = CircleEntity(
        center=Point2(20, 20),
        radius=5,
    )

    registry.add(line)
    registry.add(circle)

    return registry, line, circle


def test_insert():

    registry, line, circle = create_scene()

    index = SpatialIndex()

    index.rebuild(registry)

    assert len(index) == 2


def test_point_query():

    registry, line, circle = create_scene()

    index = SpatialIndex()

    index.rebuild(registry)

    result = index.query_point(
        Point2(5, 0)
    )

    assert line.id in result
    assert circle.id not in result


def test_box_query():

    registry, line, circle = create_scene()

    index = SpatialIndex()

    index.rebuild(registry)

    box = BoundingBox2(
        -1,
        -1,
        11,
        1,
    )

    result = index.query_box(box)

    assert line.id in result
    assert circle.id not in result


def test_remove():

    registry, line, circle = create_scene()

    index = SpatialIndex()

    index.rebuild(registry)

    index.remove(line.id)

    assert len(index) == 1
'@ | Set-Content `
    -LiteralPath $SpatialTest `
    -Encoding UTF8

# ============================================================
# 9. SELECTION TESTS
# ============================================================

$SelectionTest = Join-Path `
    $Root `
    "sovereign_cad\tests\selection\test_selection.py"

@'
from sovereign_cad.core.entities import (
    CircleEntity,
    EntityRegistry,
    LineEntity,
)

from sovereign_cad.core.geometry import (
    BoundingBox2,
    Point2,
)

from sovereign_cad.core.selection import (
    SelectionEngine,
)

from sovereign_cad.core.spatial import (
    SpatialIndex,
)


def create_selection_engine():

    registry = EntityRegistry()

    line = LineEntity(
        start=Point2(0, 0),
        end=Point2(10, 0),
    )

    circle = CircleEntity(
        center=Point2(20, 20),
        radius=5,
    )

    registry.add(line)
    registry.add(circle)

    spatial = SpatialIndex()

    spatial.rebuild(registry)

    selection = SelectionEngine(
        registry,
        spatial,
    )

    return selection, line, circle


def test_pick():

    selection, line, circle = (
        create_selection_engine()
    )

    result = selection.pick(
        Point2(5, 0)
    )

    assert line in result
    assert circle not in result


def test_crossing_window():

    selection, line, circle = (
        create_selection_engine()
    )

    box = BoundingBox2(
        -1,
        -1,
        11,
        1,
    )

    result = selection.window_select(
        box,
        crossing=True,
    )

    assert line in result
    assert circle not in result


def test_contained_window():

    selection, line, circle = (
        create_selection_engine()
    )

    box = BoundingBox2(
        -1,
        -1,
        11,
        1,
    )

    result = selection.window_select(
        box,
        crossing=False,
    )

    assert line in result
    assert circle not in result


def test_apply_selection():

    selection, line, circle = (
        create_selection_engine()
    )

    selection.apply_selection(
        [line]
    )

    assert line.selected
    assert not circle.selected


def test_additive_selection():

    selection, line, circle = (
        create_selection_engine()
    )

    selection.apply_selection(
        [line]
    )

    selection.apply_selection(
        [circle],
        additive=True,
    )

    assert line.selected
    assert circle.selected


def test_clear_selection():

    selection, line, circle = (
        create_selection_engine()
    )

    selection.apply_selection(
        [line, circle]
    )

    selection.clear()

    assert not line.selected
    assert not circle.selected
'@ | Set-Content `
    -LiteralPath $SelectionTest `
    -Encoding UTF8

# ============================================================
# CORE PACKAGE EXPORT
# ============================================================

$CoreInit = Join-Path `
    $Root `
    "sovereign_cad\core\__init__.py"

@'
from .geometry import *
from .entities import *
from .transforms import *
from .spatial import *
from .selection import *
'@ | Set-Content `
    -LiteralPath $CoreInit `
    -Encoding UTF8

Write-Host "CREATE: core exports" -ForegroundColor Green

# ============================================================
# PACKAGE ROOT
# ============================================================

$PackageInit = Join-Path `
    $Root `
    "sovereign_cad\__init__.py"

if (-not (Test-Path $PackageInit)) {

@'
"""
SovereignCAD package.
"""
'@ | Set-Content `
    -LiteralPath $PackageInit `
    -Encoding UTF8

}

# ============================================================
# 10. VALIDATION
# ============================================================

Write-Host "[8/10] Running package validation..." -ForegroundColor Yellow

$env:PYTHONPATH = $Root
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"

python -c "import sovereign_cad; import sovereign_cad.core; print('PACKAGE: OK')"

if ($LASTEXITCODE -ne 0) {
    throw "SovereignCAD package validation failed."
}

python -c "from sovereign_cad.core.transforms import Transform2D; from sovereign_cad.core.spatial import SpatialIndex; from sovereign_cad.core.selection import SelectionEngine; print('STAGE 4 IMPORTS: OK')"

if ($LASTEXITCODE -ne 0) {
    throw "Stage 4 imports failed."
}

# ============================================================
# SYNTAX
# ============================================================

Write-Host "[9/10] Running Python syntax verification..." -ForegroundColor Yellow

python -m compileall -q sovereign_cad

if ($LASTEXITCODE -ne 0) {
    throw "Python syntax verification failed."
}

Write-Host "PYTHON SYNTAX: OK" -ForegroundColor Green

# ============================================================
# TESTS
# ============================================================

Write-Host "[10/10] Running complete SovereignCAD test suite..." -ForegroundColor Yellow

python -m pytest `
    --rootdir="$Root" `
    "$Root\sovereign_cad\tests" `
    -q

if ($LASTEXITCODE -ne 0) {
    throw "SovereignCAD tests failed."
}

# ============================================================
# SUCCESS
# ============================================================

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "             SOVEREIGNCAD STAGE 4: SUCCESS" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""

Write-Host "Geometry Kernel       : ONLINE" -ForegroundColor Green
Write-Host "Entity Engine         : ONLINE" -ForegroundColor Green
Write-Host "Document Engine       : ONLINE" -ForegroundColor Green
Write-Host "Command Engine        : ONLINE" -ForegroundColor Green
Write-Host "Undo System           : ONLINE" -ForegroundColor Green
Write-Host "Redo System           : ONLINE" -ForegroundColor Green
Write-Host "Transform Engine      : ONLINE" -ForegroundColor Green
Write-Host "Spatial Index         : ONLINE" -ForegroundColor Green
Write-Host "Selection Engine      : ONLINE" -ForegroundColor Green
Write-Host "Tests                 : PASSED" -ForegroundColor Green

Write-Host ""
Write-Host "Next stage:" -ForegroundColor Cyan
Write-Host "Rendering + Viewport + Interactive CAD Canvas" -ForegroundColor Cyan
Write-Host ""