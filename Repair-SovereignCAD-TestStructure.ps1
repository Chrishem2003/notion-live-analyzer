$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "       SOVEREIGNCAD TEST STRUCTURE REPAIR" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$Root = (Get-Location).Path
$CadRoot = Join-Path $Root "sovereign_cad"
$CoreRoot = Join-Path $CadRoot "core"
$TestsRoot = Join-Path $CadRoot "tests"

Write-Host "Project: $Root" -ForegroundColor Gray
Write-Host ""

# ------------------------------------------------------------
# 1. Verify project structure
# ------------------------------------------------------------

Write-Host "[1/6] Verifying SovereignCAD structure..." -ForegroundColor Yellow

if (-not (Test-Path $CadRoot)) {
    throw "sovereign_cad directory not found."
}

if (-not (Test-Path $CoreRoot)) {
    throw "sovereign_cad\core directory not found."
}

if (-not (Test-Path $TestsRoot)) {
    throw "sovereign_cad\tests directory not found."
}

Write-Host "SOVEREIGNCAD STRUCTURE: OK" -ForegroundColor Green

# ------------------------------------------------------------
# 2. Ensure package markers
# ------------------------------------------------------------

Write-Host "[2/6] Ensuring package markers..." -ForegroundColor Yellow

$PackageDirectories = @(
    $CadRoot,
    $CoreRoot,
    (Join-Path $CoreRoot "commands"),
    (Join-Path $CoreRoot "document"),
    (Join-Path $CoreRoot "entities"),
    (Join-Path $CoreRoot "geometry"),
    (Join-Path $CoreRoot "selection"),
    (Join-Path $CoreRoot "spatial"),
    (Join-Path $CoreRoot "transforms"),
    $TestsRoot,
    (Join-Path $TestsRoot "commands"),
    (Join-Path $TestsRoot "document"),
    (Join-Path $TestsRoot "entities"),
    (Join-Path $TestsRoot "selection"),
    (Join-Path $TestsRoot "spatial"),
    (Join-Path $TestsRoot "transforms")
)

foreach ($Directory in $PackageDirectories) {

    if (-not (Test-Path $Directory)) {
        New-Item -ItemType Directory -Path $Directory -Force | Out-Null
    }

    $InitFile = Join-Path $Directory "__init__.py"

    if (-not (Test-Path $InitFile)) {
        Set-Content -LiteralPath $InitFile -Value "" -Encoding UTF8
        Write-Host "CREATE: $InitFile" -ForegroundColor Green
    }
}

Write-Host "PACKAGE MARKERS: OK" -ForegroundColor Green

# ------------------------------------------------------------
# 3. Remove stale Python cache
# ------------------------------------------------------------

Write-Host "[3/6] Removing stale Python caches..." -ForegroundColor Yellow

Get-ChildItem $CadRoot -Recurse -Directory -Force |
    Where-Object { $_.Name -eq "__pycache__" } |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "PYTHON CACHE: CLEAN" -ForegroundColor Green

# ------------------------------------------------------------
# 4. Create pytest configuration
# ------------------------------------------------------------

Write-Host "[4/6] Creating pytest configuration..." -ForegroundColor Yellow

$PytestConfig = @'
[pytest]
testpaths =
    sovereign_cad/tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -ra
'@

Set-Content `
    -LiteralPath (Join-Path $Root "pytest.ini") `
    -Value $PytestConfig `
    -Encoding UTF8

Write-Host "CREATE: pytest.ini" -ForegroundColor Green

# ------------------------------------------------------------
# 5. Verify imports before pytest
# ------------------------------------------------------------

Write-Host "[5/6] Verifying SovereignCAD imports..." -ForegroundColor Yellow

$Python = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    $Python = "python"
}

& $Python -c "from sovereign_cad.core.geometry import Point2; from sovereign_cad.core.entities import Entity, LineEntity, CircleEntity, EntityRegistry; print('SOVEREIGNCAD IMPORT: OK')"

if ($LASTEXITCODE -ne 0) {
    throw "SovereignCAD import verification failed."
}

# ------------------------------------------------------------
# 6. Run ONLY SovereignCAD tests
# ------------------------------------------------------------

Write-Host "[6/6] Running SovereignCAD test suite..." -ForegroundColor Yellow
Write-Host ""

& $Python -m pytest sovereign_cad/tests -q

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Red
    Write-Host "       SOVEREIGNCAD TESTS STILL HAVE ERRORS" -ForegroundColor Red
    Write-Host "============================================================" -ForegroundColor Red
    Write-Host ""
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "       SOVEREIGNCAD TEST STRUCTURE: FIXED" -ForegroundColor Green
Write-Host "       SOVEREIGNCAD TESTS: PASSED" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""