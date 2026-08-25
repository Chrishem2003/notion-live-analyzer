$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "   CHRISHEM SOVEREIGN CAD INTEGRATION FIX"
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# --------------------------------------------------
# 1. VERIFY REPOSITORY
# --------------------------------------------------

if (-not (Test-Path ".git")) {
    Write-Host "ERROR: You are not inside the Git repository." -ForegroundColor Red
    Write-Host "Open PowerShell inside D:\notion-live-analyzer and run again."
    exit 1
}

if (-not (Test-Path "app.py")) {
    Write-Host "ERROR: app.py was not found." -ForegroundColor Red
    exit 1
}

# --------------------------------------------------
# 2. BACKUP app.py
# --------------------------------------------------

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backup = "app.py.backup_$timestamp"

Copy-Item "app.py" $backup -Force

Write-Host "Backup created:" -ForegroundColor Green
Write-Host "  $backup"
Write-Host ""

# --------------------------------------------------
# 3. READ APP
# --------------------------------------------------

$content = Get-Content "app.py" -Raw

Write-Host "Checking sidebar navigation..." -ForegroundColor Yellow

# --------------------------------------------------
# 4. ADD SOVEREIGN CAD TO SIDEBAR
# --------------------------------------------------

$oldMenu = @'
        "📊 Sovereign Analytics Engine",
        "📝 Query Log",
'@

$newMenu = @'
        "📊 Sovereign Analytics Engine",
        "🏗️ Sovereign CAD",
        "📝 Query Log",
'@

