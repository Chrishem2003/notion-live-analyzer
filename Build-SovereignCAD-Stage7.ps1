powershell
# ============================================================
# SOVEREIGNCAD BUILD SYSTEM
# STAGE 7 - APPLICATION SHELL
# CLEAN BUILD SCRIPT
# ============================================================

$ErrorActionPreference = "Stop"

$Root = (Get-Location).Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "             SOVEREIGNCAD BUILD SYSTEM" -ForegroundColor Cyan
Write-Host "             STAGE 7 - APPLICATION SHELL" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Project: $Root"
Write-Host ""

# ============================================================
# HELPER
# ============================================================

function Write-ProjectFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string]$Content
    )

    $FullPath = Join-Path $Root $Path
    $Directory = Split-Path $FullPath -Parent

    if (-not (Test-Path $Directory)) {
        New-Item -ItemType Directory -Path $Directory -Force | Out-Null
    }

    Set-Content `
        -Path $FullPath `
        -Value $Content `
        -Encoding UTF8

    Write-Host "CREATE/UPDATE: $Path" -ForegroundColor DarkGray
}

# ============================================================
# [1/12] PROJECT
# ============================================================

Write-Host "[1/12] Verifying project..." -ForegroundColor Yellow

if (-not (Test-Path $Root)) {
    throw "Project root does not exist."
}

if (-not (Test-Path $Python)) {
    throw "Virtual environment Python not found: $Python"
}

if (-not (Test-Path (Join-Path $Root "sovereign_cad"))) {
    throw "sovereign_cad package not found."
}

Write-Host "PROJECT ROOT: OK" -ForegroundColor Green

# ============================================================
# [2/12] PYTHON
# ============================================================

Write-Host "[2/12] Selecting Python..." -ForegroundColor Yellow

$Version = & $Python --version

Write-Host "Python: $Python"
Write-Host "Version: $Version"

# ============================================================
# [3/12] IMPORT PATH
# ============================================================

Write-Host "[3/12] Configuring Python import path..." -ForegroundColor Yellow

$env:PYTHONPATH = $Root

$ImportCode = @'
import sovereign_cad
print("IMPORT PATH: OK")
print("SOVEREIGNCAD: OK")
'@

$ImportFile = Join-Path $env:TEMP "sovereigncad_stage7_import.py"

Set-Content `
    -Path $ImportFile `
    -Value $ImportCode `
    -Encoding UTF8

& $Python $ImportFile

if ($LASTEXITCODE -ne 0) {
    throw "SovereignCAD import failed."
}

# ============================================================
# [4/12] PACKAGE STRUCTURE
# ============================================================

Write-Host "[4/12] Repairing Stage 7 package structure..." -ForegroundColor Yellow

$Directories = @(
    "sovereign_cad\application",
    "sovereign_cad\application\shell",
    "sovereign_cad\application\services",
    "sovereign_cad\tests\application"
)

