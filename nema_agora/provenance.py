"""Phase 20 evidence provenance and reproducibility.

Records lineage for governed evaluation/admission/shadow/review evidence.
This metadata describes provenance; it never establishes environmental truth
or regulatory authority.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib, json, sqlite3, uuid
from typing import Any

POLICY_VERSION = "phase20-v1"
EVENT_TYPES = (
    "EVALUATION_RUN", "ANNOTATION_BATCH", "COMPARISON_RUN",
    "MODEL_COMPARISON", "MODEL_ADMISSION", "CONTROLLED_SHADOW",
    "SHADOW_REVIEW", "LIFECYCLE_DECISION", "DEPLOYMENT_MANIFEST",
)

def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()

@dataclass(frozen=True)
class ProvenanceRecord:
    provenance_id: str
    event_type: str
    event_id: str
    actor_id: str
    occurred_at: str
    dataset_version: str
    dataset_hash: str
    model_identity: dict[str, str]
    parent_ids: tuple[str, ...]
    evidence_hash: str
    metadata: dict[str, Any]
    policy_version: str = POLICY_VERSION

    def __post_init__(self) -> None:
        if self.event_type not in EVENT_TYPES:
            raise ValueError("Unsupported provenance event type")
        for name in ("provenance_id","event_id","actor_id","dataset_version","dataset_hash","evidence_hash"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} is required")
        if not isinstance(self.model_identity, dict):
            raise ValueError("model_identity must be a mapping")
        if not isinstance(self.parent_ids, tuple):
            raise ValueError("parent_ids must be a tuple")
        if not isinstance(self.metadata, dict):
            raise ValueError("metadata must be a mapping")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

def make_provenance(*, event_type: str, event_id: str, actor_id: str,
                    dataset_version: str, dataset_hash: str,
                    model_identity: dict[str, str] | None = None,
                    parent_ids: tuple[str, ...] = (),
                    evidence: Any = None, metadata: dict[str, Any] | None = None) -> ProvenanceRecord:
    return ProvenanceRecord(
        provenance_id=f"PROV-{uuid.uuid4().hex[:12].upper()}",
        event_type=event_type,
        event_id=event_id.strip(),
        actor_id=actor_id.strip(),
        occurred_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        dataset_version=dataset_version.strip(),
        dataset_hash=dataset_hash.strip(),
        model_identity=dict(model_identity or {}),
        parent_ids=tuple(parent_ids),
        evidence_hash=fingerprint(evidence if evidence is not None else {}),
        metadata=dict(metadata or {}),
    )

class ProvenanceStore:
    def __init__(self, database_path: str):
        self.database_path = str(database_path)
        with sqlite3.connect(self.database_path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS provenance_records (
                provenance_id TEXT PRIMARY KEY, event_type TEXT NOT NULL, event_id TEXT NOT NULL,
                actor_id TEXT NOT NULL, occurred_at TEXT NOT NULL, dataset_version TEXT NOT NULL,
                dataset_hash TEXT NOT NULL, model_identity_json TEXT NOT NULL,
                parent_ids_json TEXT NOT NULL, evidence_hash TEXT NOT NULL,
                metadata_json TEXT NOT NULL, policy_version TEXT NOT NULL,
                UNIQUE(event_type, event_id)
            )""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_provenance_event ON provenance_records(event_type, occurred_at)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_provenance_dataset ON provenance_records(dataset_version, dataset_hash)")

    def save(self, record: ProvenanceRecord) -> None:
        with sqlite3.connect(self.database_path) as db:
            db.execute("""INSERT INTO provenance_records
                (provenance_id,event_type,event_id,actor_id,occurred_at,dataset_version,dataset_hash,
                 model_identity_json,parent_ids_json,evidence_hash,metadata_json,policy_version)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (record.provenance_id,record.event_type,record.event_id,record.actor_id,record.occurred_at,
                 record.dataset_version,record.dataset_hash,canonical_json(record.model_identity),
                 canonical_json(record.parent_ids),record.evidence_hash,canonical_json(record.metadata),
                 record.policy_version))

    def list(self, *, event_type: str | None = None, event_id: str | None = None,
             limit: int = 500) -> list[dict[str, Any]]:
        safe_limit=max(1,min(int(limit),1000))
        with sqlite3.connect(self.database_path) as db:
            db.row_factory=sqlite3.Row
            where=[]; params=[]
            if event_type: where.append("event_type = ?"); params.append(event_type)
            if event_id: where.append("event_id = ?"); params.append(event_id)
            sql="SELECT * FROM provenance_records"
            if where: sql += " WHERE " + " AND ".join(where)
            sql += " ORDER BY occurred_at DESC, provenance_id DESC LIMIT ?"
            rows=db.execute(sql,(*params,safe_limit)).fetchall()
        out=[]
        for row in rows:
            item=dict(row)
            item["model_identity"]=json.loads(item.pop("model_identity_json"))
            item["parent_ids"]=json.loads(item.pop("parent_ids_json"))
            item["metadata"]=json.loads(item.pop("metadata_json"))
            out.append(item)
        return out

def verify_provenance_chain(records: list[dict[str, Any]]) -> dict[str, Any]:
    ids={str(r.get("provenance_id")) for r in records}
    missing=[]
    for record in records:
        for parent in record.get("parent_ids", []):
            if parent not in ids: missing.append(parent)
    duplicate_events=len(records)!=len({(r.get("event_type"),r.get("event_id")) for r in records})
    return {"records":len(records),"missing_parents":sorted(set(missing)),
            "duplicate_events":duplicate_events,
            "valid":not missing and not duplicate_events,
            "policy_version":POLICY_VERSION}
