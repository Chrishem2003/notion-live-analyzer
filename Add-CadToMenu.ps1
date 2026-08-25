$ErrorActionPreference = "Stop"
$AppPath = Join-Path (Get-Location).Path "app.py"

Write-Host "[1/3] Reading app.py..." -ForegroundColor Yellow
$Content = Get-Content $AppPath -Raw

# Check if Sovereign CAD is already in the selectbox list
if ($Content -like '*"Sovereign CAD"*') {
    Write-Host "Sovereign CAD is already inside the selectbox options." -ForegroundColor Green
} else {
    Write-Host "[2/3] Inserting Sovereign CAD into the sidebar navigation selectbox..." -ForegroundColor Yellow
    
    # Target the navigation selectbox list options array and insert Sovereign CAD
    # Look for common sidebar selectbox patterns like st.sidebar.selectbox(..., [ ... ])
    if ($Content -match 'st\.sidebar\.selectbox\s*\(\s*["\']Navigation["\'],\s*\[([^\]]+)\]') {
        $ExistingOptions = $Matches[1]
        if ($ExistingOptions -notlike '*Sovereign CAD*') {
            $UpdatedOptions = $ExistingOptions.TrimEnd() + "`n        `"Sovereign CAD`","
            $Content = $Content -replace [regex]::Escape($ExistingOptions), $UpdatedOptions
            Write-Host "Injected Sovereign CAD into navigation list successfully." -ForegroundColor Green
        }
    } else {
        # Fallback: General regex pattern match for any list inside selectbox
        $Content = $Content -replace '(\bSt\.sidebar\.selectbox\s*\([^,]+,\s*\[)([^\]]+)(\])', '$1$2, "Sovereign CAD"$3'
        Write-Host "Applied fallback selectbox injection." -ForegroundColor Green
    }
}

# Save cleanly with UTF-8 encoding
[System.IO.File]::WriteAllText($AppPath, $Content, [System.Text.Encoding]::UTF8)

Write-Host "[3/3] Committing and pushing updates to GitHub..." -ForegroundColor Yellow
git add app.py
git commit -m "feat: add Sovereign CAD option directly into sidebar navigation selectbox"
git push

Write-Host "SUCCESS: Sovereign CAD option added to the navigation menu and pushed!" -ForegroundColor Green
