"""Authenticated local gateway for a remote Ollama host.

Keep Ollama bound to localhost:11434. Run this gateway on localhost:11435 and
publish only the gateway through a TLS tunnel. OLLAMA_GATEWAY_TOKEN must be
a random secret of at least 32 characters and must match OLLAMA_API_KEY on
the calling service. Do not expose Ollama's native port directly.
"""
from __future__ import annotations

import hmac
import os

import httpx
from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.responses import Response

app = FastAPI(title="Ollama Private Gateway", docs_url=None, redoc_url=None)
UPSTREAM = os.environ.get("OLLAMA_UPSTREAM_URL", "http://127.0.0.1:11434").rstrip("/")
MAX_BODY_BYTES = 1_000_000


def _configured_token() -> str:
    token = os.environ.get("OLLAMA_GATEWAY_TOKEN", "").strip()
    if len(token) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gateway token is not configured securely.",
        )
    return token


def _authorize(authorization: str | None) -> None:
    expected = f"Bearer {_configured_token()}"
    if not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid gateway credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def _proxy(method: str, path: str, request: Request) -> Response:
    body = await request.body()
    if len(body) > MAX_BODY_BYTES:
        raise HTTPException(status_code=413, detail="Request body too large.")
    timeout = httpx.Timeout(90.0, connect=3.0)
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            upstream = await client.request(
                method,
                f"{UPSTREAM}{path}",
                content=body if method != "GET" else None,
                headers={"Content-Type": request.headers.get("content-type", "application/json")},
            )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Ollama request timed out.") from None
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Ollama upstream is unavailable.") from None
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type", "application/json"),
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/tags")
async def tags(request: Request, authorization: str | None = Header(default=None)) -> Response:
    _authorize(authorization)
    return await _proxy("GET", "/api/tags", request)


@app.post("/api/chat")
async def chat(request: Request, authorization: str | None = Header(default=None)) -> Response:
    _authorize(authorization)
    return await _proxy("POST", "/api/chat", request)


@app.post("/api/generate")
async def generate(request: Request, authorization: str | None = Header(default=None)) -> Response:
    _authorize(authorization)
    return await _proxy("POST", "/api/generate", request)


@app.post("/api/embeddings")
async def embeddings(request: Request, authorization: str | None = Header(default=None)) -> Response:
    _authorize(authorization)
    return await _proxy("POST", "/api/embeddings", request)
