"""Phase 27 deployment health checks; no external integration is assumed."""
from __future__ import annotations

from dataclasses import dataclass
import importlib
from pathlib import Path
from typing import Iterable

from nema_agora.backup import integrity_check

POLICY_VERSION = "phase27-v1"

REQUIRED_MODULES = (
    "nema_agora.access",
    "nema_agora.config",
    "nema_agora.storage",
    "nema_agora.service",
    "nema_agora.provenance",
    "nema_agora.reproducibility",
    "nema_agora.demo",
    "nema_agora.recovery",
)

@dataclass(frozen=True)
class HealthCheck:
    name: str
    ok: bool
    detail: str

def _module_checks() -> list[HealthCheck]:
    checks: list[HealthCheck] = []
    for name in REQUIRED_MODULES:
        try:
            importlib.import_module(name)
        except Exception as exc:
            checks.append(HealthCheck(f"import:{name}", False, "module import failed; inspect restricted server logs"))
        else:
            checks.append(HealthCheck(f"import:{name}", True, "imported"))
    return checks

def _path_check() -> HealthCheck:
    try:
        package = importlib.import_module("nema_agora")
        package_path = Path(package.__file__ or "")
    except Exception as exc:
        return HealthCheck("package-path", False, "package path could not be resolved; inspect restricted server logs")
    if not package_path.exists():
        return HealthCheck("package-path", False, "package path does not exist")
    return HealthCheck("package-path", True, "package path available")

def _database_check(database_path: str | Path) -> HealthCheck:
    """Check an explicitly configured existing SQLite database without creating it."""
    try:
        path = Path(database_path).expanduser()
        if not path.is_file():
            return HealthCheck("persistent-database", False, "configured database file is missing")
        if not integrity_check(path):
            return HealthCheck("persistent-database", False, "database integrity check failed")
        return HealthCheck("persistent-database", True, "database integrity verified")
    except (OSError, TypeError, ValueError):
        return HealthCheck("persistent-database", False, "database health could not be verified")


def run_health_checks(database_path: str | Path | None = None) -> tuple[HealthCheck, ...]:
    checks = _module_checks()
    checks.append(_path_check())
    if database_path is not None:
        checks.append(_database_check(database_path))
    checks.append(HealthCheck("policy-version", bool(POLICY_VERSION.strip()), POLICY_VERSION))
    return tuple(checks)

def health_summary(checks: Iterable[HealthCheck] | None = None) -> dict:
    resolved = tuple(checks) if checks is not None else run_health_checks()
    return {
        "healthy": bool(resolved) and all(check.ok for check in resolved),
        "checks": [{"name": c.name, "ok": c.ok, "detail": c.detail} for c in resolved],
        "policy_version": POLICY_VERSION,
        "decision_notice": (
            "Deployment health only; does not establish environmental truth, "
            "NEMA authorization, regulatory status, production approval, "
            "enforcement, or emergency response."
        ),
    }

def deployment_preflight(secrets: object) -> dict:
    """Check deployment configuration shape without exposing values or opening gates.

    A passing preflight only means the required settings are present and
    structurally valid. It does not prove credentials work, a provider can be
    reached, a database is durable, or a deployment is production-approved.
    """
    from collections.abc import Mapping
    from nema_agora.access import ROLE_PERMISSIONS
    from nema_agora.auth import role_bindings_from_secrets
    from nema_agora.config import (
        backup_dir_from_secrets,
        backup_retention_from_secrets,
        database_path_from_secrets,
        mode_from_secrets,
    )

    checks: list[dict[str, object]] = []

    def record(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    if not isinstance(secrets, Mapping):
        record("secrets_mapping", False, "deployment settings are unavailable or malformed")
        return {
            "preflight_passed": False,
            "checks": checks,
            "release_approved": False,
            "production_ready": False,
            "execution_gate": "CLOSED",
        }

    mode = mode_from_secrets(secrets)
    record("mode", mode in {"demo", "persistent"}, "mode validated" if mode in {"demo", "persistent"} else "mode is invalid")

    if mode == "persistent":
        auth = secrets.get("auth", {})
        if not isinstance(auth, Mapping):
            auth = {}
        required_auth_keys = (
            "client_id",
            "client_secret",
            "cookie_secret",
            "redirect_uri",
            "server_metadata_url",
        )
        missing_auth = [key for key in required_auth_keys if not isinstance(auth.get(key), str) or not auth.get(key, "").strip()]
        record(
            "oidc_configuration_shape",
            not missing_auth,
            "required OIDC settings are present" if not missing_auth else "required OIDC settings are missing: " + ", ".join(missing_auth),
        )

        bindings = role_bindings_from_secrets(secrets)
        invalid_bindings = [key for key, role in bindings.items() if role not in ROLE_PERMISSIONS]
        record(
            "server_role_bindings",
            bool(bindings) and not invalid_bindings,
            "server-side role bindings are structurally valid" if bindings and not invalid_bindings else "valid explicit role bindings are required",
        )

        database_path = database_path_from_secrets(secrets)
        record("persistent_database_path", database_path is not None, "database path is configured" if database_path is not None else "database path is missing")

        backup_dir = backup_dir_from_secrets(secrets)
        record("backup_directory", backup_dir is not None, "backup directory is configured" if backup_dir is not None else "backup directory is missing")

        retention = backup_retention_from_secrets(secrets)
        record("backup_retention", retention is not None, "backup retention is within policy" if retention is not None else "backup retention must be an integer from 1 to 3650 days")

    passed = all(item["ok"] for item in checks)
    return {
        "preflight_passed": bool(passed),
        "mode": mode,
        "checks": checks,
        "release_approved": False,
        "production_ready": False,
        "execution_gate": "CLOSED",
        "decision_notice": (
            "Configuration preflight only. Passing does not prove live authentication, "
            "persistent writes, backup recovery, external data access, or institutional approval."
        ),
    }

