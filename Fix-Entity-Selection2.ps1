$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "     SOVEREIGNCAD ENTITY SELECTION REPAIR 2" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$Root = (Get-Location).Path
$EntityFile = Join-Path $Root "sovereign_cad\core\entities\entity.py"
$BackupFile = "$EntityFile.selection-backup"

if (-not (Test-Path $EntityFile)) {
    throw "Entity file not found: $EntityFile"
}

Write-Host "[1/6] Restoring clean entity.py backup..." -ForegroundColor Yellow

if (Test-Path $BackupFile) {
    Copy-Item $BackupFile $EntityFile -Force
    Write-Host "RESTORE: OK" -ForegroundColor Green
}
else {
    throw "Backup not found: $BackupFile"
}

Write-Host "[2/6] Inspecting Entity class..." -ForegroundColor Yellow

$content = Get-Content $EntityFile -Raw

if (-not ($content -match 'class Entity')) {
    throw "Entity class was not found."
}

Write-Host "ENTITY CLASS: OK" -ForegroundColor Green

Write-Host "[3/6] Inserting selection methods inside Entity..." -ForegroundColor Yellow

$marker = @'
    def set_layer(self, layer: str) -> None:
'@

$methods = @'
    def select(self) -> None:
        """Mark this entity as selected."""
        self.selected = True

    def deselect(self) -> None:
        """Mark this entity as not selected."""
        self.selected = False

    def is_selected(self) -> bool:
        """Return whether this entity is currently selected."""
        return self.selected

'@

if ($content -match '(?m)^\s+def select\(self\)') {
    Write-Host "SELECTION METHODS: ALREADY PRESENT" -ForegroundColor Yellow
}
elseif ($content.Contains($marker)) {
    $content = $content.Replace($marker, $methods + $marker)

    Set-Content `
        -LiteralPath $EntityFile `
        -Value $content `
        -Encoding UTF8

    Write-Host "SELECTION METHODS: INSERTED" -ForegroundColor Green
}
else {
    throw "Could not find set_layer() insertion point."
}

Write-Host "[4/6] Clearing Python caches..." -ForegroundColor Yellow

Get-ChildItem `
    -Path $Root `
    -Directory `
    -Recurse `
    -Force `
    -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -eq "__pycache__" } |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "CACHE: CLEARED" -ForegroundColor Green

Write-Host "[5/6] Verifying entity selection..." -ForegroundColor Yellow

python -c "from sovereign_cad.core.entities import LineEntity; from sovereign_cad.core.geometry import Point2; e=LineEntity(Point2(0,0),Point2(10,0)); print('Initially:',e.selected); e.select(); print('Selected:',e.selected); assert e.selected is True; e.deselect(); print('Deselected:',e.selected); assert e.selected is False; print('SELECTION: OK')"

if ($LASTEXITCODE -ne 0) {
    throw "Entity selection verification failed."
}

Write-Host "[6/6] Running complete SovereignCAD test suite..." -ForegroundColor Yellow

python -m pytest sovereign_cad/tests -q

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "TESTS STILL HAVE FAILURES." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "       SOVEREIGNCAD TEST SUITE: ALL PASSED" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "ENTITY ENGINE       : ONLINE" -ForegroundColor Green
Write-Host "DOCUMENT ENGINE     : ONLINE" -ForegroundColor Green
Write-Host "COMMAND ENGINE      : ONLINE" -ForegroundColor Green
Write-Host "UNDO / REDO         : ONLINE" -ForegroundColor Green
Write-Host "SELECTION           : ONLINE" -ForegroundColor Green
Write-Host "TESTS               : PASSED" -ForegroundColor Green
Write-Host ""
Write-Host "READY FOR NEXT STAGE." -ForegroundColor Cyan
Write-Host ""