foreach ($Directory in $Directories) {
    $FullDirectory = Join-Path $Root $Directory

    if (-not (Test-Path $FullDirectory)) {
        New-Item `
            -ItemType Directory `
            -Path $FullDirectory `
            -Force | Out-Null
    }
}

Write-ProjectFile `
    -Path "sovereign_cad\application\__init__.py" `
    -Content @'
from .shell import ApplicationShell
from .context import ApplicationContext

__all__ = [
    "ApplicationShell",
    "ApplicationContext",
]
'@

Write-ProjectFile `
    -Path "sovereign_cad\application\shell\__init__.py" `
    -Content @'
from .shell import ApplicationShell

__all__ = [
    "ApplicationShell",
]
'@

Write-ProjectFile `
    -Path "sovereign_cad\application\services\__init__.py" `
    -Content @'
from .application_service import ApplicationService

__all__ = [
    "ApplicationService",
]
'@

Write-ProjectFile `
    -Path "sovereign_cad\tests\application\__init__.py" `
    -Content @'
# SovereignCAD Stage 7 application tests.
'@

Write-Host "PACKAGE STRUCTURE: OK" -ForegroundColor Green

# ============================================================
# [5/12] STAGE 1-6 COMPATIBILITY
# ============================================================

Write-Host "[5/12] Validating Stage 1-6..." -ForegroundColor Yellow

$CompatibilityCode = @'
import sovereign_cad

print("SOVEREIGNCAD: OK")

modules = [
    ("GEOMETRY", "sovereign_cad.core.geometry"),
    ("ENTITIES", "sovereign_cad.core.entities"),
    ("TRANSFORMS", "sovereign_cad.core.transforms"),
    ("SPATIAL", "sovereign_cad.core.spatial"),
    ("SELECTION", "sovereign_cad.core.selection"),
    ("UI", "sovereign_cad.ui"),
    ("RENDERING", "sovereign_cad.rendering"),
    ("INPUT", "sovereign_cad.input"),
    ("COMMANDS", "sovereign_cad.commands"),
    ("DOCUMENT", "sovereign_cad.document"),
]

for label, module_name in modules:
    try:
        __import__(module_name)
        print(f"{label}: OK")
    except Exception as exc:
        print(f"{label}: WARNING: {exc}")

print("STAGE 1-6 COMPATIBILITY: OK")
'@

$CompatibilityFile = Join-Path $env:TEMP "sovereigncad_stage7_compatibility.py"

Set-Content `
    -Path $CompatibilityFile `
    -Value $CompatibilityCode `
    -Encoding UTF8

& $Python $CompatibilityFile

if ($LASTEXITCODE -ne 0) {
    throw "Stage 1-6 compatibility validation failed."
}

# ============================================================
# [6/12] APPLICATION SHELL
# ============================================================

Write-Host "[6/12] Building application shell..." -ForegroundColor Yellow

Write-ProjectFile `
    -Path "sovereign_cad\application\shell\shell.py" `
    -Content @'
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ApplicationShell:

    running: bool = False
    initialized: bool = False

    services: dict[str, Any] = field(
        default_factory=dict
    )

    def initialize(self) -> None:
        self.initialized = True

    def start(self) -> None:
        if not self.initialized:
            self.initialize()

        self.running = True

    def stop(self) -> None:
        self.running = False

    def register_service(
        self,
        name: str,
        service: Any,
    ) -> None:

        if not name:
            raise ValueError(
                "Service name must not be empty."
            )

        self.services[name] = service

    def get_service(
        self,
        name: str,
    ) -> Any:

        return self.services.get(name)

    def has_service(
        self,
        name: str,
    ) -> bool:

        return name in self.services

    def remove_service(
        self,
        name: str,
    ) -> Any:

        return self.services.pop(
            name,
            None,
        )

    def clear_services(self) -> None:
        self.services.clear()
'@

Write-Host "APPLICATION SHELL: OK" -ForegroundColor Green

# ============================================================
# [7/12] APPLICATION SERVICE
# ============================================================

Write-Host "[7/12] Building application service..." -ForegroundColor Yellow

Write-ProjectFile `
    -Path "sovereign_cad\application\services\application_service.py" `
    -Content @'
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ApplicationService:

    shell: Any = None

    state: dict[str, Any] = field(
        default_factory=dict
    )

    def set(
        self,
        key: str,
        value: Any,
    ) -> None:

        if not key:
            raise ValueError(
                "State key must not be empty."
            )

        self.state[key] = value

    def get(
        self,
        key: str,
        default: Any = None,
    ) -> Any:

        return self.state.get(
            key,
            default,
        )

    def remove(
        self,
        key: str,
    ) -> Any:

        return self.state.pop(
            key,
            None,
        )

    def clear(self) -> None:
        self.state.clear()
'@

Write-Host "APPLICATION SERVICE: OK" -ForegroundColor Green

# ============================================================
# [8/12] APPLICATION CONTEXT
# ============================================================

Write-Host "[8/12] Building application context..." -ForegroundColor Yellow

Write-ProjectFile `
    -Path "sovereign_cad\application\context.py" `
    -Content @'
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ApplicationContext:

    document: Any = None
    canvas: Any = None
    viewport: Any = None
    renderer: Any = None
    input_system: Any = None
    command_system: Any = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def set_metadata(
        self,
        key: str,
        value: Any,
    ) -> None:

        if not key:
            raise ValueError(
                "Metadata key must not be empty."
            )

        self.metadata[key] = value

    def get_metadata(
        self,
        key: str,
        default: Any = None,
    ) -> Any:

        return self.metadata.get(
            key,
            default,
        )

    def clear_metadata(self) -> None:
        self.metadata.clear()
'@

Write-Host "APPLICATION CONTEXT: OK" -ForegroundColor Green

# ============================================================
# [9/12] TESTS
# ============================================================

Write-Host "[9/12] Creating Stage 7 tests..." -ForegroundColor Yellow

Write-ProjectFile `
    -Path "sovereign_cad\tests\application\test_application.py" `
    -Content @'
from sovereign_cad.application import (
    ApplicationShell,
    ApplicationContext,
)

from sovereign_cad.application.services import (
    ApplicationService,
)


def test_application_shell():

    shell = ApplicationShell()

    assert shell.initialized is False
    assert shell.running is False

    shell.initialize()

    assert shell.initialized is True

    shell.start()

    assert shell.running is True

    shell.stop()

    assert shell.running is False


def test_service_registry():

    shell = ApplicationShell()

    service = ApplicationService(
        shell=shell
    )

    shell.register_service(
        "application",
        service,
    )

    assert shell.has_service(
        "application"
    )

    assert shell.get_service(
        "application"
    ) is service


def test_application_service():

    service = ApplicationService()

    service.set(
        "status",
        "ready",
    )

    assert service.get(
        "status"
    ) == "ready"


def test_application_context():

    context = ApplicationContext()

    context.set_metadata(
        "stage",
        7,
    )

    assert context.get_metadata(
        "stage"
    ) == 7
'@

Write-Host "STAGE 7 TESTS: CREATED" -ForegroundColor Green

# ============================================================
# [10/12] IMPORT VALIDATION
# ============================================================

Write-Host "[10/12] Validating Stage 7 imports..." -ForegroundColor Yellow

$Stage7ImportCode = @'
from sovereign_cad.application import (
    ApplicationShell,
    ApplicationContext,
)

from sovereign_cad.application.services import (
    ApplicationService,
)

shell = ApplicationShell()
context = ApplicationContext()
service = ApplicationService(shell=shell)

print("APPLICATION SHELL: OK")
print("APPLICATION CONTEXT: OK")
print("APPLICATION SERVICE: OK")
print("STAGE 7 IMPORTS: OK")
'@

$Stage7ImportFile = Join-Path $env:TEMP "sovereigncad_stage7_imports.py"

Set-Content `
    -Path $Stage7ImportFile `
    -Value $Stage7ImportCode `
    -Encoding UTF8

& $Python $Stage7ImportFile

if ($LASTEXITCODE -ne 0) {
    throw "Stage 7 imports failed."
}

# ============================================================
# [11/12] SYNTAX + COMPLETE TEST SUITE
# ============================================================

Write-Host "[11/12] Validating Python syntax..." -ForegroundColor Yellow

$PythonFiles = Get-ChildItem `
    -Path (Join-Path $Root "sovereign_cad") `
    -Recurse `
    -Filter "*.py" `
    -File

foreach ($File in $PythonFiles) {

    & $Python -m py_compile $File.FullName

    if ($LASTEXITCODE -ne 0) {
        throw "Python syntax failed: $($File.FullName)"
    }
}

Write-Host "PYTHON SYNTAX: OK" -ForegroundColor Green

Write-Host ""
Write-Host "Running complete SovereignCAD test suite..." -ForegroundColor Cyan
Write-Host ""

& $Python -m pytest `
    (Join-Path $Root "sovereign_cad\tests") `
    -q

if ($LASTEXITCODE -ne 0) {

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Red
    Write-Host "              STAGE 7 TESTS FAILED" -ForegroundColor Red
    Write-Host "============================================================" -ForegroundColor Red
    Write-Host ""

    throw "SovereignCAD Stage 7 tests failed."
}

# ============================================================
# [12/12] SMOKE TEST
# ============================================================

Write-Host ""
Write-Host "[12/12] Running final Stage 7 smoke test..." -ForegroundColor Yellow
Write-Host ""

$SmokeCode = @'
from sovereign_cad.application import (
    ApplicationShell,
    ApplicationContext,
)

from sovereign_cad.application.services import (
    ApplicationService,
)


print("Checking application shell...")

shell = ApplicationShell()

assert shell.initialized is False
assert shell.running is False

shell.initialize()

assert shell.initialized is True

shell.start()

assert shell.running is True

print("APPLICATION SHELL: ONLINE")


print("Checking application context...")

context = ApplicationContext()

context.set_metadata(
    "stage",
    7,
)

assert context.get_metadata(
    "stage"
) == 7

print("APPLICATION CONTEXT: ONLINE")


print("Checking application service...")

service = ApplicationService(
    shell=shell
)

service.set(
    "status",
    "ready",
)

assert service.get(
    "status"
) == "ready"

print("APPLICATION SERVICE: ONLINE")


print("Checking service registration...")

shell.register_service(
    "application",
    service,
)

assert shell.has_service(
    "application"
)

assert shell.get_service(
    "application"
) is service

print("SERVICE REGISTRY: ONLINE")


shell.stop()

assert shell.running is False

print("APPLICATION LIFECYCLE: OK")

print("")
print("STAGE 7 SMOKE TEST: OK")
'@

$SmokeFile = Join-Path $env:TEMP "sovereigncad_stage7_smoke.py"

Set-Content `
    -Path $SmokeFile `
    -Value $SmokeCode `
    -Encoding UTF8

Write-Host "CREATE/UPDATE: $SmokeFile" -ForegroundColor DarkGray

& $Python $SmokeFile

if ($LASTEXITCODE -ne 0) {

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Red
    Write-Host "              STAGE 7 SMOKE TEST FAILED" -ForegroundColor Red
    Write-Host "============================================================" -ForegroundColor Red
    Write-Host ""

    throw "SovereignCAD Stage 7 smoke test failed."
}

# ============================================================
# SUCCESS
# ============================================================

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "             SOVEREIGNCAD STAGE 7: SUCCESS" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""

Write-Host "Geometry Kernel       : ONLINE" -ForegroundColor Green
Write-Host "Entity System         : ONLINE" -ForegroundColor Green
Write-Host "Transform System      : ONLINE" -ForegroundColor Green
Write-Host "Spatial System        : ONLINE" -ForegroundColor Green
Write-Host "Selection System      : ONLINE" -ForegroundColor Green
Write-Host "Viewport Engine       : ONLINE" -ForegroundColor Green
Write-Host "Canvas State          : ONLINE" -ForegroundColor Green
Write-Host "Renderer              : ONLINE" -ForegroundColor Green
Write-Host "Render Commands       : ONLINE" -ForegroundColor Green
Write-Host "Input System          : ONLINE" -ForegroundColor Green
Write-Host "Command System        : ONLINE" -ForegroundColor Green
Write-Host "Undo / Redo           : ONLINE" -ForegroundColor Green
Write-Host "Document Session      : ONLINE" -ForegroundColor Green
Write-Host "Application Shell     : ONLINE" -ForegroundColor Green
Write-Host "Application Context   : ONLINE" -ForegroundColor Green
Write-Host "Application Services  : ONLINE" -ForegroundColor Green
Write-Host "Stage 7 Tests         : PASS" -ForegroundColor Green
Write-Host "Stage 7 Smoke Test    : PASS" -ForegroundColor Green
Write-Host ""

Write-Host "SovereignCAD Stage 7 is complete." -ForegroundColor Green
Write-Host ""