if ($content -notmatch '"🏗️ Sovereign CAD"') {

    if ($content.Contains($oldMenu)) {

        $content = $content.Replace(
            $oldMenu,
            $newMenu
        )

        Write-Host "CAD navigation item added." -ForegroundColor Green

    }
    else {

        Write-Host "WARNING: Standard sidebar location not found." -ForegroundColor Yellow
        Write-Host "Trying fallback insertion..."

        $content = $content -replace `
            '("📊 Sovereign Analytics Engine",)',
            '$1`r`n        "🏗️ Sovereign CAD",'

        Write-Host "Fallback CAD navigation insertion completed." -ForegroundColor Green
    }

}
else {

    Write-Host "CAD navigation item already exists." -ForegroundColor Yellow
}

# --------------------------------------------------
# 5. REMOVE OLD DISCONNECTED CAD BLOCK
# --------------------------------------------------

$oldCadPattern = '(?ms)\r?\n?# ==========================================\r?\n?# Sovereign CAD Workspace Integration\r?\n?# ==========================================\r?\n?if ''menu_selection'' in locals\(\) and menu_selection == "Sovereign CAD":.*?\r?\n?else:\r?\n?\s*# Fallback or standard flow check\r?\n?\s*pass'

if ($content -match $oldCadPattern) {

    $content = [regex]::Replace(
        $content,
        $oldCadPattern,
        ''
    )

    Write-Host "Removed disconnected CAD block." -ForegroundColor Green
}
else {

    Write-Host "No disconnected CAD block found, or it was already removed." -ForegroundColor Yellow
}

# --------------------------------------------------
# 6. ADD CAD ROUTE INTO MAIN WORKSPACE ROUTING
# --------------------------------------------------

$cadRoute = @'

    elif menu_selection == "🏗️ Sovereign CAD":
        st.title("🏗️ Sovereign CAD Workspace")
        st.caption("Professional CAD design and engineering workspace")

        try:
            from sovereign_cad.streamlit import render_cad_workspace
            render_cad_workspace()

        except ModuleNotFoundError as e:
            st.error("❌ Sovereign CAD module could not be imported.")
            st.code(str(e))

            st.info("""
The CAD files may exist in the repository, but Python cannot find
the required Sovereign CAD Streamlit module.

Expected structure:

sovereign_cad/
    __init__.py
    streamlit.py
""")

        except Exception as e:
            st.error("❌ Sovereign CAD workspace failed to load.")
            st.exception(e)

'@

if ($content -notmatch 'elif menu_selection == "🏗️ Sovereign CAD"') {

    $anchor = @'
    elif menu_selection == "📝 Query Log":
'@

    if ($content.Contains($anchor)) {

        $content = $content.Replace(
            $anchor,
            $cadRoute + $anchor
        )

        Write-Host "CAD route added to main application router." -ForegroundColor Green
    }
    else {

        Write-Host "ERROR: Could not locate main routing anchor." -ForegroundColor Red
        Write-Host "Restoring backup..."

        Copy-Item $backup "app.py" -Force

        exit 1
    }

}
else {

    Write-Host "CAD route already exists." -ForegroundColor Yellow
}

# --------------------------------------------------
# 7. WRITE UPDATED APP
# --------------------------------------------------

Set-Content `
    -Path "app.py" `
    -Value $content `
    -Encoding UTF8

Write-Host ""
Write-Host "Updated app.py successfully." -ForegroundColor Green

# --------------------------------------------------
# 8. CHECK CAD PACKAGE
# --------------------------------------------------

Write-Host ""
Write-Host "Checking CAD package structure..." -ForegroundColor Cyan

if (Test-Path "sovereign_cad") {

    Write-Host "Found sovereign_cad directory." -ForegroundColor Green

    Get-ChildItem "sovereign_cad" -Recurse -File |
        Select-Object FullName

}
else {

    Write-Host "WARNING: sovereign_cad directory was NOT found." -ForegroundColor Red
}

# --------------------------------------------------
# 9. CHECK REQUIRED STREAMLIT MODULE
# --------------------------------------------------

Write-Host ""
Write-Host "Checking for CAD Streamlit integration..." -ForegroundColor Cyan

$possibleFiles = @(
    "sovereign_cad\streamlit.py",
    "sovereign_cad\streamlit\__init__.py"
)

$cadStreamlitFound = $false

foreach ($file in $possibleFiles) {

    if (Test-Path $file) {

        Write-Host "FOUND: $file" -ForegroundColor Green
        $cadStreamlitFound = $true
    }
}

if (-not $cadStreamlitFound) {

    Write-Host ""
    Write-Host "WARNING: Expected CAD Streamlit adapter was not found." -ForegroundColor Yellow

    Write-Host "Searching CAD package for render functions..."

    Get-ChildItem "sovereign_cad" -Recurse -Filter "*.py" |
        Select-String `
            -Pattern "def render_.*cad|def render_cad|render_cad_workspace" `
            -CaseSensitive:$false

}

# --------------------------------------------------
# 10. PYTHON SYNTAX CHECK
# --------------------------------------------------

Write-Host ""
Write-Host "Running Python syntax check..." -ForegroundColor Cyan

$pythonCommand = $null

if (Test-Path ".venv\Scripts\python.exe") {

    $pythonCommand = ".\.venv\Scripts\python.exe"

}
elseif (Get-Command python -ErrorAction SilentlyContinue) {

    $pythonCommand = "python"

}

if ($pythonCommand) {

    & $pythonCommand -m py_compile app.py

    if ($LASTEXITCODE -eq 0) {

        Write-Host "SUCCESS: app.py syntax is valid." -ForegroundColor Green

    }
    else {

        Write-Host "ERROR: Python syntax check failed." -ForegroundColor Red
        Write-Host "Restoring backup..."

        Copy-Item $backup "app.py" -Force

        exit 1
    }

}
else {

    Write-Host "WARNING: Python executable not found. Skipping syntax check." -ForegroundColor Yellow
}

# --------------------------------------------------
# 11. SHOW GIT STATUS
# --------------------------------------------------

Write-Host ""
Write-Host "Git status:" -ForegroundColor Cyan

git status

# --------------------------------------------------
# 12. COMMIT CHANGES
# --------------------------------------------------

Write-Host ""
$commit = Read-Host "Commit CAD integration changes to Git? (Y/N)"

if ($commit -match '^[Yy]$') {

    git add app.py

    git commit -m "Integrate Sovereign CAD workspace into Streamlit navigation"

    Write-Host ""
    $push = Read-Host "Push changes to GitHub? (Y/N)"

    if ($push -match '^[Yy]$') {

        git push

        Write-Host ""
        Write-Host "CAD integration pushed to GitHub." -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "==================================================" -ForegroundColor Green
Write-Host " CAD INTEGRATION PROCESS COMPLETE"
Write-Host "==================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next, start the application:"
Write-Host ""
Write-Host "streamlit run app.py" -ForegroundColor Cyan
Write-Host ""