# Local Ollama for Sovereign Intelligence

This configuration is for running the application on the same computer as Ollama. It does not require a cloud AI provider key.

## Environment

Set these variables in the environment used to launch the application:

```dotenv
SOVEREIGN_AI_PROVIDER=ollama
SOVEREIGN_AI_MODEL=qwen2.5:3b
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:3b
```

The explicit `SOVEREIGN_AI_PROVIDER=ollama` setting takes precedence over provider auto-detection. The provider defaults to `qwen2.5:3b` if no model is supplied.

## Windows PowerShell smoke test

Run this in the same environment where the repository is checked out:

```powershell
$env:SOVEREIGN_AI_PROVIDER = "ollama"
$env:SOVEREIGN_AI_MODEL = "qwen2.5:3b"
$env:OLLAMA_BASE_URL = "http://127.0.0.1:11434"
$env:OLLAMA_MODEL = "qwen2.5:3b"

Invoke-RestMethod http://127.0.0.1:11434/api/tags
```

Then run the repository's test suite and the Sovereign Intelligence smoke test before using the provider in the application.

## Deployment boundary

Do not set `OLLAMA_BASE_URL=http://127.0.0.1:11434` in a hosted Render service unless Ollama is running inside that same service. On Render, loopback refers to the Render instance, not a developer's Windows computer. Keep the hosted provider configuration separate; never expose the local Ollama port to the public internet just to connect Render.

## Safety

The provider only performs model inference. It does not execute shell commands or grant the model repository, database, or deployment permissions. Those capabilities must be exposed separately through authenticated, allowlisted tools with authorization and approval checks.
