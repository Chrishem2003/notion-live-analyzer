"""Guard the Render blueprint against unsafe ephemeral API ledger defaults."""
from pathlib import Path


def test_render_api_ledger_defaults_require_persistent_storage():
    root = Path(__file__).resolve().parents[1]
    blueprint = (root / "render.yaml").read_text(encoding="utf-8")

    assert "/var/data/research_run_idempotency.sqlite3" in blueprint
    assert "/tmp/research_run_idempotency.sqlite3" not in blueprint
    assert "RESEARCH_RUN_ALLOW_EPHEMERAL_LEDGER" in blueprint
    assert 'value: "false"' in blueprint
