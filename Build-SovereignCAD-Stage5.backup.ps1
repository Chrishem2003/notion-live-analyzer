[CmdletBinding()]
param(
    [switch]$RunTests
)

$ErrorActionPreference = "Stop"

# ============================================================
# SOVEREIGNCAD BUILD SYSTEM
# STAGE 5 - VIEWPORT + RENDERING + CANVAS
# ============================================================

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "             SOVEREIGNCAD BUILD SYSTEM" -ForegroundColor Cyan
Write-Host "             STAGE 5 - VIEWPORT + RENDERING" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# ============================================================
# 1. PROJECT ROOT
# ============================================================

Write-Host "[1/10] Verifying project..." -ForegroundColor Yellow

$Root = (Get-Location).Path

if (-not (Test-Path -LiteralPath (Join-Path $Root "sovereign_cad"))) {
    throw "sovereign_cad directory not found. Run this script from D:\notion-live-analyzer"
}

Write-Host "PROJECT ROOT: OK" -ForegroundColor Green
Write-Host "Project: $Root" -ForegroundColor Gray

# ============================================================
# 2. PYTHON
# ============================================================

Write-Host "[2/10] Selecting Python..." -ForegroundColor Yellow

$PythonPath = Join-Path $Root ".venv\Scripts\python.exe"

if (Test-Path -LiteralPath $PythonPath) {
    $Python = $PythonPath
}
else {
    $PythonCommand = Get-Command python -ErrorAction SilentlyContinue

    if (-not $PythonCommand) {
        throw "Python was not found. Activate the .venv first."
    }

    $Python = $PythonCommand.Source
}

$PythonVersion = & $Python --version 2>&1

Write-Host "Python: $Python" -ForegroundColor Green
Write-Host "Version: $PythonVersion" -ForegroundColor Green

# ============================================================
# 3. PYTHON IMPORT PATH
# ============================================================

Write-Host "[3/10] Configuring Python import path..." -ForegroundColor Yellow

$env:PYTHONPATH = $Root
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"

Write-Host "PYTHONPATH: $env:PYTHONPATH" -ForegroundColor Green

# ------------------------------------------------------------
# Use a real Python validation file instead of python -c.
# This avoids PowerShell quote escaping completely.
# ------------------------------------------------------------

$ValidationFile = Join-Path $Root "_stage5_import_validation.py"

@'
import sys
from pathlib import Path

root = Path.cwd().resolve()

if str(root) not in sys.path:
    sys.path.insert(0, str(root))

import sovereign_cad
import sovereign_cad.core

from sovereign_cad.core.geometry import Point2, Vector2, BoundingBox2
from sovereign_cad.core.entities import (
    Entity,
    LineEntity,
    CircleEntity,
    EntityRegistry,
)
from sovereign_cad.core.transforms import Transform2D
from sovereign_cad.core.spatial import SpatialIndex
from sovereign_cad.core.selection import SelectionEngine

print("SOVEREIGNCAD IMPORT: OK")
print("CORE IMPORT: OK")
print("GEOMETRY IMPORT: OK")
print("ENTITY IMPORT: OK")
print("TRANSFORM IMPORT: OK")
print("SPATIAL IMPORT: OK")
print("SELECTION IMPORT: OK")
'@ | Set-Content -LiteralPath $ValidationFile -Encoding UTF8

& $Python $ValidationFile

if ($LASTEXITCODE -ne 0) {
    Remove-Item -LiteralPath $ValidationFile -Force -ErrorAction SilentlyContinue
    throw "SovereignCAD import path validation failed."
}

Remove-Item -LiteralPath $ValidationFile -Force -ErrorAction SilentlyContinue

# ============================================================
# 4. CREATE STAGE 5 DIRECTORIES
# ============================================================

Write-Host "[4/10] Creating Stage 5 architecture..." -ForegroundColor Yellow

