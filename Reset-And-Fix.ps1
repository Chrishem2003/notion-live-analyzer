$ErrorActionPreference = "Stop"
$AppPath = Join-Path (Get-Location).Path "app.py"
$BackupPath = "$AppPath.bak"

Write-Host "[1/4] Forcibly restoring pristine backup (app.py.bak)..." -ForegroundColor Yellow
if (Test-Path $BackupPath) {
    Copy-Item $BackupPath $AppPath -Force
    Write-Host "Restored app.py successfully from backup." -ForegroundColor Green
} else {
    throw "Fatal: app.py.bak not found! Please ensure your base backup file is present."
}

Write-Host "[2/4] Reading clean code and injecting Sovereign CAD safely..." -ForegroundColor Yellow
$Content = Get-Content $AppPath -Raw

# Clean up any potential leftover corruption characters in the file
$Content = $Content -replace '(?i)\?\?', ''

# Append a clean, standalone, guarded block at the end of app.py that doesn't mess with existing indentation
$SovereignIntegration = @"


# ==========================================
# Sovereign CAD Integration Module
# ==========================================
if 'menu_selection' in locals() and menu_selection == "Sovereign CAD":
    try:
        from sovereign_cad.streamlit import render_cad_workspace
        render_cad_workspace()
    except Exception as e:
        st.error(f"Could not load Sovereign CAD workspace: {{e}}")
"@

$Content += $SovereignIntegration

# Force UTF-8 without BOM encoding to prevent Windows/PowerShell encoding corruption
[System.IO.File]::WriteAllText($AppPath, $Content, [System.Text.Encoding]::UTF8)
Write-Host "Sovereign CAD integration appended cleanly." -ForegroundColor Green

Write-Host "[3/4] Staging updated files..." -ForegroundColor Yellow
git add app.py

Write-Host "[4/4] Committing and pushing to GitHub..." -ForegroundColor Yellow
git commit -m "fix: reset file corruption and add clean independent Sovereign CAD block"
git push

Write-Host "SUCCESS: Application reset, cleaned of corruption, and pushed to GitHub!" -ForegroundColor Green
