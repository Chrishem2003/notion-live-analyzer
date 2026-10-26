def test_workspace_exposes_uploaded_evidence_hash_verification():
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1]
        / "pages"
        / "19_NEMA_AGORA_Workspace.py"
    ).read_text(encoding="utf-8")
    assert "Local evidence-file integrity" in source
    assert "Verify uploaded evidence hashes" in source
    assert "verify_evidence_assets(" in source
    assert "does not prove who created the evidence" in source


def test_workspace_exposes_spatiotemporal_split_audit():
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1]
        / "pages"
        / "19_NEMA_AGORA_Workspace.py"
    ).read_text(encoding="utf-8")
    assert "Spatial and temporal split-separation audit" in source
    assert "Audit spatial/temporal separation" in source
    assert "audit_spatiotemporal_separation(" in source
    assert "conservative warning" in source
