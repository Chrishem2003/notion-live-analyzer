$ErrorActionPreference = "Stop"
$Root = (Get-Location).Path
$ZipPath = "D:\APP\round14_reference_manager_v2.zip"
$TempExtractDir = Join-Path $Root "temp_round14_extract"

Write-Host "Extracting and integrating Round 14 Reference Manager..." -ForegroundColor Cyan

if (-not (Test-Path $ZipPath)) {
    throw "ZIP file not found at: $ZipPath"
}

if (Test-Path $TempExtractDir) { Remove-Item -Path $TempExtractDir -Recurse -Force }
New-Item -ItemType Directory -Path $TempExtractDir -Force | Out-Null
Expand-Archive -Path $ZipPath -DestinationPath $TempExtractDir -Force

Get-ChildItem -Path $TempExtractDir -Recurse | ForEach-Object {
    $RelativePath = $_.FullName.Substring($TempExtractDir.Length + 1)
    $DestinationPath = Join-Path $Root $RelativePath
    if ($_.PSIsContainer) {
        if (-not (Test-Path $DestinationPath)) { New-Item -ItemType Directory -Path $DestinationPath -Force | Out-Null }
    } else {
        $ParentDir = Split-Path $DestinationPath -Parent
        if (-not (Test-Path $ParentDir)) { New-Item -ItemType Directory -Path $ParentDir -Force | Out-Null }
        Copy-Item -Path $_.FullName -Destination $DestinationPath -Force
    }
}

Remove-Item -Path $TempExtractDir -Recurse -Force
Write-Host "Integration Complete! Check ROUND_14_INTEGRATION_NOTES.txt for routing instructions." -ForegroundColor Green
