[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

# ============================================================
# SOVEREIGNCAD BUILD SYSTEM
# STAGE 5 - VIEWPORT + RENDERING
# CLEAN BUILD v2
# ============================================================

$Root = (Get-Location).Path

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "             SOVEREIGNCAD BUILD SYSTEM" -ForegroundColor Cyan
Write-Host "             STAGE 5 - VIEWPORT + RENDERING" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Project: $Root" -ForegroundColor Gray
Write-Host ""

# ============================================================
# FILE WRITERS
# ============================================================

function Write-ProjectFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RelativePath,

        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string]$Content
    )

    $FullPath = Join-Path $Root $RelativePath
    $Parent = Split-Path -Parent $FullPath

    if (-not (Test-Path -LiteralPath $Parent)) {
        New-Item `
            -ItemType Directory `
            -Path $Parent `
            -Force | Out-Null
    }

    [System.IO.File]::WriteAllText(
        $FullPath,
        $Content,
        [System.Text.UTF8Encoding]::new($false)
    )

    Write-Host "CREATE/UPDATE: $RelativePath" -ForegroundColor Green
}

function Write-EmptyProjectFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RelativePath
    )

    $FullPath = Join-Path $Root $RelativePath
    $Parent = Split-Path -Parent $FullPath

    if (-not (Test-Path -LiteralPath $Parent)) {
        New-Item `
            -ItemType Directory `
            -Path $Parent `
            -Force | Out-Null
    }

    [System.IO.File]::WriteAllText(
        $FullPath,
        "",
        [System.Text.UTF8Encoding]::new($false)
    )

    Write-Host "CREATE/UPDATE: $RelativePath" -ForegroundColor Green
}

# ============================================================
# 1. PROJECT
# ============================================================

Write-Host "[1/10] Verifying project..." -ForegroundColor Yellow

if (-not (Test-Path -LiteralPath (Join-Path $Root "sovereign_cad"))) {
    throw "sovereign_cad directory was not found."
}

Write-Host "PROJECT ROOT: OK" -ForegroundColor Green

# ============================================================
# 2. PYTHON
# ============================================================

Write-Host "[2/10] Selecting Python..." -ForegroundColor Yellow

$Python = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $Python)) {

    $PythonCommand = Get-Command python -ErrorAction SilentlyContinue

    if (-not $PythonCommand) {
        throw "Python was not found."
    }

    $Python = $PythonCommand.Source
}

Write-Host "Python: $Python" -ForegroundColor Green

$PythonVersion = & $Python --version

if ($LASTEXITCODE -ne 0) {
    throw "Python could not be executed."
}

Write-Host "Version: $PythonVersion" -ForegroundColor Green

# ============================================================
# 3. IMPORT PATH
# ============================================================

Write-Host "[3/10] Configuring Python import path..." -ForegroundColor Yellow

$env:PYTHONPATH = $Root
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"

Write-Host "PYTHONPATH: $env:PYTHONPATH" -ForegroundColor Green

& $Python -c "import sovereign_cad; import sovereign_cad.core; print('IMPORT PATH: OK'); print('SOVEREIGNCAD: OK'); print('CORE: OK')"

if ($LASTEXITCODE -ne 0) {
    throw "SovereignCAD import path validation failed."
}

# ============================================================
# 4. PACKAGE STRUCTURE
# ============================================================

Write-Host "[4/10] Repairing Stage 5 package structure..." -ForegroundColor Yellow

$Directories = @(
    "sovereign_cad\ui",
    "sovereign_cad\ui\viewport",
    "sovereign_cad\ui\canvas",
    "sovereign_cad\rendering",
    "sovereign_cad\tests\viewport",
    "sovereign_cad\tests\canvas",
    "sovereign_cad\tests\rendering"
)

