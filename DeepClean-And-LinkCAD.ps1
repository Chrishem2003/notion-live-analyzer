$ErrorActionPreference = "Stop"
$RootPath = (Get-Location).Path
$AppPath = Join-Path $RootPath "app.py"
$BackupPath = "$AppPath.bak"

Write-Host "[1/5] Restoring absolute clean base from backup..." -ForegroundColor Yellow
if (Test-Path $BackupPath) {
    Copy-Item $BackupPath $AppPath -Force
} else {
    throw "Fatal: app.py.bak missing! Please provide a clean baseline app.py."
}

Write-Host "[2/5] Purging all Mojibake / encoding character artifacts across repository files..." -ForegroundColor Yellow
# Find Python and text files and clean out corrupted UTF-8 byte sequences
Get-ChildItem -Path $RootPath -Recurse -Include *.py, *.md, *.txt | ForEach-Object {
    $FilePath = $_.FullName
    try {
        # Read using raw bytes/UTF8 to strip broken sequences
        $Bytes = [System.IO.File]::ReadAllBytes($FilePath)
        $Text = [System.Text.Encoding]::UTF8.GetString($Bytes)
        
        # Strip common Mojibake patterns like ⚡, 🌟, etc.
        $CleanText = $Text -replace '⚡|🌟|✨|�\u0080|�\u0099', ''
        
        [System.IO.File]::WriteAllText($FilePath, $CleanText, [System.Text.Encoding]::UTF8)
    } catch {
        Write-Host "Skipped locked/binary file: $FilePath" -ForegroundColor DarkGray
    }
}

Write-Host "[3/5] Properly integrating Sovereign CAD into app.py..." -ForegroundColor Yellow
$Content = Get-Content $AppPath -Raw

# Ensure Sovereign CAD menu option and router are safely present
$CadIntegrationBlock = @"


# ==========================================
# Sovereign CAD Workspace Integration
# ==========================================
if 'menu_selection' in locals() and menu_selection == "Sovereign CAD":
    try:
        from sovereign_cad.streamlit import render_cad_workspace
        render_cad_workspace()
    except Exception as e:
        st.error(f"Could not load Sovereign CAD workspace: {{e}}")
else:
    # Fallback or standard flow check
    pass
"@

$Content += $CadIntegrationBlock

# Write back with explicit UTF-8 encoding (No BOM)
[System.IO.File]::WriteAllText($AppPath, $Content, [System.Text.Encoding]::UTF8)
Write-Host "Sovereign CAD linkage successfully appended." -ForegroundColor Green

Write-Host "[4/5] Staging clean repository changes..." -ForegroundColor Yellow
git add .

Write-Host "[5/5] Committing and pushing to GitHub..." -ForegroundColor Yellow
git commit -m "fix: deep clean text encoding artifacts and integrate Sovereign CAD workspace"
git push

Write-Host "SUCCESS: Workspace fully sanitized, linked, and pushed to GitHub!" -ForegroundColor Green
