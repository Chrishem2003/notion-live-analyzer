"""Phase 81 — SQLite repository adapter for spatial evidence history."""
from __future__ import annotations
from typing import Any
from nema_agora.spatial_evidence_storage import SpatialEvidenceStore,validate_record
POLICY_VERSION="phase81-v1"
class SQLiteSpatialEvidenceRepository:
    def __init__(self,database_path:str): self.database_path=database_path
    def append(self,record:dict[str,Any])->None:
        validate_record(record)
        SpatialEvidenceStore(self.database_path).append(record)
    def list(self,**filters:Any)->list[dict[str,Any]]:
        allowed={"case_id","candidate_id","observed_at","sequence"}
        if set(filters)-allowed: raise ValueError("UNSUPPORTED_FILTER")
        rows=SpatialEvidenceStore(self.database_path).list(case_id=filters.get("case_id"))
        for key in ("candidate_id","observed_at","sequence"):
            if filters.get(key) is not None: rows=[r for r in rows if r.get(key)==filters[key]]
        return rows
