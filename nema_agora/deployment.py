"""Phase 27 deployment health checks; no external integration is assumed."""
from __future__ import annotations
from dataclasses import dataclass
import importlib

POLICY_VERSION="phase27-v1"
REQUIRED_MODULES=("nema_agora.access","nema_agora.config","nema_agora.storage","nema_agora.service","nema_agora.provenance","nema_agora.reproducibility","nema_agora.demo")

@dataclass(frozen=True)
class HealthCheck:
    name:str
    ok:bool
    detail:str

def run_health_checks():
    checks=[]
    for name in REQUIRED_MODULES:
        try:
            importlib.import_module(name)
            checks.append(HealthCheck("import:"+name,True,"imported"))
        except Exception as exc:
            checks.append(HealthCheck("import:"+name,False,f"{type(exc).__name__}: {exc}"))
    checks.append(HealthCheck("policy-version",bool(POLICY_VERSION),"present"))
    return tuple(checks)

def health_summary(checks=None):
    checks=tuple(checks or run_health_checks())
    return {"healthy":all(c.ok for c in checks),"checks":[{"name":c.name,"ok":c.ok,"detail":c.detail} for c in checks],"policy_version":POLICY_VERSION,
            "decision_notice":"Deployment health only; does not establish environmental truth, NEMA authorization, regulatory status, production approval, enforcement, or emergency response."}
