def test_workspace_exposes_dataset_split_leakage_audit():
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1]
        / "pages"
        / "19_NEMA_AGORA_Workspace.py"
    ).read_text(encoding="utf-8")
    assert "Dataset split leakage audit" in source
    assert "Audit dataset split overlap" in source
    assert "BLOCK_EVALUATION" in source or "BLOCK evaluation" in source
    assert "does not prove complete spatial, temporal" in source
