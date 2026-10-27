def test_workspace_exposes_gated_holdout_evaluation():
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1]
        / "pages"
        / "19_NEMA_AGORA_Workspace.py"
    ).read_text(encoding="utf-8")
    assert "Gated holdout evaluation" in source
    assert "Run gated holdout evaluation" in source
    assert "evaluate_holdout_package(" in source
    assert "does not authenticate reviewers or evidence" in source
