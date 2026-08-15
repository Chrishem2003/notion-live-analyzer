<#
.SYNOPSIS
    CHRISHEM Enterprise Intelligence Engine - One-Click Master Launcher
.DESCRIPTION
    Executes an initial cognitive background cycle and launches the Streamlit workspace.
#>
param()

Continue = "Stop"
 = 
Set-Location 

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host " ?? INITIALIZING CHRISHEM SOVEREIGN WORKSPACE" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Cyan

# 1. Run Background Intelligence Verification
Write-Host "[+] Running initial autonomous cognitive cycle..." -ForegroundColor Yellow
python modules/autonomous_background_worker.py

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host " ?? LAUNCHING STREAMLIT ENTERPRISE INTELLIGENCE SUITE" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Cyan

# 2. Launch Streamlit Master Application
streamlit run app.py
