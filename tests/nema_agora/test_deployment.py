from nema_agora.deployment import health_summary, run_health_checks
from nema_agora.reproducibility import build_runtime_manifest, current_git_revision

def test_health_summary_is_fail_closed():
    result=health_summary([type("C",(),{"ok":False,"name":"x","detail":"failed"})()])
    assert result["healthy"] is False

def test_health_checks_include_runtime_modules():
    checks=run_health_checks()
    assert any(c.name=="import:nema_agora.demo" for c in checks)

def test_runtime_manifest_uses_real_deployment_identity_or_fails_closed():
    revision=current_git_revision()
    try:
        manifest=build_runtime_manifest(configuration={"mode":"persistent"})
    except RuntimeError:
        assert not revision
    else:
        assert manifest.git_revision==revision
        assert manifest.secret_values_included is False

def test_deployment_preflight_fails_closed_for_malformed_secrets():
    from nema_agora.deployment import deployment_preflight

    result = deployment_preflight(None)
    assert result["preflight_passed"] is False
    assert result["release_approved"] is False
    assert result["production_ready"] is False
    assert result["execution_gate"] == "CLOSED"


def test_demo_preflight_does_not_claim_production_readiness():
    from nema_agora.deployment import deployment_preflight

    result = deployment_preflight({"nema_agora": {"mode": "demo"}})
    assert result["preflight_passed"] is True
    assert result["mode"] == "demo"
    assert result["release_approved"] is False
    assert result["production_ready"] is False
    assert result["execution_gate"] == "CLOSED"


def test_persistent_preflight_requires_oidc_role_bindings_database_and_backup_config():
    from nema_agora.deployment import deployment_preflight

    result = deployment_preflight({"nema_agora": {"mode": "persistent"}})
    assert result["preflight_passed"] is False
    checks = {item["name"]: item["ok"] for item in result["checks"]}
    assert checks["oidc_configuration_shape"] is False
    assert checks["server_role_bindings"] is False
    assert checks["persistent_database_path"] is False
    assert checks["backup_directory"] is False
    assert checks["backup_retention"] is True
    assert result["execution_gate"] == "CLOSED"


def test_persistent_preflight_accepts_complete_config_shape_without_claiming_live_validation():
    from nema_agora.deployment import deployment_preflight

    settings = {
        "auth": {
            "client_id": "synthetic-client-id",
            "client_secret": "synthetic-client-secret",
            "cookie_secret": "synthetic-cookie-secret",
            "redirect_uri": "https://example.invalid/oauth2callback",
            "server_metadata_url": "https://identity.example.invalid/.well-known/openid-configuration",
        },
        "nema_agora": {
            "mode": "persistent",
            "database_path": "/tmp/nema-agora-test.sqlite3",
            "backup_dir": "/tmp/nema-agora-backups",
            "backup_retention": 30,
            "role_bindings": {"https://issuer.example.invalid|synthetic-subject": "reviewer"},
        },
    }
    result = deployment_preflight(settings)
    assert result["preflight_passed"] is True
    assert all(item["ok"] for item in result["checks"])
    assert result["release_approved"] is False
    assert result["production_ready"] is False
    assert result["execution_gate"] == "CLOSED"
    rendered = repr(result)
    assert "synthetic-client-secret" not in rendered
    assert "synthetic-cookie-secret" not in rendered


def test_persistent_preflight_rejects_unknown_server_role_and_bad_retention():
    from nema_agora.deployment import deployment_preflight

    settings = {
        "auth": {
            "client_id": "id",
            "client_secret": "secret",
            "cookie_secret": "cookie",
            "redirect_uri": "https://example.invalid/oauth2callback",
            "server_metadata_url": "https://identity.example.invalid/.well-known/openid-configuration",
        },
        "nema_agora": {
            "mode": "persistent",
            "database_path": "/tmp/nema.sqlite3",
            "backup_dir": "/tmp/backups",
            "backup_retention": True,
            "role_bindings": {"https://issuer.example.invalid|subject": "superadmin"},
        },
    }
    result = deployment_preflight(settings)
    checks = {item["name"]: item["ok"] for item in result["checks"]}
    assert result["preflight_passed"] is False
    assert checks["server_role_bindings"] is False
    assert checks["backup_retention"] is False
    assert result["release_approved"] is False
    assert result["execution_gate"] == "CLOSED"

