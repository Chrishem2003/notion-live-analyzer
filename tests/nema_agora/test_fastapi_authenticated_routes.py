import pytest
from nema_agora.fastapi_authenticated_routes import FASTAPI_AVAILABLE


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI optional")
def test_spatial_query_fails_closed_even_with_bearer_header():
    from fastapi.testclient import TestClient
    from nema_agora.fastapi_authenticated_routes import app

    client = TestClient(app)
    response = client.get(
        "/api/v1/spatial-evidence/query",
        params={
            "request_id": "REQ-87",
            "actor_id": "admin",
            "role": "admin",
            "database_path": "/tmp/attacker-selected.db",
        },
        headers={"Authorization": "Bearer demo"},
    )
    assert response.status_code == 503
    assert "identity verification is not configured" in response.json()["detail"]


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI optional")
def test_health_does_not_claim_query_access_is_enabled():
    from fastapi.testclient import TestClient
    from nema_agora.fastapi_authenticated_routes import app

    response = TestClient(app).get("/api/v1/spatial-evidence/health")
    assert response.status_code == 200
    assert response.json()["query_access"] == "disabled_until_identity_verifier_is_configured"