foreach ($Directory in $Directories) {

    $Path = Join-Path $Root $Directory

    if (-not (Test-Path -LiteralPath $Path)) {

        New-Item `
            -ItemType Directory `
            -Path $Path `
            -Force | Out-Null
    }
}

Write-ProjectFile `
    "sovereign_cad\ui\__init__.py" `
    @'
"""
SovereignCAD user interface package.
"""
'@

Write-ProjectFile `
    "sovereign_cad\ui\viewport\__init__.py" `
    @'
from .viewport import Viewport2D

__all__ = ["Viewport2D"]
'@

Write-ProjectFile `
    "sovereign_cad\ui\canvas\__init__.py" `
    @'
from .state import CanvasState

__all__ = ["CanvasState"]
'@

Write-ProjectFile `
    "sovereign_cad\rendering\__init__.py" `
    @'
from .renderer import RenderCommand, Renderer2D

__all__ = [
    "RenderCommand",
    "Renderer2D",
]
'@

Write-Host "PACKAGE STRUCTURE: OK" -ForegroundColor Green

# ============================================================
# 5. VALIDATE STAGE 1-4
# ============================================================

Write-Host "[5/10] Validating Stage 1-4..." -ForegroundColor Yellow

& $Python -c "from sovereign_cad.core.geometry import Point2,Vector2,BoundingBox2; from sovereign_cad.core.entities import Entity,LineEntity,CircleEntity,EntityRegistry; from sovereign_cad.core.transforms import Transform2D; from sovereign_cad.core.spatial import SpatialIndex; from sovereign_cad.core.selection import SelectionEngine; print('GEOMETRY: OK'); print('ENTITIES: OK'); print('TRANSFORMS: OK'); print('SPATIAL: OK'); print('SELECTION: OK'); print('STAGE 1-4 CORE: OK')"

if ($LASTEXITCODE -ne 0) {
    throw "Stage 1-4 core validation failed."
}

# ============================================================
# 6. VIEWPORT
# ============================================================

Write-Host "[6/10] Building viewport engine..." -ForegroundColor Yellow

Write-ProjectFile `
    "sovereign_cad\ui\viewport\viewport.py" `
    @'
from __future__ import annotations

from dataclasses import dataclass

from sovereign_cad.core.geometry import Point2, Vector2


@dataclass
class Viewport2D:

    width: float = 1200.0
    height: float = 800.0

    center: Point2 = Point2(
        0.0,
        0.0,
    )

    zoom: float = 1.0

    min_zoom: float = 0.0001
    max_zoom: float = 1000000.0

    def __post_init__(self):

        if self.width <= 0:
            raise ValueError(
                "Viewport width must be positive."
            )

        if self.height <= 0:
            raise ValueError(
                "Viewport height must be positive."
            )

        if self.zoom <= 0:
            raise ValueError(
                "Viewport zoom must be positive."
            )

        self.zoom = self._clamp_zoom(
            self.zoom
        )

    def _clamp_zoom(
        self,
        value: float,
    ) -> float:

        return max(
            self.min_zoom,
            min(
                self.max_zoom,
                value,
            ),
        )

    def world_to_screen(
        self,
        point: Point2,
    ) -> Point2:

        return Point2(
            (point.x - self.center.x)
            * self.zoom
            + self.width / 2.0,

            self.height / 2.0
            - (point.y - self.center.y)
            * self.zoom,
        )

    def screen_to_world(
        self,
        point: Point2,
    ) -> Point2:

        return Point2(
            (point.x - self.width / 2.0)
            / self.zoom
            + self.center.x,

            (self.height / 2.0 - point.y)
            / self.zoom
            + self.center.y,
        )

    def world_vector_to_screen(
        self,
        vector: Vector2,
    ) -> Vector2:

        return Vector2(
            vector.x * self.zoom,
            -vector.y * self.zoom,
        )

    def screen_vector_to_world(
        self,
        vector: Vector2,
    ) -> Vector2:

        return Vector2(
            vector.x / self.zoom,
            -vector.y / self.zoom,
        )

    def pan(
        self,
        delta_screen: Vector2,
    ) -> None:

        delta_world = self.screen_vector_to_world(
            delta_screen
        )

        self.center = Point2(
            self.center.x - delta_world.x,
            self.center.y - delta_world.y,
        )

    def pan_world(
        self,
        delta_world: Vector2,
    ) -> None:

        self.center = Point2(
            self.center.x + delta_world.x,
            self.center.y + delta_world.y,
        )

    def zoom_by(
        self,
        factor: float,
    ) -> None:

        if factor <= 0:
            raise ValueError(
                "Zoom factor must be positive."
            )

        self.zoom = self._clamp_zoom(
            self.zoom * factor
        )

    def set_zoom(
        self,
        zoom: float,
    ) -> None:

        if zoom <= 0:
            raise ValueError(
                "Zoom must be positive."
            )

        self.zoom = self._clamp_zoom(
            zoom
        )

    def reset(self) -> None:

        self.center = Point2(
            0.0,
            0.0,
        )

        self.zoom = 1.0

    def screen_center(self) -> Point2:

        return Point2(
            self.width / 2.0,
            self.height / 2.0,
        )
'@

# ============================================================
# 7. RENDERER
# ============================================================

Write-Host "[7/10] Building renderer..." -ForegroundColor Yellow

Write-ProjectFile `
    "sovereign_cad\rendering\renderer.py" `
    @'
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sovereign_cad.core.entities import (
    CircleEntity,
    Entity,
    LineEntity,
)

from sovereign_cad.ui.viewport import Viewport2D


@dataclass
class RenderCommand:

    operation: str

    data: dict[str, Any] = field(
        default_factory=dict
    )


class Renderer2D:

    def __init__(
        self,
        viewport: Viewport2D,
    ):

        self.viewport = viewport

    def render_entity(
        self,
        entity: Entity,
    ):

        if not entity.visible:
            return None

        if isinstance(
            entity,
            LineEntity,
        ):

            start = (
                self.viewport.world_to_screen(
                    entity.start
                )
            )

            end = (
                self.viewport.world_to_screen(
                    entity.end
                )
            )

            return RenderCommand(
                operation="line",
                data={
                    "entity_id": entity.entity_id,
                    "start": start,
                    "end": end,
                    "selected": entity.selected,
                    "layer": entity.layer,
                },
            )

        if isinstance(
            entity,
            CircleEntity,
        ):

            center = (
                self.viewport.world_to_screen(
                    entity.center
                )
            )

            radius = (
                entity.radius
                * self.viewport.zoom
            )

            return RenderCommand(
                operation="circle",
                data={
                    "entity_id": entity.entity_id,
                    "center": center,
                    "radius": radius,
                    "selected": entity.selected,
                    "layer": entity.layer,
                },
            )

        return RenderCommand(
            operation="entity",
            data={
                "entity_id": entity.entity_id,
                "entity_type": entity.entity_type,
                "selected": entity.selected,
                "layer": entity.layer,
            },
        )

    def render_entities(
        self,
        entities,
    ):

        commands = []

        for entity in entities:

            command = self.render_entity(
                entity
            )

            if command is not None:
                commands.append(command)

        return commands

    def render_registry(
        self,
        registry,
    ):

        return self.render_entities(
            registry.visible()
        )

    def render_grid(
        self,
        spacing: float = 10.0,
        extent: float = 1000.0,
    ):

        if spacing <= 0:
            raise ValueError(
                "Grid spacing must be positive."
            )

        commands = []

        value = -extent

        while value <= extent:

            vertical_start = (
                self.viewport.world_to_screen(
                    Point2(
                        value,
                        -extent,
                    )
                )
            )

            vertical_end = (
                self.viewport.world_to_screen(
                    Point2(
                        value,
                        extent,
                    )
                )
            )

            commands.append(
                RenderCommand(
                    operation="grid_line",
                    data={
                        "start": vertical_start,
                        "end": vertical_end,
                    },
                )
            )

            horizontal_start = (
                self.viewport.world_to_screen(
                    Point2(
                        -extent,
                        value,
                    )
                )
            )

            horizontal_end = (
                self.viewport.world_to_screen(
                    Point2(
                        extent,
                        value,
                    )
                )
            )

            commands.append(
                RenderCommand(
                    operation="grid_line",
                    data={
                        "start": horizontal_start,
                        "end": horizontal_end,
                    },
                )
            )

            value += spacing

        return commands
'@

# Fix missing Point2 import in renderer
$RendererPath = Join-Path $Root "sovereign_cad\rendering\renderer.py"

$RendererText = Get-Content `
    -LiteralPath $RendererPath `
    -Raw

$RendererText = $RendererText.Replace(
    "from sovereign_cad.core.entities import (",
    "from sovereign_cad.core.geometry import Point2`r`n`r`nfrom sovereign_cad.core.entities import ("
)

[System.IO.File]::WriteAllText(
    $RendererPath,
    $RendererText,
    [System.Text.UTF8Encoding]::new($false)
)

# ============================================================
# 8. CANVAS
# ============================================================

Write-Host "[8/10] Building canvas state..." -ForegroundColor Yellow

Write-ProjectFile `
    "sovereign_cad\ui\canvas\state.py" `
    @'
from __future__ import annotations

from dataclasses import dataclass, field

from sovereign_cad.core.geometry import (
    Point2,
    Vector2,
)

from sovereign_cad.core.entities import (
    EntityRegistry,
)

from sovereign_cad.ui.viewport import (
    Viewport2D,
)


@dataclass
class CanvasState:

    viewport: Viewport2D = field(
        default_factory=Viewport2D
    )

    registry: EntityRegistry | None = None

    cursor_screen: Point2 = field(
        default_factory=lambda: Point2(
            0.0,
            0.0,
        )
    )

    cursor_world: Point2 = field(
        default_factory=lambda: Point2(
            0.0,
            0.0,
        )
    )

    is_panning: bool = False

    last_pan_screen: Point2 | None = None

    def update_cursor(
        self,
        screen_point: Point2,
    ) -> Point2:

        self.cursor_screen = screen_point

        self.cursor_world = (
            self.viewport.screen_to_world(
                screen_point
            )
        )

        return self.cursor_world

    def begin_pan(
        self,
        screen_point: Point2,
    ) -> None:

        self.is_panning = True

        self.last_pan_screen = (
            screen_point
        )

    def update_pan(
        self,
        screen_point: Point2,
    ) -> None:

        if not self.is_panning:
            return

        if self.last_pan_screen is None:

            self.last_pan_screen = (
                screen_point
            )

            return

        delta = Vector2(
            screen_point.x
            - self.last_pan_screen.x,

            screen_point.y
            - self.last_pan_screen.y,
        )

        self.viewport.pan(delta)

        self.last_pan_screen = (
            screen_point
        )

        self.update_cursor(
            screen_point
        )

    def end_pan(self) -> None:

        self.is_panning = False
        self.last_pan_screen = None

    def zoom_in(
        self,
        factor: float = 1.2,
    ) -> None:

        self.viewport.zoom_by(
            factor
        )

        self.update_cursor(
            self.cursor_screen
        )

    def zoom_out(
        self,
        factor: float = 1.2,
    ) -> None:

        if factor <= 0:
            raise ValueError(
                "Zoom factor must be positive."
            )

        self.viewport.zoom_by(
            1.0 / factor
        )

        self.update_cursor(
            self.cursor_screen
        )

    def reset_view(self) -> None:

        self.viewport.reset()

        self.update_cursor(
            self.cursor_screen
        )
'@

# ============================================================
# 9. TESTS
# ============================================================

Write-Host "[9/10] Creating Stage 5 tests..." -ForegroundColor Yellow

Write-EmptyProjectFile `
    "sovereign_cad\tests\viewport\__init__.py"

Write-EmptyProjectFile `
    "sovereign_cad\tests\canvas\__init__.py"

Write-EmptyProjectFile `
    "sovereign_cad\tests\rendering\__init__.py"

Write-ProjectFile `
    "sovereign_cad\tests\viewport\test_viewport.py" `
    @'
from sovereign_cad.core.geometry import (
    Point2,
    Vector2,
)

from sovereign_cad.ui.viewport import (
    Viewport2D,
)


def test_world_screen_round_trip():

    viewport = Viewport2D(
        width=1000,
        height=800,
        zoom=2,
    )

    world = Point2(
        25,
        40,
    )

    screen = viewport.world_to_screen(
        world
    )

    result = viewport.screen_to_world(
        screen
    )

    assert result.almost_equal(
        world
    )


def test_origin_is_screen_center():

    viewport = Viewport2D(
        width=1000,
        height=800,
    )

    result = viewport.world_to_screen(
        Point2(0, 0)
    )

    assert result.almost_equal(
        Point2(500, 400)
    )


def test_zoom():

    viewport = Viewport2D()

    viewport.zoom_by(2)

    assert viewport.zoom == 2


def test_pan_world():

    viewport = Viewport2D()

    viewport.pan_world(
        Vector2(
            10,
            20,
        )
    )

    assert viewport.center.almost_equal(
        Point2(
            10,
            20,
        )
    )


def test_reset():

    viewport = Viewport2D(
        center=Point2(
            50,
            60,
        ),
        zoom=10,
    )

    viewport.reset()

    assert viewport.center.almost_equal(
        Point2(
            0,
            0,
        )
    )

    assert viewport.zoom == 1
'@

Write-ProjectFile `
    "sovereign_cad\tests\canvas\test_canvas_state.py" `
    @'
from sovereign_cad.core.geometry import (
    Point2,
)

from sovereign_cad.ui.canvas import (
    CanvasState,
)


def test_cursor_conversion():

    canvas = CanvasState()

    result = canvas.update_cursor(
        Point2(
            600,
            400,
        )
    )

    assert result.almost_equal(
        Point2(
            0,
            0,
        )
    )


def test_pan():

    canvas = CanvasState()

    canvas.begin_pan(
        Point2(
            100,
            100,
        )
    )

    canvas.update_pan(
        Point2(
            110,
            100,
        )
    )

    canvas.end_pan()

    assert canvas.viewport.center.x == -10


def test_zoom_in():

    canvas = CanvasState()

    canvas.zoom_in()

    assert canvas.viewport.zoom > 1


def test_zoom_out():

    canvas = CanvasState()

    canvas.zoom_out()

    assert canvas.viewport.zoom < 1


def test_reset():

    canvas = CanvasState()

    canvas.viewport.pan_world(
        type(canvas.viewport.center)(
            50,
            50,
        )
    )

    canvas.zoom_in()

    canvas.reset_view()

    assert canvas.viewport.center.almost_equal(
        Point2(
            0,
            0,
        )
    )

    assert canvas.viewport.zoom == 1
'@

Write-ProjectFile `
    "sovereign_cad\tests\rendering\test_renderer.py" `
    @'
from sovereign_cad.core.entities import (
    CircleEntity,
    EntityRegistry,
    LineEntity,
)

from sovereign_cad.core.geometry import (
    Point2,
)

from sovereign_cad.rendering import (
    Renderer2D,
)

from sovereign_cad.ui.viewport import (
    Viewport2D,
)


def test_line_render():

    renderer = Renderer2D(
        Viewport2D(
            width=1000,
            height=800,
        )
    )

    line = LineEntity(
        start=Point2(
            0,
            0,
        ),
        end=Point2(
            10,
            0,
        ),
    )

    command = renderer.render_entity(
        line
    )

    assert command is not None
    assert command.operation == "line"

    assert command.data["start"].almost_equal(
        Point2(
            500,
            400,
        )
    )


def test_circle_render():

    renderer = Renderer2D(
        Viewport2D(
            zoom=2
        )
    )

    circle = CircleEntity(
        center=Point2(
            10,
            10,
        ),
        radius=5,
    )

    command = renderer.render_entity(
        circle
    )

    assert command is not None
    assert command.operation == "circle"
    assert command.data["radius"] == 10


def test_hidden_entity():

    renderer = Renderer2D(
        Viewport2D()
    )

    line = LineEntity(
        start=Point2(
            0,
            0,
        ),
        end=Point2(
            10,
            0,
        ),
    )

    line.visible = False

    assert renderer.render_entity(
        line
    ) is None


def test_registry_render():

    registry = EntityRegistry()

    registry.add(
        LineEntity(
            start=Point2(
                0,
                0,
            ),
            end=Point2(
                10,
                0,
            ),
        )
    )

    registry.add(
        CircleEntity(
            center=Point2(
                20,
                20,
            ),
            radius=5,
        )
    )

    renderer = Renderer2D(
        Viewport2D()
    )

    commands = renderer.render_registry(
        registry
    )

    assert len(commands) == 2


def test_selected_state():

    line = LineEntity(
        start=Point2(
            0,
            0,
        ),
        end=Point2(
            10,
            0,
        ),
    )

    line.selected = True

    command = Renderer2D(
        Viewport2D()
    ).render_entity(
        line
    )

    assert command.data["selected"] is True
'@

# ============================================================
# VALIDATION
# ============================================================

Write-Host "[10/10] Validating Stage 5..." -ForegroundColor Yellow

Get-ChildItem `
    (Join-Path $Root "sovereign_cad") `
    -Recurse `
    -Directory `
    -Filter "__pycache__" `
    -ErrorAction SilentlyContinue |
    Remove-Item `
        -Recurse `
        -Force `
        -ErrorAction SilentlyContinue

Write-Host "CACHE: CLEAN" -ForegroundColor Green

# Stage 5 import validation
& $Python -c "import sovereign_cad; import sovereign_cad.core; import sovereign_cad.ui; import sovereign_cad.ui.viewport; import sovereign_cad.ui.canvas; import sovereign_cad.rendering; from sovereign_cad.ui.viewport import Viewport2D; from sovereign_cad.ui.canvas import CanvasState; from sovereign_cad.rendering import Renderer2D; print('PACKAGE: OK'); print('CORE: OK'); print('UI: OK'); print('VIEWPORT: OK'); print('CANVAS: OK'); print('RENDERING: OK'); print('STAGE 5 IMPORTS: OK')"

if ($LASTEXITCODE -ne 0) {
    throw "Stage 5 imports failed."
}

# Python compilation
& $Python -m compileall -q sovereign_cad

if ($LASTEXITCODE -ne 0) {
    throw "Python syntax validation failed."
}

Write-Host "PYTHON SYNTAX: OK" -ForegroundColor Green

# ============================================================
# FULL TEST SUITE
# ============================================================

Write-Host ""
Write-Host "Running complete SovereignCAD test suite..." -ForegroundColor Cyan
Write-Host ""

& $Python -m pytest `
    "$Root\sovereign_cad\tests" `
    -q

if ($LASTEXITCODE -ne 0) {

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Red
    Write-Host "              STAGE 5 TESTS FAILED" -ForegroundColor Red
    Write-Host "============================================================" -ForegroundColor Red
    Write-Host ""

    throw "SovereignCAD Stage 5 tests failed."
}

# ============================================================
# SMOKE TEST
# ============================================================

Write-Host ""
Write-Host "Running final Stage 5 smoke test..." -ForegroundColor Yellow

$SmokeCode = @"
from sovereign_cad.core.geometry import Point2
from sovereign_cad.ui.viewport import Viewport, Viewport2D
from sovereign_cad.ui.canvas import CanvasState
from sovereign_cad.rendering import Renderer2D, RenderCommand

print("Checking Viewport...")

viewport = Viewport()

assert viewport.width > 0
assert viewport.height > 0
assert viewport.zoom > 0

print("VIEWPORT: ONLINE")

print("Checking world/screen conversion...")

world = Point2(0.0, 0.0)
screen = viewport.world_to_screen(world)
roundtrip = viewport.screen_to_world(screen)

assert abs(roundtrip.x - world.x) < 1e-9
assert abs(roundtrip.y - world.y) < 1e-9

print("COORDINATE CONVERSION: OK")

print("Checking CanvasState...")

canvas = CanvasState()

assert canvas.viewport is not None

canvas.update_cursor(
    viewport.screen_center()
)

assert canvas.cursor_world is not None

print("CANVAS: ONLINE")

print("Checking Renderer2D...")

renderer = Renderer2D(viewport)

assert renderer is not None

print("RENDERER: ONLINE")

print("Checking RenderCommand...")

command = RenderCommand(
    operation="smoke_test"
)

assert command.operation == "smoke_test"
assert isinstance(command.data, dict)

print("RENDER COMMANDS: ONLINE")

print("SMOKE TEST: OK")
"@

& $Python -c $SmokeCode

if ($LASTEXITCODE -ne 0) {

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Red
    Write-Host "              STAGE 5 SMOKE TEST FAILED" -ForegroundColor Red
    Write-Host "============================================================" -ForegroundColor Red
    Write-Host ""

    throw "Stage 5 smoke test failed."
}

# ============================================================
# SUCCESS
# ============================================================

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "             SOVEREIGNCAD STAGE 5: SUCCESS" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""

Write-Host "Geometry Kernel       : ONLINE" -ForegroundColor Green
Write-Host "Entity Engine         : ONLINE" -ForegroundColor Green
Write-Host "Document Engine       : ONLINE" -ForegroundColor Green
Write-Host "Command Engine        : ONLINE" -ForegroundColor Green
Write-Host "Undo / Redo           : ONLINE" -ForegroundColor Green
Write-Host "Transform Engine      : ONLINE" -ForegroundColor Green
Write-Host "Spatial Index         : ONLINE" -ForegroundColor Green
Write-Host "Selection Engine      : ONLINE" -ForegroundColor Green
Write-Host "Viewport Engine       : ONLINE" -ForegroundColor Green
Write-Host "Canvas State          : ONLINE" -ForegroundColor Green
Write-Host "Renderer              : ONLINE" -ForegroundColor Green
Write-Host "Tests                 : PASSED" -ForegroundColor Green

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "NEXT STAGE:" -ForegroundColor Cyan
Write-Host "Interactive CAD UI + Drawing Tools + Command Workflow" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
