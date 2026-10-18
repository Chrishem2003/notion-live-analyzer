"""Phase 27 deployment health checks; no external integration is assumed."""
from __future__ import annotations

from dataclasses import dataclass
import importlib
from pathlib import Path
from typing import Iterable

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
            checks.append(HealthCheck(f"import:{name}", False, f"{type(exc).__name__}: {exc}"))
        else:
            checks.append(HealthCheck(f"import:{name}", True, "imported"))
    return checks

def _path_check() -> HealthCheck:
    try:
        package = importlib.import_module("nema_agora")
        package_path = Path(package.__file__ or "")
    except Exception as exc:
        return HealthCheck("package-path", False, f"{type(exc).__name__}: {exc}")
    if not package_path.exists():
        return HealthCheck("package-path", False, "package path does not exist")
    return HealthCheck("package-path", True, str(package_path))

def run_health_checks() -> tuple[HealthCheck, ...]:
    checks = _module_checks()
    checks.append(_path_check())
    checks.append(HealthCheck("policy-version", bool(POLICY_VERSION.strip()), POLICY_VERSION))
    return tuple(checks)

def health_summary(checks: Iterable[HealthCheck] | None = None) -> dict:
    resolved = tuple(checks) if checks is not None else run_health_checks()
    return {
        "healthy": all(check.ok for check in resolved),
        "checks": [{"name": c.name, "ok": c.ok, "detail": c.detail} for c in resolved],
        "policy_version": POLICY_VERSION,
        "decision_notice": (
            "Deployment health only; does not establish environmental truth, "
            "NEMA authorization, regulatory status, production approval, "
            "enforcement, or emergency response."
        ),
    }
