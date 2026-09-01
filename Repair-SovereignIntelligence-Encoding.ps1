$ErrorActionPreference = "Stop"

$Repo = "D:\notion-live-analyzer"
$Package = Join-Path $Repo "sovereign_intelligence"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " SOVEREIGN INTELLIGENCE ENCODING REPAIR" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path -LiteralPath $Repo)) {
    throw "Repository not found: $Repo"
}

Set-Location -LiteralPath $Repo

if (-not (Test-Path -LiteralPath $Package)) {
    throw "sovereign_intelligence folder was not found."
}

$PythonFiles = Get-ChildItem `
    -LiteralPath $Package `
    -Recurse `
    -File `
    -Filter "*.py"

if ($PythonFiles.Count -eq 0) {
    throw "No Python files found under sovereign_intelligence."
}

Write-Host "[1/4] Checking Python source files..." -ForegroundColor Cyan

foreach ($File in $PythonFiles) {

    $bytes = [System.IO.File]::ReadAllBytes($File.FullName)

    $text = [System.Text.Encoding]::UTF8.GetString($bytes)

    if ($text.Contains([char]0xFFFD)) {
        Write-Host ""
        Write-Host "[FAIL] U+FFFD found in:" -ForegroundColor Red
        Write-Host $File.FullName -ForegroundColor Red
        throw "Invalid replacement character detected."
    }

    if ($text.Contains([char]0xFEFF)) {

        $text = $text.Replace(
            [string][char]0xFEFF,
            ""
        )

        [System.IO.File]::WriteAllText(
            $File.FullName,
            $text,
            [System.Text.UTF8Encoding]::new($false)
        )

        Write-Host "[FIXED] Removed UTF-8 BOM: $($File.Name)" -ForegroundColor Yellow
    }
    else {

        [System.IO.File]::WriteAllText(
            $File.FullName,
            $text,
            [System.Text.UTF8Encoding]::new($false)
        )

        Write-Host "[OK] $($File.Name)" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "[2/4] Locating Python..." -ForegroundColor Cyan

$Python = Join-Path $Repo ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Virtual environment Python not found: $Python"
}

Write-Host "[OK] $Python" -ForegroundColor Green

Write-Host ""
Write-Host "[3/4] Compiling every Sovereign Intelligence module..." -ForegroundColor Cyan

foreach ($File in $PythonFiles) {

    & $Python -m py_compile $File.FullName

    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "[FAIL] Compilation failed:" -ForegroundColor Red
        Write-Host $File.FullName -ForegroundColor Red
        throw "Python compilation failed."
    }

    Write-Host "[OK] $($File.Name)" -ForegroundColor Green
}

Write-Host ""
Write-Host "[4/4] Testing Sovereign Brain import..." -ForegroundColor Cyan

& $Python -c "from sovereign_intelligence import SovereignBrain; print('SOVEREIGN_BRAIN_OK')"

if ($LASTEXITCODE -ne 0) {
    throw "SovereignBrain import failed."
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " ENCODING REPAIR SUCCESSFUL" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Sovereign Intelligence source files are clean." -ForegroundColor Green
Write-Host "SovereignBrain imports successfully." -ForegroundColor Green
Write-Host ""