from nema_agora.reproducibility import build_manifest, manifest_fingerprint, validate_manifest

def test_manifest_is_deterministically_fingerprintable():
    manifest = build_manifest(
        git_revision="abc123",
        policy_versions={"phase24": "phase24-v1"},
        dataset_bindings={"dataset": "sha256:123"},
        configuration={"mode": "persistent", "official_integration": False},
        dependencies={"pytest": "9.1.1"},
        manifest_id="REPRO-TEST",
        generated_at="2026-10-04T10:00:00+03:00",
    )
    assert validate_manifest(manifest)["valid"] is True
    assert len(manifest_fingerprint(manifest)) == 64
    assert manifest.secret_values_included is False

def test_manifest_fingerprint_changes_when_deployment_identity_changes():
    a = build_manifest(git_revision="abc123", configuration={"mode": "persistent"}, manifest_id="A")
    b = build_manifest(git_revision="def456", configuration={"mode": "persistent"}, manifest_id="B")
    assert manifest_fingerprint(a) != manifest_fingerprint(b)

def test_manifest_rejects_empty_revision():
    try:
        build_manifest(git_revision=" ")
    except ValueError as exc:
        assert "git_revision" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
