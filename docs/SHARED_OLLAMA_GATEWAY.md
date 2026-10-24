# Shared Ollama host: secure zero-cost setup

The platform's shared AI gateway can use the Ollama model running on the Windows development computer, without a per-request model API fee. This is a **best-effort shared host**, not a 24/7 cloud service: the PC, Ollama, gateway, and secure tunnel must remain online.

## Security requirements

- Never expose port `11434` directly.
- Keep Ollama on `http://127.0.0.1:11434`.
- Run `ollama_gateway.py` on `127.0.0.1:11435`.
- Publish only port 11435 through a TLS tunnel.
- Set a random secret of at least 32 characters in `OLLAMA_GATEWAY_TOKEN` on the model host and the same value in `OLLAMA_API_KEY` on the server-side caller.
- Do not put secrets in source code, the UI, browser storage, or chat messages.

## Windows PowerShell

From the repository root, with the app's Python environment activated:

```powershell
$bytes = New-Object byte[] 32
[System.Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
$token = [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+','-').Replace('/','_')
$env:OLLAMA_GATEWAY_TOKEN = $token
$env:OLLAMA_UPSTREAM_URL = "http://127.0.0.1:11434"

ollama list
python -m uvicorn ollama_gateway:app --host 127.0.0.1 --port 11435
```

Keep that terminal open. In a second terminal, create a TLS tunnel whose local target is `http://127.0.0.1:11435`. Prefer a stable hostname. A temporary quick-tunnel URL may change and is only suitable for initial testing.

## No-domain option: temporary Cloudflare Quick Tunnel

A domain is **not required** for the first controlled test. Install `cloudflared` from Cloudflare's official Windows instructions, then in a second PowerShell terminal run:

```powershell
cloudflared tunnel --url http://127.0.0.1:11435
```

Copy the generated `https://….trycloudflare.com` origin. The hostname is temporary and changes when the tunnel is restarted. Keep the terminal open. This is for a short staging test only, not production uptime.

**Important security boundaries:**
- Keep the gateway bound to `127.0.0.1:11435` and Ollama bound to `127.0.0.1:11434`; never tunnel port 11434.
- The Quick Tunnel URL is publicly reachable by anyone who learns it. The gateway's bearer token is therefore mandatory; keep it random, private, and server-side. The public `/health` route reveals only a generic status.
- Do not paste the token into the browser, repository, issue tracker, or chat. Set it only in the Windows process environment and Render's server-side environment settings.
- Cloudflare's optional `--allowed-mail` protection is browser-interactive and cannot be used for the Render service's non-interactive API calls. Do not assume it replaces the gateway bearer token.
- Quick Tunnels are explicitly for development/testing, have no uptime guarantee, and do not support Server-Sent Events (SSE). Confirm the app's non-streaming request path works before testing. Stop the tunnel after the test.

Official docs: [Cloudflare Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/).

## Server-side settings

After the HTTPS tunnel is live, configure the **existing** Render API service's environment variables by merging (not replacing) these values:

- `OLLAMA_BASE_URL`: the HTTPS tunnel origin, no trailing slash and no `/api` suffix.
- `OLLAMA_MODEL`: `qwen2.5:3b`
- `OLLAMA_API_KEY`: the exact same secret used for `OLLAMA_GATEWAY_TOKEN`.

If the Streamlit service calls the provider directly, set the same three variables there too. Keep `SHARED_AI_GATEWAY_ENABLED=false` until the independent security and staging gates in `SHARED_PLATFORM_STAGING_RUNBOOK.md` pass. Do not guess the Render Key Value private URL or enable the gateway without a working distributed quota backend.

## Smoke tests

1. `http://127.0.0.1:11435/health` returns `{"status":"ok"}`.
2. An unauthenticated request to `/api/tags` returns HTTP 401.
3. A request with the correct bearer secret reaches Ollama through the gateway.
4. The deployed provider's **Check Ollama connection** succeeds and a signed-in test account receives a response from the configured model.
5. Stop the tunnel and confirm requests fail safely; do not enable a paid fallback silently.

This setup is suitable for development and controlled pilots. For production, use an always-on host with capacity, network controls, concurrency/rate limits, monitoring, and tested account isolation. Zero model API spend does not mean zero availability risk.
