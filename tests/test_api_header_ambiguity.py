"""Route-level tests for ambiguous raw authentication and idempotency headers.

All values are synthetic. Duplicate-header rejection must happen before any
repository, Supabase, Notion, AI-provider, or other external operation.
"""
import hashlib
import hmac
import importlib

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect


@pytest.fixture
def api_client(monkeypatch):
    monkeypatch.setenv("PLATFORM_API_KEY", "synthetic-platform-key")
    monkeypatch.setenv("USER_JOB_API_ENABLED", "true")
    monkeypatch.setenv("RESEARCH_RUN_WRITEBACK_ENABLED", "false")
    monkeypatch.setenv("SUPABASE_URL", "")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "")
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "synthetic-webhook-secret")

    import api_server

    api_server = importlib.reload(api_server)
    client = TestClient(api_server.app, raise_server_exceptions=False)
    yield api_server, client
    client.close()
    api_server.app.dependency_overrides.clear()


def _duplicate(name: str, value: str):
    return [(name, value), (name, value)]


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        (
            "POST",
            "/api/v1/research-runs",
            {
                "run_id": "synthetic-header-test",
                "run_name": "Synthetic header contract",
                "project_page_id": "synthetic-project",
                "protocol_page_id": "synthetic-protocol",
            },
        ),
        ("POST", "/api/v1/jobs", {"prompt": "synthetic service job"}),
        ("GET", "/api/v1/intelligence/providers", None),
        ("GET", "/api/v1/nema/cases", None),
    ],
)
def test_duplicate_service_key_fields_are_rejected_across_routers(api_client, method, path, body):
    _, client = api_client
    headers = _duplicate("X-API-Key", "synthetic-platform-key")
    if body is None:
        response = client.request(method, path, headers=headers)
    else:
        response = client.request(method, path, headers=headers, json=body)

    assert response.status_code == 401, response.text
    assert "synthetic-platform-key" not in response.text


@pytest.mark.parametrize(
    ("path", "body", "expected_detail"),
    [
        (
            "/api/v1/automations/draft",
            {"description": "Synthetic duplicate bearer header test"},
            "A valid user bearer token is required.",
        ),
        (
            "/api/v1/user-jobs",
            {"prompt": "Synthetic duplicate bearer header test"},
            "Missing bearer token.",
        ),
    ],
)
def test_duplicate_bearer_fields_are_rejected_before_identity_lookup(api_client, path, body, expected_detail):
    _, client = api_client
    headers = _duplicate("Authorization", "Bearer synthetic-user-token")
    response = client.post(path, headers=headers, json=body)

    assert response.status_code == 401, response.text
    assert response.json()["detail"] == expected_detail
    assert "synthetic-user-token" not in response.text


def test_service_job_rejects_duplicate_idempotency_fields_before_repository(api_client, monkeypatch):
    _, client = api_client
    import platform_jobs.api as service_jobs

    def unexpected_repository():
        pytest.fail("Repository must not be constructed for duplicate Idempotency-Key fields.")

    monkeypatch.setattr(service_jobs, "SupabaseJobRepository", unexpected_repository)
    headers = [
        ("X-API-Key", "synthetic-platform-key"),
        ("Idempotency-Key", "synthetic-job-key"),
        ("Idempotency-Key", "synthetic-job-key"),
    ]
    response = client.post("/api/v1/jobs", headers=headers, json={"prompt": "synthetic job"})

    assert response.status_code == 400, response.text
    assert response.json()["detail"] == "Exactly one Idempotency-Key header is required."
    assert "synthetic-job-key" not in response.text


def test_user_job_rejects_duplicate_idempotency_fields_before_repository(api_client, monkeypatch):
    api_server, client = api_client
    import platform_jobs.user_api as user_jobs

    def unexpected_repository():
        pytest.fail("Repository must not be constructed for duplicate Idempotency-Key fields.")

    monkeypatch.setattr(user_jobs, "SupabaseJobRepository", unexpected_repository)
    monkeypatch.setitem(
        api_server.app.dependency_overrides,
        user_jobs._verified_user,
        lambda: {"id": "00000000-0000-0000-0000-000000000001", "email": ""},
    )
    headers = [
        ("Idempotency-Key", "synthetic-user-job-key"),
        ("Idempotency-Key", "synthetic-user-job-key"),
    ]
    response = client.post("/api/v1/user-jobs", headers=headers, json={"prompt": "synthetic user job"})

    assert response.status_code == 400, response.text
    assert response.json()["detail"] == "Exactly one Idempotency-Key header is required."
    assert "synthetic-user-job-key" not in response.text



def _synthetic_github_signature(body: bytes) -> str:
    digest = hmac.new(
        b"synthetic-webhook-secret",
        body,
        hashlib.sha256,
    ).hexdigest()
    return "sha256=" + digest


def test_github_webhook_rejects_duplicate_signature_fields(api_client):
    _, client = api_client
    body = b'{"action":"ping"}'
    signature = _synthetic_github_signature(body)
    headers = [
        ("X-Hub-Signature-256", signature),
        ("X-Hub-Signature-256", signature),
        ("X-GitHub-Event", "ping"),
    ]

    response = client.post("/api/v1/webhooks/github", content=body, headers=headers)

    assert response.status_code == 401, response.text
    assert signature not in response.text


def test_github_webhook_rejects_ambiguous_event_fields(api_client):
    _, client = api_client
    body = b'{"action":"ping"}'
    headers = [
        ("X-Hub-Signature-256", _synthetic_github_signature(body)),
        ("X-GitHub-Event", "ping"),
        ("X-GitHub-Event", "push"),
    ]

    response = client.post("/api/v1/webhooks/github", content=body, headers=headers)

    assert response.status_code == 400, response.text
    assert response.json()["detail"] == "Ambiguous GitHub event header."



@pytest.mark.parametrize(
    "path",
    [
        "/ws/chat/synthetic-room",
        "/ws/docs/synthetic-document",
        "/ws/meet/synthetic-room",
    ],
)
def test_websocket_routes_reject_duplicate_token_query_values(api_client, monkeypatch, path):
    api_server, client = api_client

    def unexpected_token_verification(token):
        pytest.fail("Token verification must not run when the token query parameter is duplicated.")

    monkeypatch.setattr(api_server, "verify_chat_token", unexpected_token_verification)
    url = (
        path
        + "?token=synthetic-websocket-token"
        + "&token=synthetic-websocket-token"
    )
    disconnect = None
    try:
        with client.websocket_connect(url) as websocket:
            try:
                websocket.receive_text()
            except WebSocketDisconnect as exc:
                disconnect = exc
    except WebSocketDisconnect as exc:
        disconnect = exc

    assert disconnect is not None, "WebSocket should close before accepting an ambiguous token."
    assert disconnect.code == 4401
