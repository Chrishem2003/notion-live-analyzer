"""Phase 27 deployment recovery smoke test on an isolated temporary database.

The smoke test never opens or mutates the configured persistent database. It
creates a disposable SQLite database, exercises backup/restore/integrity, and
verifies a small provenance chain.
"""
from __future__ import annotations

from pathlib import Path
import sqlite3
import tempfile

from nema_agora.backup import backup_database, integrity_check, restore_database
from nema_agora.provenance import ProvenanceStore, make_provenance, verify_provenance_chain

POLICY_VERSION = "phase27-v1"


def run_recovery_smoke() -> dict:
    """Exercise backup, restore, integrity, and provenance using only temp files."""
    with tempfile.TemporaryDirectory(prefix="nema_agora_smoke_") as raw_dir:
        root = Path(raw_dir)
        source = root / "source.sqlite3"
        restore_target = root / "restored.sqlite3"
        backups = root / "backups"

        with sqlite3.connect(source) as db:
            db.execute("CREATE TABLE smoke_marker (value TEXT NOT NULL)")
            db.execute("INSERT INTO smoke_marker(value) VALUES ('phase27')")
        source_ok = integrity_check(source)

        backup_path = backup_database(source, backups)
        backup_ok = integrity_check(backup_path)

        restore_database(backup_path, restore_target, confirm_destructive=True)
        restored_ok = integrity_check(restore_target)
        with sqlite3.connect(restore_target) as db:
            marker = db.execute("SELECT value FROM smoke_marker").fetchone()
        data_restored = bool(marker and marker[0] == "phase27")

        provenance_db = root / "provenance.sqlite3"
        store = ProvenanceStore(str(provenance_db))
        first = make_provenance(
            event_type="DEPLOYMENT_MANIFEST",
            event_id="SMOKE-MANIFEST",
            actor_id="deployment-smoke",
            dataset_version="smoke-v1",
            dataset_hash="smoke-dataset",
            evidence={"stage": "manifest"},
        )
        second = make_provenance(
            event_type="CONTROLLED_SHADOW",
            event_id="SMOKE-SHADOW",
            actor_id="deployment-smoke",
            dataset_version="smoke-v1",
            dataset_hash="smoke-dataset",
            parent_ids=(first.provenance_id,),
            evidence={"stage": "shadow"},
        )
        store.save(first)
        store.save(second)
        provenance = verify_provenance_chain(store.list(limit=10))

        checks = {
            "source_integrity": source_ok,
            "backup_integrity": backup_ok,
            "restore_integrity": restored_ok,
            "data_restored": data_restored,
            "provenance_chain": provenance["valid"],
        }
        return {
            "healthy": all(checks.values()),
            "checks": checks,
            "policy_version": POLICY_VERSION,
            "persistent_database_touched": False,
            "decision_notice": (
                "Disposable deployment recovery evidence only; no persistent "
                "database is opened or modified."
            ),
        }
