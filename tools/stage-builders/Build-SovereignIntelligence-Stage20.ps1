$ErrorActionPreference = "Stop"

$Repo = "D:\notion-live-analyzer"
$Python = "$Repo\.venv\Scripts\python.exe"
$Root = "$Repo\sovereign_intelligence"

Write-Host "============================================================"
Write-Host " SOVEREIGN INTELLIGENCE — STAGE 20"
Write-Host " MULTI-AGENT COLLABORATION"
Write-Host "============================================================"

if (!(Test-Path $Python)) {
    throw "Python executable not found: $Python"
}

if (!(Test-Path $Root)) {
    throw "Sovereign Intelligence package not found."
}

Write-Host "Existing Stage 20 implementation detected."
Write-Host "Running integrity verification..."

& $Python -m compileall -q $Root

if ($LASTEXITCODE -ne 0) {
    throw "Stage 20 compilation failed."
}

Write-Host "STAGE20_COMPILE_OK"

& $Python -c "from sovereign_intelligence.execution import MultiAgentTeam,TeamResult,AgentContribution; print('STAGE20_IMPORT_OK')"

if ($LASTEXITCODE -ne 0) {
    throw "Stage 20 import failed."
}

& $Python -c "from sovereign_intelligence.execution import MultiAgentTeam; t=MultiAgentTeam(); a=t.select_agents('Find the latest information about a Python repository'); assert len(a) >= 2; print('STAGE20_SELECTION_OK')"

if ($LASTEXITCODE -ne 0) {
    throw "Stage 20 selection failed."
}

& $Python -c "from sovereign_intelligence.execution import MultiAgentTeam; t=MultiAgentTeam(); r=t.execute('calculate a mathematical percentage',lambda agent,role,prompt: agent+' solved the problem'); assert r.success; assert r.successful_agents > 0; assert r.consensus.strip(); print('STAGE20_TEAM_EXECUTION_OK')"

if ($LASTEXITCODE -ne 0) {
    throw "Stage 20 team execution failed."
}

& $Python -c "from sovereign_intelligence import SovereignBrain; b=SovereignBrain(); assert hasattr(b,'solve'); print('STAGE20_BRAIN_COMPATIBILITY_OK')"

if ($LASTEXITCODE -ne 0) {
    throw "Stage 20 brain compatibility failed."
}

Write-Host ""
Write-Host "============================================================"
Write-Host " STAGE 20 VERIFIED"
Write-Host "============================================================"
Write-Host "SOVEREIGN_STAGE20_INTEGRITY_OK"