$Directories = @(
    "sovereign_cad\core\viewport",
    "sovereign_cad\core\rendering",
    "sovereign_cad\ui",
    "sovereign_cad\ui\canvas",
    "sovereign_cad\tests\viewport",
    "sovereign_cad\tests\rendering",
    "sovereign_cad\tests\canvas"
)

foreach ($Directory in $Directories) {

    $DirectoryPath = Join-Path $Root $Directory

    New-Item `
        -ItemType Directory `
        -Path $DirectoryPath `
        -Force |
        Out-Null
}

Write-Host "STAGE 5 DIRECTORIES: OK" -ForegroundColor Green

# ============================================================
# HELPER
# ============================================================

function Write-ProjectFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RelativePath,

        [Parameter(Mandatory = $true)]
        [string]$Content
    )

    $FullPath = Join-Path $Root $RelativePath
    $Parent = Split-Path -Parent $FullPath

    New-Item `
        -ItemType Directory `
        -Path $Parent `
        -Force |
        Out-Null

    Set-Content `
        -LiteralPath $FullPath `
        -Value $Content `
        -Encoding UTF8

    Write-Host "CREATE: $RelativePath" -ForegroundColor Green
}

# ============================================================
# 5. VIEWPORT ENGINE
# ============================================================

Write-Host "[5/10] Building viewport engine..." -ForegroundColor Yellow

Write-ProjectFile `
    "sovereign_cad\core\viewport\viewport.py" `
@'
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from ..geometry import Point2
from ..transforms import Transform2D


@dataclass(frozen=True, slots=True)
class ViewportState:
    """
    Camera state for the CAD viewport.

    world -> screen:

        screen = translation + scale * world

    The Y axis is configurable so UI systems can use either
    mathematical or screen coordinates.
    """

    center: Point2 = Point2(0.0, 0.0)
    zoom: float = 1.0
    screen_width: float = 1280.0
    screen_height: float = 720.0
    y_down: bool = True

    def __post_init__(self) -> None:
        if not isfinite(self.zoom) or self.zoom <= 0:
            raise ValueError("Viewport zoom must be greater than zero.")

        if self.screen_width <= 0:
            raise ValueError("Viewport width must be greater than zero.")

        if self.screen_height <= 0:
            raise ValueError("Viewport height must be greater than zero.")


class Viewport:

    def __init__(
        self,
        width: float = 1280.0,
        height: float = 720.0,
    ) -> None:

        self._state = ViewportState(
            screen_width=float(width),
            screen_height=float(height),
        )

    @property
    def state(self) -> ViewportState:
        return self._state

    @property
    def center(self) -> Point2:
        return self._state.center

    @property
    def zoom(self) -> float:
        return self._state.zoom

    @property
    def width(self) -> float:
        return self._state.screen_width

    @property
    def height(self) -> float:
        return self._state.screen_height

    def resize(
        self,
        width: float,
        height: float,
    ) -> None:

        if width <= 0 or height <= 0:
            raise ValueError(
                "Viewport dimensions must be greater than zero."
            )

        self._state = ViewportState(
            center=self.center,
            zoom=self.zoom,
            screen_width=float(width),
            screen_height=float(height),
            y_down=self._state.y_down,
        )

    def set_center(
        self,
        point: Point2,
    ) -> None:

        self._state = ViewportState(
            center=point,
            zoom=self.zoom,
            screen_width=self.width,
            screen_height=self.height,
            y_down=self._state.y_down,
        )

    def set_zoom(
        self,
        zoom: float,
    ) -> None:

        if not isfinite(zoom) or zoom <= 0:
            raise ValueError(
                "Viewport zoom must be greater than zero."
            )

        self._state = ViewportState(
            center=self.center,
            zoom=float(zoom),
            screen_width=self.width,
            screen_height=self.height,
            y_down=self._state.y_down,
        )

    def zoom_by(
        self,
        factor: float,
    ) -> None:

        if not isfinite(factor) or factor <= 0:
            raise ValueError(
                "Zoom factor must be greater than zero."
            )

        self.set_zoom(self.zoom * factor)

    def pan(
        self,
        dx: float,
        dy: float,
    ) -> None:

        self.set_center(
            Point2(
                self.center.x + dx,
                self.center.y + dy,
            )
        )

    def world_to_screen(
        self,
        point: Point2,
    ) -> Point2:

        x = (
            (point.x - self.center.x)
            * self.zoom
            + self.width / 2.0
        )

        if self._state.y_down:
            y = (
                self.height / 2.0
                - (point.y - self.center.y) * self.zoom
            )
        else:
            y = (
                (point.y - self.center.y)
                * self.zoom
                + self.height / 2.0
            )

        return Point2(x, y)

    def screen_to_world(
        self,
        point: Point2,
    ) -> Point2:

        x = (
            (point.x - self.width / 2.0)
            / self.zoom
            + self.center.x
        )

        if self._state.y_down:
            y = (
                self.center.y
                - (point.y - self.height / 2.0)
                / self.zoom
            )
        else:
            y = (
                (point.y - self.height / 2.0)
                / self.zoom
                + self.center.y
            )

        return Point2(x, y)

    def world_transform(self) -> Transform2D:

        if self._state.y_down:
            return Transform2D(
                a=self.zoom,
                d=-self.zoom,
                tx=self.width / 2.0 - self.center.x * self.zoom,
                ty=self.height / 2.0 + self.center.y * self.zoom,
            )

        return Transform2D(
            a=self.zoom,
            d=self.zoom,
            tx=self.width / 2.0 - self.center.x * self.zoom,
            ty=self.height / 2.0 - self.center.y * self.zoom,
        )

    def reset(self) -> None:

        self._state = ViewportState(
            screen_width=self.width,
            screen_height=self.height,
            y_down=self._state.y_down,
        )
'@

Write-ProjectFile `
    "sovereign_cad\core\viewport\__init__.py" `
@'
from .viewport import Viewport, ViewportState

__all__ = [
    "Viewport",
    "ViewportState",
]
'@

# ============================================================
# 6. RENDERING ENGINE
# ============================================================

Write-Host "[6/10] Building rendering engine..." -ForegroundColor Yellow

Write-ProjectFile `
    "sovereign_cad\core\rendering\renderer.py" `
@'
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..entities import CircleEntity, Entity, LineEntity
from ..geometry import Point2
from ..viewport import Viewport


@dataclass(frozen=True, slots=True)
class RenderCommand:
    """
    Backend-independent drawing command.

    Stage 5 deliberately does not require a GUI toolkit.
    The renderer produces deterministic commands that can
    later be consumed by Qt, Tk, OpenGL, Vulkan, or another
    frontend.
    """

    operation: str
    points: tuple[Point2, ...]
    properties: dict[str, Any]


class Renderer:

    def __init__(
        self,
        viewport: Viewport,
    ) -> None:

        self.viewport = viewport

    def render_entity(
        self,
        entity: Entity,
    ) -> list[RenderCommand]:

        if not entity.visible:
            return []

        if isinstance(entity, LineEntity):
            return self._render_line(entity)

        if isinstance(entity, CircleEntity):
            return self._render_circle(entity)

        return []

    def render_entities(
        self,
        entities,
    ) -> list[RenderCommand]:

        commands: list[RenderCommand] = []

        for entity in entities:
            commands.extend(
                self.render_entity(entity)
            )

        return commands

    def _render_line(
        self,
        entity: LineEntity,
    ) -> list[RenderCommand]:

        start = self.viewport.world_to_screen(
            entity.start
        )

        end = self.viewport.world_to_screen(
            entity.end
        )

        return [
            RenderCommand(
                operation="line",
                points=(start, end),
                properties={
                    "entity_id": entity.entity_id,
                    "selected": entity.selected,
                    "layer": entity.layer,
                },
            )
        ]

    def _render_circle(
        self,
        entity: CircleEntity,
    ) -> list[RenderCommand]:

        center = self.viewport.world_to_screen(
            entity.center
        )

        edge = self.viewport.world_to_screen(
            Point2(
                entity.center.x + entity.radius,
                entity.center.y,
            )
        )

        radius = abs(edge.x - center.x)

        return [
            RenderCommand(
                operation="circle",
                points=(center,),
                properties={
                    "radius": radius,
                    "entity_id": entity.entity_id,
                    "selected": entity.selected,
                    "layer": entity.layer,
                },
            )
        ]

    def render_grid(
        self,
        spacing: float = 10.0,
        extent: float = 1000.0,
    ) -> list[RenderCommand]:

        if spacing <= 0:
            raise ValueError(
                "Grid spacing must be greater than zero."
            )

        commands: list[RenderCommand] = []

        x = -extent

        while x <= extent:
            commands.append(
                RenderCommand(
                    operation="grid_line",
                    points=(
                        self.viewport.world_to_screen(
                            Point2(x, -extent)
                        ),
                        self.viewport.world_to_screen(
                            Point2(x, extent)
                        ),
                    ),
                    properties={
                        "grid": True,
                    },
                )
            )

            x += spacing

        y = -extent

        while y <= extent:
            commands.append(
                RenderCommand(
                    operation="grid_line",
                    points=(
                        self.viewport.world_to_screen(
                            Point2(-extent, y)
                        ),
                        self.viewport.world_to_screen(
                            Point2(extent, y)
                        ),
                    ),
                    properties={
                        "grid": True,
                    },
                )
            )

            y += spacing

        return commands
'@

Write-ProjectFile `
    "sovereign_cad\core\rendering\__init__.py" `
@'
from .renderer import RenderCommand, Renderer

__all__ = [
    "RenderCommand",
    "Renderer",
]
'@

# ============================================================
# 7. CANVAS STATE
# ============================================================

Write-Host "[7/10] Building interactive canvas state..." -ForegroundColor Yellow

Write-ProjectFile `
    "sovereign_cad\ui\canvas\state.py" `
@'
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from sovereign_cad.core.geometry import Point2
from sovereign_cad.core.viewport import Viewport


class CanvasMode(str, Enum):
    SELECT = "select"
    PAN = "pan"
    DRAW = "draw"


@dataclass(slots=True)
class CanvasState:
    mode: CanvasMode = CanvasMode.SELECT
    mouse_position: Point2 = Point2(0.0, 0.0)
    world_position: Point2 = Point2(0.0, 0.0)
    dragging: bool = False
    grid_visible: bool = True


class CanvasController:

    def __init__(
        self,
        viewport: Viewport,
    ) -> None:

        self.viewport = viewport
        self.state = CanvasState()

    def set_mode(
        self,
        mode: CanvasMode | str,
    ) -> None:

        if isinstance(mode, str):
            mode = CanvasMode(mode)

        self.state.mode = mode

    def pointer_move(
        self,
        screen_point: Point2,
    ) -> Point2:

        self.state.mouse_position = screen_point

        world_point = self.viewport.screen_to_world(
            screen_point
        )

        self.state.world_position = world_point

        return world_point

    def pointer_down(
        self,
        screen_point: Point2,
    ) -> Point2:

        self.state.dragging = True

        return self.pointer_move(
            screen_point
        )

    def pointer_up(
        self,
        screen_point: Point2,
    ) -> Point2:

        self.state.dragging = False

        return self.pointer_move(
            screen_point
        )

    def pan(
        self,
        dx: float,
        dy: float,
    ) -> None:

        self.viewport.pan(
            dx,
            dy,
        )

    def zoom(
        self,
        factor: float,
    ) -> None:

        self.viewport.zoom_by(
            factor
        )

    def toggle_grid(self) -> bool:

        self.state.grid_visible = (
            not self.state.grid_visible
        )

        return self.state.grid_visible
'@

Write-ProjectFile `
    "sovereign_cad\ui\canvas\__init__.py" `
@'
from .state import CanvasController, CanvasMode, CanvasState

__all__ = [
    "CanvasController",
    "CanvasMode",
    "CanvasState",
]
'@

Write-ProjectFile `
    "sovereign_cad\ui\__init__.py" `
@'
from .canvas import CanvasController, CanvasMode, CanvasState

__all__ = [
    "CanvasController",
    "CanvasMode",
    "CanvasState",
]
'@

# ============================================================
# CORE EXPORTS
# ============================================================

Write-Host "Updating core package exports..." -ForegroundColor Yellow

Write-ProjectFile `
    "sovereign_cad\core\__init__.py" `
@'
from .geometry import *
from .entities import *
from .transforms import *
from .spatial import *
from .selection import *
from .viewport import *
from .rendering import *

__all__ = []
'@

# ============================================================
# STAGE 5 VIEWPORT TESTS
# ============================================================

Write-Host "Creating viewport tests..." -ForegroundColor Yellow

Write-ProjectFile `
    "sovereign_cad\tests\viewport\test_viewport.py" `
@'
from sovereign_cad.core.geometry import Point2
from sovereign_cad.core.viewport import Viewport


def test_viewport_defaults():

    viewport = Viewport()

    assert viewport.width == 1280
    assert viewport.height == 720
    assert viewport.zoom == 1.0


def test_world_to_screen_origin():

    viewport = Viewport(
        width=1000,
        height=600,
    )

    result = viewport.world_to_screen(
        Point2(0, 0)
    )

    assert result.almost_equal(
        Point2(500, 300)
    )


def test_world_screen_roundtrip():

    viewport = Viewport(
        width=1000,
        height=600,
    )

    original = Point2(
        25,
        40,
    )

    screen = viewport.world_to_screen(
        original
    )

    result = viewport.screen_to_world(
        screen
    )

    assert result.almost_equal(
        original
    )


def test_zoom():

    viewport = Viewport()

    viewport.set_zoom(2.0)

    assert viewport.zoom == 2.0


def test_pan():

    viewport = Viewport()

    viewport.pan(
        10,
        20,
    )

    assert viewport.center.almost_equal(
        Point2(10, 20)
    )


def test_resize():

    viewport = Viewport()

    viewport.resize(
        1920,
        1080,
    )

    assert viewport.width == 1920
    assert viewport.height == 1080
'@

# ============================================================
# RENDERER TESTS
# ============================================================

Write-Host "Creating renderer tests..." -ForegroundColor Yellow

Write-ProjectFile `
    "sovereign_cad\tests\rendering\test_renderer.py" `
@'
from sovereign_cad.core.entities import (
    CircleEntity,
    LineEntity,
)
from sovereign_cad.core.geometry import Point2
from sovereign_cad.core.rendering import Renderer
from sovereign_cad.core.viewport import Viewport


def test_render_line():

    viewport = Viewport(
        width=1000,
        height=600,
    )

    renderer = Renderer(
        viewport
    )

    line = LineEntity(
        start=Point2(0, 0),
        end=Point2(10, 0),
    )

    commands = renderer.render_entity(
        line
    )

    assert len(commands) == 1
    assert commands[0].operation == "line"
    assert len(commands[0].points) == 2


def test_render_circle():

    viewport = Viewport()

    renderer = Renderer(
        viewport
    )

    circle = CircleEntity(
        center=Point2(10, 20),
        radius=5,
    )

    commands = renderer.render_entity(
        circle
    )

    assert len(commands) == 1
    assert commands[0].operation == "circle"
    assert commands[0].properties["radius"] == 5


def test_hidden_entity_not_rendered():

    viewport = Viewport()

    renderer = Renderer(
        viewport
    )

    line = LineEntity(
        start=Point2(0, 0),
        end=Point2(10, 0),
        visible=False,
    )

    commands = renderer.render_entity(
        line
    )

    assert commands == []


def test_render_entities():

    viewport = Viewport()

    renderer = Renderer(
        viewport
    )

    line = LineEntity(
        start=Point2(0, 0),
        end=Point2(10, 0),
    )

    circle = CircleEntity(
        center=Point2(20, 20),
        radius=5,
    )

    commands = renderer.render_entities(
        [line, circle]
    )

    assert len(commands) == 2


def test_grid():

    viewport = Viewport()

    renderer = Renderer(
        viewport
    )

    commands = renderer.render_grid(
        spacing=10,
        extent=20,
    )

    assert len(commands) > 0

    assert all(
        command.operation == "grid_line"
        for command in commands
    )
'@

# ============================================================
# CANVAS TESTS
# ============================================================

Write-Host "Creating canvas tests..." -ForegroundColor Yellow

Write-ProjectFile `
    "sovereign_cad\tests\canvas\test_canvas_state.py" `
@'
from sovereign_cad.core.geometry import Point2
from sovereign_cad.core.viewport import Viewport
from sovereign_cad.ui.canvas import (
    CanvasController,
    CanvasMode,
)


def test_canvas_defaults():

    viewport = Viewport()

    canvas = CanvasController(
        viewport
    )

    assert canvas.state.mode == CanvasMode.SELECT
    assert canvas.state.dragging is False
    assert canvas.state.grid_visible is True


def test_canvas_mode():

    viewport = Viewport()

    canvas = CanvasController(
        viewport
    )

    canvas.set_mode(
        CanvasMode.PAN
    )

    assert canvas.state.mode == CanvasMode.PAN


def test_canvas_pointer_conversion():

    viewport = Viewport(
        width=1000,
        height=600,
    )

    canvas = CanvasController(
        viewport
    )

    world = canvas.pointer_move(
        Point2(500, 300)
    )

    assert world.almost_equal(
        Point2(0, 0)
    )

    assert canvas.state.world_position.almost_equal(
        Point2(0, 0)
    )


def test_pointer_drag_state():

    viewport = Viewport()

    canvas = CanvasController(
        viewport
    )

    canvas.pointer_down(
        Point2(100, 100)
    )

    assert canvas.state.dragging is True

    canvas.pointer_up(
        Point2(120, 120)
    )

    assert canvas.state.dragging is False


def test_canvas_zoom():

    viewport = Viewport()

    canvas = CanvasController(
        viewport
    )

    canvas.zoom(2)

    assert viewport.zoom == 2


def test_canvas_pan():

    viewport = Viewport()

    canvas = CanvasController(
        viewport
    )

    canvas.pan(
        10,
        20,
    )

    assert viewport.center.almost_equal(
        Point2(10, 20)
    )


def test_grid_toggle():

    viewport = Viewport()

    canvas = CanvasController(
        viewport
    )

    assert canvas.toggle_grid() is False
    assert canvas.toggle_grid() is True
'@

# ============================================================
# 8. PACKAGE VALIDATION
# ============================================================

Write-Host "[8/10] Validating Stage 5 package..." -ForegroundColor Yellow

$Stage5Validation = Join-Path `
    $Root `
    "_stage5_validation.py"

@'
import sys
from pathlib import Path

root = Path.cwd().resolve()

if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from sovereign_cad.core.viewport import Viewport, ViewportState
from sovereign_cad.core.rendering import Renderer, RenderCommand
from sovereign_cad.ui.canvas import (
    CanvasController,
    CanvasMode,
    CanvasState,
)

viewport = Viewport()

assert viewport.width == 1280
assert viewport.height == 720

renderer = Renderer(viewport)

canvas = CanvasController(viewport)

assert canvas.state.mode == CanvasMode.SELECT

print("VIEWPORT PACKAGE: OK")
print("RENDERING PACKAGE: OK")
print("CANVAS PACKAGE: OK")
print("STAGE 5 VALIDATION: OK")
'@ | Set-Content `
    -LiteralPath $Stage5Validation `
    -Encoding UTF8

& $Python $Stage5Validation

$ValidationExitCode = $LASTEXITCODE

Remove-Item `
    -LiteralPath $Stage5Validation `
    -Force `
    -ErrorAction SilentlyContinue

if ($ValidationExitCode -ne 0) {
    throw "Stage 5 package validation failed."
}

# ============================================================
# 9. PYTHON COMPILE
# ============================================================

Write-Host "[9/10] Running Python syntax verification..." -ForegroundColor Yellow

& $Python -m compileall -q sovereign_cad

if ($LASTEXITCODE -ne 0) {
    throw "Python syntax verification failed."
}

Write-Host "PYTHON SYNTAX: OK" -ForegroundColor Green

# ============================================================
# CLEAN PYTHON CACHE
# ============================================================

Write-Host "Cleaning Python caches..." -ForegroundColor Yellow

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

# ============================================================
# 10. COMPLETE TEST SUITE
# ============================================================

Write-Host "[10/10] Running complete SovereignCAD test suite..." -ForegroundColor Yellow
Write-Host ""

$TestPath = Join-Path `
    $Root `
    "sovereign_cad\tests"

& $Python -m pytest `
    --rootdir="$Root" `
    "$TestPath" `
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
# FINAL SMOKE TEST
# ============================================================

Write-Host ""
Write-Host "Running final Stage 5 smoke test..." -ForegroundColor Yellow

$SmokeTest = Join-Path `
    $Root `
    "_stage5_smoke.py"

@'
import sys
from pathlib import Path

root = Path.cwd().resolve()

if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from sovereign_cad.core.geometry import Point2
from sovereign_cad.core.entities import (
    EntityRegistry,
    LineEntity,
    CircleEntity,
)
from sovereign_cad.core.viewport import Viewport
from sovereign_cad.core.rendering import Renderer
from sovereign_cad.ui.canvas import CanvasController

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

viewport = Viewport(
    width=1000,
    height=600,
)

renderer = Renderer(
    viewport
)

commands = renderer.render_entities(
    registry.all()
)

assert len(commands) == 2

screen = viewport.world_to_screen(
    Point2(0, 0)
)

world = viewport.screen_to_world(
    screen
)

assert world.almost_equal(
    Point2(0, 0)
)

canvas = CanvasController(
    viewport
)

canvas.pointer_move(
    screen
)

assert canvas.state.world_position.almost_equal(
    Point2(0, 0)
)

print("ENTITY ENGINE: OK")
print("VIEWPORT ENGINE: OK")
print("WORLD/SCREEN CONVERSION: OK")
print("RENDERER: OK")
print("CANVAS STATE: OK")
print("STAGE 5 SMOKE TEST: OK")
'@ | Set-Content `
    -LiteralPath $SmokeTest `
    -Encoding UTF8

& $Python $SmokeTest

$SmokeExitCode = $LASTEXITCODE

Remove-Item `
    -LiteralPath $SmokeTest `
    -Force `
    -ErrorAction SilentlyContinue

if ($SmokeExitCode -ne 0) {
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
Write-Host "Rendering Engine      : ONLINE" -ForegroundColor Green
Write-Host "Canvas State          : ONLINE" -ForegroundColor Green
Write-Host "World/Screen Mapping  : ONLINE" -ForegroundColor Green
Write-Host "Python Syntax         : PASSED" -ForegroundColor Green
Write-Host "Complete Test Suite   : PASSED" -ForegroundColor Green
Write-Host "Smoke Test            : PASSED" -ForegroundColor Green

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "NEXT STAGE:" -ForegroundColor Cyan
Write-Host "Interactive CAD Frontend + Drawing Tools + Mouse Input" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""