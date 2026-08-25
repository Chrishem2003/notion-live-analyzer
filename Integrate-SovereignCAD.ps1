$ErrorActionPreference = "Stop"
$AppPath = Join-Path (Get-Location).Path "app.py"

if (-not (Test-Path $AppPath)) {
    throw "app.py not found in the current directory!"
}

Write-Host "Backing up app.py to app.py.bak..." -ForegroundColor Yellow
Copy-Item $AppPath "$AppPath.bak" -Force

$Content = Get-Content $AppPath -Raw

# 1. Check if Sovereign CAD menu option already exists using plain string search (-like instead of -match)
if ($Content -like "*Sovereign CAD*") {
    Write-Host "Sovereign CAD menu option is already present in app.py!" -ForegroundColor Green
    exit
}

# 2. Append the safe routing handler logic at the bottom of the navigation block
$RoutingCode = @"

elif menu_selection == "?? Sovereign CAD":
    try:
        from sovereign_cad.streamlit import render_cad_workspace
        render_cad_workspace()
    except Exception as e:
        st.error(f"Could not load Sovereign CAD workspace: {e}")
"@

if ($Content -match 'else:') {
    $Content = $Content -replace 'else:', "$RoutingCode`n`nelse:"
    Write-Host "Injected routing handler safely before fallback else block." -ForegroundColor Cyan
} else {
    $Content += $RoutingCode
    Write-Host "Appended routing handler to the end of app.py." -ForegroundColor Cyan
}

# Save updated app.py with UTF-8 encoding
Set-Content -Path $AppPath -Value $Content -Encoding UTF8
Write-Host "SUCCESS: app.py updated safely with Sovereign CAD integration!" -ForegroundColor Green
