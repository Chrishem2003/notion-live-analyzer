$ErrorActionPreference = "Stop"

$Repo = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Repo ".venv\Scripts\python.exe"

Write-Host ""
Write-Host "============================================="
Write-Host " SOVEREIGN INTELLIGENCE HEALTH CHECK"
Write-Host "============================================="
Write-Host ""

if (-not (Test-Path $Python)) {
    Write-Host "[FAIL] Python environment missing" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Python environment"

& $Python -c "import sovereign_intelligence; print('[OK] sovereign_intelligence import')"

if ($LASTEXITCODE -ne 0) {
    exit 1
}

& $Python -c "from sovereign_intelligence.agents import AgentRegistry; print('[OK] agent registry'); print(AgentRegistry().names())"

& $Python -c "from sovereign_intelligence.providers import ProviderRegistry; print('[OK] provider registry'); print(list(ProviderRegistry.default()._providers.keys()))"

& $Python -c "from sovereign_intelligence.knowledge import chunk_text; print('[OK] knowledge subsystem'); print(len(chunk_text('hello world ' * 500)))"

Write-Host ""
Write-Host "[SUCCESS] Sovereign Intelligence health check passed." -ForegroundColor Green