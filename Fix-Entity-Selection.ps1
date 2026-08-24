$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "       SOVEREIGNCAD ENTITY SELECTION REPAIR" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$Root = (Get-Location).Path
$EntityFile = Join-Path $Root "sovereign_cad\core\entities\entity.py"

if (-not (Test-Path $EntityFile)) {
    throw "Entity file not found: $EntityFile"
}

Write-Host "[1/5] Backing up entity.py..." -ForegroundColor Yellow

$Backup = "$EntityFile.selection-backup"

Copy-Item $EntityFile $Backup -Force

Write-Host "BACKUP: $Backup" -ForegroundColor Green

Write-Host "[2/5] Reading entity.py..." -ForegroundColor Yellow

$content = Get-Content $EntityFile -Raw

Write-Host "[3/5] Adding selection methods..." -ForegroundColor Yellow

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

if ($content -match 'def select\(self\)') {
    Write-Host "Selection methods already exist. No duplicate added." -ForegroundColor Yellow
}
else {
    $content = $content.TrimEnd() + $methods + "`r`n"

    Set-Content `
        -LiteralPath $EntityFile `
        -Value $content `
        -Encoding UTF8

    Write-Host "ENTITY.PY: UPDATED" -ForegroundColor Green
}

Write-Host "[4/5] Clearing Python caches..." -ForegroundColor Yellow

Get-ChildItem `
    -Path $Root `
    -Directory `
    -Recurse `
    -Force `
    -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -eq "__pycache__" } |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "CACHE: CLEARED" -ForegroundColor Green

Write-Host "[5/5] Testing selection..." -ForegroundColor Yellow

python -c "from sovereign_cad.core.entities import LineEntity; from sovereign_cad.core.geometry import Point2; e=LineEntity(Point2(0,0),Point2(10,0)); print('Initially:',e.selected); e.select(); print('After select:',e.selected); assert e.selected is True; e.deselect(); print('After deselect:',e.selected); assert e.selected is False; print('SELECTION: OK')"

if ($LASTEXITCODE -ne 0) {
    throw "Entity selection verification failed."
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "       ENTITY SELECTION REPAIR COMPLETE" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""

Write-Host "Running full SovereignCAD test suite..." -ForegroundColor Cyan
Write-Host ""

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