# Configure local Ollama for this PowerShell session only.
# Safe by design: does not expose Ollama to the internet and does not write secrets.
$ErrorActionPreference = "Stop"
$ollamaUrl = "http://127.0.0.1:11434"
$model = "qwen2.5:3b"

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    throw "Ollama CLI was not found. Install Ollama for Windows from https://ollama.com/download/windows, then reopen PowerShell."
}

try {
    $null = Invoke-RestMethod -Uri "$ollamaUrl/api/tags" -TimeoutSec 3
} catch {
    Write-Host "Ollama API is not responding. Starting the local Ollama service..."
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    $ready = $false
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Seconds 1
        try {
            $null = Invoke-RestMethod -Uri "$ollamaUrl/api/tags" -TimeoutSec 2
            $ready = $true
            break
        } catch {}
    }
    if (-not $ready) {
        throw "Ollama did not become ready at $ollamaUrl. Open Ollama and rerun this script."
    }
}

$models = (ollama list 2>$null | Out-String)
if ($models -notmatch '(?m)^qwen2\.5:3b\s') {
    Write-Host "Downloading $model (first run may take time)..."
    ollama pull $model
    if ($LASTEXITCODE -ne 0) { throw "Failed to download $model." }
}

# These variables apply only to this PowerShell window and child processes.
$env:OLLAMA_BASE_URL = $ollamaUrl
$env:OLLAMA_MODEL = $model
$env:SOVEREIGN_AI_PROVIDER = "ollama"
$env:SOVEREIGN_AI_MODEL = $model

$payload = @{
    model = $model
    messages = @(@{ role = "user"; content = "Reply with exactly: OLLAMA_OK" })
    stream = $false
} | ConvertTo-Json -Depth 5

$answer = Invoke-RestMethod -Method Post -Uri "$ollamaUrl/api/chat" -ContentType "application/json" -Body $payload -TimeoutSec 180
if (-not $answer.message.content) { throw "Ollama responded without message content." }

Write-Host ""
Write-Host "Ollama is ready: $ollamaUrl"
Write-Host "Model: $($answer.model)"
Write-Host "Smoke-test reply: $($answer.message.content.Trim())"
Write-Host "Provider configured for this PowerShell session: $env:SOVEREIGN_AI_PROVIDER"
Write-Host ""
Write-Host "Next: activate your project venv, then run: python -m streamlit run app.py"
Write-Host "Keep Ollama bound to 127.0.0.1. Do not set OLLAMA_BASE_URL to 0.0.0.0 or expose port 11434 publicly."
