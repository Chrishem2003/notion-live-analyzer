$ErrorActionPreference = "Stop"

$Repo = "D:\notion-live-analyzer"
$Builder = Join-Path $Repo "Build-SovereignIntelligence-Stage2.ps1"

Set-Location -LiteralPath $Repo

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " STAGE 2 BUILDER REPAIR" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path -LiteralPath $Builder)) {
    throw "Build-SovereignIntelligence-Stage2.ps1 was not found."
}

$BackupDir = Join-Path $Repo "backups"
New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

$Backup = Join-Path `
    $BackupDir `
    "Build-SovereignIntelligence-Stage2_$Timestamp.ps1"

Copy-Item `
    -LiteralPath $Builder `
    -Destination $Backup `
    -Force

Write-Host "[OK] Backup created:" -ForegroundColor Green
Write-Host $Backup

$Content = [System.IO.File]::ReadAllText(
    $Builder,
    [System.Text.Encoding]::UTF8
)

$Content = $Content.Replace(
    [string][char]0xFEFF,
    ""
)

if ($Content.Contains([char]0xFFFD)) {
    throw "U+FFFD replacement character found in the builder."
}

$PythonLine = '$Python = Join-Path $Repo ".venv\Scripts\python.exe"'

if (-not $Content.Contains($PythonLine)) {

    $Marker = '$BackupRoot = Join-Path $Repo ("backups\sovereign_stage2_" + (Get-Date -Format "yyyyMMdd_HHmmss"))'

    if ($Content.Contains($Marker)) {

        $Content = $Content.Replace(
            $Marker,
            $Marker + "`r`n" + $PythonLine
        )

        Write-Host "[FIX] Python initialization inserted." -ForegroundColor Yellow

    }
    else {
        throw "Could not find Stage 2 initialization block."
    }
}
else {
    Write-Host "[OK] Python initialization already exists." -ForegroundColor Green
}

$StrictLine = 'Set-StrictMode -Version Latest'

$strictIndex = $Content.IndexOf($StrictLine)
$pythonIndex = $Content.IndexOf($PythonLine)

if ($strictIndex -ge 0 -and $pythonIndex -ge 0) {

    if ($strictIndex -lt $pythonIndex) {

        $Content = $Content.Replace(
            $StrictLine,
            "# StrictMode enabled after variables are initialized.`r`n" +
            $StrictLine
        )

        Write-Host "[FIX] StrictMode ordering normalized." -ForegroundColor Yellow
    }
}

$Utf8NoBom = [System.Text.UTF8Encoding]::new($false)

[System.IO.File]::WriteAllText(
    $Builder,
    $Content,
    $Utf8NoBom
)

Write-Host "[OK] Builder saved as UTF-8 without BOM." -ForegroundColor Green

$Tokens = $null
$Errors = $null

[System.Management.Automation.Language.Parser]::ParseFile(
    $Builder,
    [ref]$Tokens,
    [ref]$Errors
) | Out-Null

if ($Errors.Count -gt 0) {

    Write-Host ""
    Write-Host "[FAIL] PowerShell syntax errors:" -ForegroundColor Red

    foreach ($ErrorRecord in $Errors) {
        Write-Host $ErrorRecord.Message -ForegroundColor Red
    }

    throw "Stage 2 builder syntax validation failed."
}

Write-Host "[OK] PowerShell syntax validated." -ForegroundColor Green

$Python = Join-Path $Repo ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python executable not found: $Python"
}

Write-Host "[OK] Python found:" -ForegroundColor Green
Write-Host $Python

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " STAGE 2 BUILDER REPAIR COMPLETE" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Backup created at:" -ForegroundColor Cyan
Write-Host $Backup
Write-Host ""
Write-Host "NEXT:" -ForegroundColor Yellow
Write-Host ".\Build-SovereignIntelligence-Stage2.ps1" -ForegroundColor Yellow
Write-Host ""
