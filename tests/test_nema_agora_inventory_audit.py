"""Regression tests for the static NEMA module inventory tool."""
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_nema_agora_inventory.py"
SPEC = importlib.util.spec_from_file_location("audit_nema_agora_inventory", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_inventory_reports_importers_and_phase_suffix_without_claiming_dead_code(tmp_path):
    package = tmp_path / "nema_agora"
    pages = tmp_path / "pages"
    tests = tmp_path / "tests"
    package.mkdir()
    pages.mkdir()
    tests.mkdir()
    (package / "__init__.py").write_text("from .core import VALUE\n", encoding="utf-8")
    (package / "core.py").write_text("VALUE = 1\n", encoding="utf-8")
    (package / "legacy_phase139.py").write_text("from .core import VALUE\n", encoding="utf-8")
    (pages / "18_NEMA_AGORA.py").write_text("from nema_agora.core import VALUE\n", encoding="utf-8")
    (tests / "test_core.py").write_text(
        "from nema_agora import legacy_phase139\nfrom nema_agora.missing import VALUE\n",
        encoding="utf-8",
    )

    report = MODULE.build_inventory(tmp_path)
    records = {row["module"]: row for row in report["modules"]}

    assert report["module_count"] == 3
    assert records["nema_agora.core"]["static_importer_count"] >= 3
    assert records["nema_agora.legacy_phase139"]["phase_suffixed"] is True
    assert "nema_agora/legacy_phase139.py" in report["phase_suffixed_package_files"]
    assert report["unresolved_nema_imports"] == [
        {"import": "nema_agora.missing", "importers": ["tests.test_core"]}
    ]
    assert "not proof of dead code" in report["warning"]


def test_inventory_fails_clearly_when_package_is_missing(tmp_path):
    try:
        MODULE.build_inventory(tmp_path)
    except FileNotFoundError as exc:
        assert "Expected package directory" in str(exc)
    else:
        raise AssertionError("missing package must fail")
