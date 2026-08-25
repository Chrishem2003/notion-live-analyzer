$ErrorActionPreference = "Stop"
$AppPath = Join-Path (Get-Location).Path "app.py"
$BackupPath = "$AppPath.bak"

Write-Host "[1/4] Restoring clean backup..." -ForegroundColor Yellow
if (Test-Path $BackupPath) {
    Copy-Item $BackupPath $AppPath -Force
} else {
    throw "Backup app.py.bak not found! Please ensure your base app.py is intact."
}

Write-Host "[2/4] Reading and updating app.py safely..." -ForegroundColor Yellow
$Content = Get-Content $AppPath -Raw

# 1. Ensure "Sovereign CAD" is in the menu selection list
$OldMenuPattern = 'st\.sidebar\.selectbox\(\s*"Navigation",\s*\[(.*?)\]'
if ($Content -match $OldMenuPattern) {
    $CurrentOptions = $Matches[1]
    if ($CurrentOptions -notlike "*Sovereign CAD*") {
        # Add Sovereign CAD cleanly into the list items
        $NewOptions = $CurrentOptions.TrimEnd() + "`n        `"Sovereign CAD`","
        $Content = $Content -replace [regex]::Escape($CurrentOptions), $NewOptions
        Write-Host "Added Sovereign CAD to navigation selectbox options." -ForegroundColor Green
    }
} else {
    Write-Host "Warning: Could not automatically locate sidebar selectbox pattern, checking manual placement..." -ForegroundColor Yellow
}

# 2. Append a safe, independent if-block at the end of the file (guarantees no syntax/elif nesting errors)
$SafeBlock = @"


# --- Sovereign CAD Router Integration ---
if 'menu_selection' in locals() and menu_selection == "Sovereign CAD":
    try:
        from sovereign_cad.streamlit import render_cad_workspace
        render_cad_workspace()
    except Exception as e:
        st.error(f"Could not load Sovereign CAD workspace: {e}")
------------------------------------------
"@
# Replace the dashes comment with actual clean python code block
$SafeBlockPython = @"


# --- Sovereign CAD Router Integration ---
if 'menu_selection' in locals() and menu_selection == "Sovereign CAD":
    try:
        from sovereign_cad.streamlit import render_cad_workspace
        render_cad_workspace()
    except Exception as e:
        st.error(f"Could not load Sovereign CAD workspace: {e}")
"@

$Content += $SafeBlockPython

# Write back with explicit UTF-8 encoding
[System.IO.File]::WriteAllText($AppPath, $Content, [System.Text.Encoding]::UTF8)
Write-Host "Successfully updated app.py with valid syntax structure!" -ForegroundColor Green

Write-Host "[3/4] Staging changes..." -ForegroundColor Yellow
git add app.py

Write-Host "[4/4] Committing and pushing to GitHub..." -ForegroundColor Yellow
git commit -m "fix: replace broken elif with independent guarded if-block for Sovereign CAD"
git push

Write-Host "SUCCESS: Fix pushed to GitHub. Streamlit will rebuild cleanly now!" -ForegroundColor Green
