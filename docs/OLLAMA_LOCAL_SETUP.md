# Local Ollama setup (Windows)

This configures Ollama for **local development** of Sovereign Intelligence and the integrated platform. It does not publish the local model to the internet, change Render, write credentials, or modify persistent Windows environment variables.

## Why local and hosted AI are separate

- **Local development:** Streamlit on your PC talks to Ollama at `http://127.0.0.1:11434`. This is the recommended private, no-cloud-key route for the local `qwen2.5:3b` model.
- **Hosted/multi-user service:** Render cannot reach your PC's `127.0.0.1`. Do not configure the hosted API to use this address. Use a provider hosted where the API can reach it, or later use a private authenticated network/tunnel with strict access controls.
- The shared AI gateway remains disabled until authentication, the rate-limit backend, provider configuration, and staging checks are complete.

## One-time setup

1. Install and open Ollama for Windows: https://ollama.com/download/windows
2. Open PowerShell in the repository root.
3. Run:

   ```powershell
   .\scripts\setup_ollama_local.ps1
   ```

   The script checks that Ollama is running, pulls `qwen2.5:3b` if missing, and sends a real test prompt. It sets provider variables only for that PowerShell session.
4. In the same PowerShell window, activate your existing virtual environment and start Streamlit. For example:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   python -m streamlit run app.py
   ```

5. Open the **Sovereign Intelligence** page and select/use Ollama. If Streamlit was already running, stop it with Ctrl+C and restart it from the same configured PowerShell session.

## Troubleshooting

- Check local API: `Invoke-RestMethod http://127.0.0.1:11434/api/tags`
- Check model: `ollama list`
- Pull again if needed: `ollama pull qwen2.5:3b`
- If the model is too slow for your PC, try a smaller Ollama model, then set both `OLLAMA_MODEL` and `SOVEREIGN_AI_MODEL` to the exact installed tag for that session.
- Do not paste API keys, Supabase service-role keys, or Render connection strings into source files, screenshots, or chat.
- Do not expose Ollama port 11434 publicly. Keep the base URL at loopback.

## Production safety

Ollama is a local runtime, not a shared hosted inference service. The shared gateway selects a server-side provider and model from environment configuration; callers cannot override those choices. Keep the gateway disabled until the staging checklist is passed. Automation drafts remain drafts and require human approval; they are not executed by the AI gateway.
