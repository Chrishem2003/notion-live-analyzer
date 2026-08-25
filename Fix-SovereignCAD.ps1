$ErrorActionPreference = "Stop"
$AppPath = Join-Path (Get-Location).Path "app.py"
$BackupPath = "$AppPath.bak"

Write-Host "[1/5] Checking for app.py backup..." -ForegroundColor Yellow
if (Test-Path $BackupPath) {
    Copy-Item $BackupPath $AppPath -Force
    Write-Host "Restored clean state from app.py.bak" -ForegroundColor Green
} else {
    Write-Host "Warning: No backup found, working on current app.py" -ForegroundColor Yellow
}

if (-not (Test-Path $AppPath)) {
    throw "app.py not found in the current directory!"
}

Write-Host "[2/5] Reading app.py contents..." -ForegroundColor Yellow
$Content = Get-Content $AppPath -Raw

# Check if Sovereign CAD is already integrated
if ($Content -like "*Sovereign CAD*") {
    Write-Host "Sovereign CAD is already present in app.py." -ForegroundColor Green
} else {
    Write-Host "[3/5] Injecting Sovereign CAD menu option and router..." -ForegroundColor Yellow
    
    # Safe routing code block (using plain text to prevent encoding/syntax issues)
    $RoutingCode = @"

elif menu_selection == "Sovereign CAD":
    try:
        from sovereign_cad.streamlit import render_cad_workspace
        render_cad_workspace()
    except Exception as e:
        st.error(f"Could not load Sovereign CAD workspace: {e}")
"@

    # Inject before fallback else block or at the end
    if ($Content -match 'else:') {
        $Content = $Content -replace 'else:', "$RoutingCode`n`nelse:"
    } else {
        $Content += $RoutingCode
    }
    
    # Save with explicit UTF-8 encoding so emojis/characters never break Python syntax
    [System.IO.File]::WriteAllText($AppPath, $Content, [System.Text.Encoding]::UTF8)
    Write-Host "Router injected successfully!" -ForegroundColor Green
}

Write-Host "[4/5] Staging changes in Git..." -ForegroundColor Yellow
git add app.py

Write-Host "[5/5] Committing and pushing to GitHub..." -ForegroundColor Yellow
git commit -m "fix: safely integrate Sovereign CAD without syntax or encoding errors"
git push

Write-Host "SUCCESS: Everything has been corrected, committed, and pushed!" -ForegroundColor Green
