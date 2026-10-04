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
