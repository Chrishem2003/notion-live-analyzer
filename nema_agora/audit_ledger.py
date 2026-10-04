"""Phase 34 — append-only, hash-chained audit ledger.

The ledger detects changes to previously recorded entries when verified against a
trusted checkpoint. SQLite triggers prevent ordinary UPDATE/DELETE operations;
this is tamper-evident, not tamper-proof against a privileged database owner.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib, json, sqlite3
from pathlib import Path
from typing import Any

POLICY_VERSION="phase34-v1"
GENESIS_HASH="0"*64

def _canonical(value:Any)->str:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str)

def _hash(value:Any)->str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()

@dataclass(frozen=True)
class LedgerEntry:
    sequence:int
    entry_id:str
    actor_id:str
    event_type:str
    occurred_at:str
    payload:dict[str,Any]
    previous_hash:str
    entry_hash:str
    policy_version:str=POLICY_VERSION
    def to_dict(self): return asdict(self)

class AuditLedger:
    def __init__(self,database_path:str|Path):
        path=str(database_path)
        if not path.strip(): raise ValueError("Explicit database path required.")
        self.database_path=path
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS audit_ledger(
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id TEXT NOT NULL UNIQUE,
                actor_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                previous_hash TEXT NOT NULL,
                entry_hash TEXT NOT NULL UNIQUE,
                policy_version TEXT NOT NULL)""")
            db.execute("""CREATE TRIGGER IF NOT EXISTS audit_ledger_no_update
                BEFORE UPDATE ON audit_ledger BEGIN
                SELECT RAISE(ABORT,'audit ledger is append-only'); END""")
            db.execute("""CREATE TRIGGER IF NOT EXISTS audit_ledger_no_delete
                BEFORE DELETE ON audit_ledger BEGIN
                SELECT RAISE(ABORT,'audit ledger is append-only'); END""")
            db.execute("CREATE TABLE IF NOT EXISTS audit_ledger_checkpoints("
                "checkpoint_id TEXT PRIMARY KEY, sequence INTEGER NOT NULL, "
                "entry_hash TEXT NOT NULL, created_at TEXT NOT NULL, actor_id TEXT NOT NULL)")

    def _connect(self):
        db=sqlite3.connect(self.database_path,timeout=10)
        db.row_factory=sqlite3.Row
        return db

    def append(self,*,entry_id:str,actor_id:str,event_type:str,payload:dict[str,Any],
               occurred_at:str|None=None)->dict[str,Any]:
        for label,value in (("entry_id",entry_id),("actor_id",actor_id),("event_type",event_type)):
            if not isinstance(value,str) or not value.strip() or len(value)>128:
                raise ValueError(f"Valid {label} required.")
        if not isinstance(payload,dict): raise ValueError("payload must be an object.")
        timestamp=occurred_at or datetime.now(timezone.utc).isoformat()
        with self._connect() as db:
            # Acquire the write lock before reading the head so concurrent writers
            # cannot both append entries against the same previous hash.
            db.execute("BEGIN IMMEDIATE")
            row=db.execute("SELECT sequence,entry_hash FROM audit_ledger ORDER BY sequence DESC LIMIT 1").fetchone()
            previous=row["entry_hash"] if row else GENESIS_HASH
            sequence=(row["sequence"]+1) if row else 1
            body={"sequence":sequence,"entry_id":entry_id,"actor_id":actor_id,
                  "event_type":event_type,"occurred_at":timestamp,"payload":payload,
                  "previous_hash":previous,"policy_version":POLICY_VERSION}
            digest=_hash(body)
            db.execute("""INSERT INTO audit_ledger
                (entry_id,actor_id,event_type,occurred_at,payload_json,previous_hash,entry_hash,policy_version)
                VALUES(?,?,?,?,?,?,?,?)""",(entry_id,actor_id,event_type,timestamp,_canonical(payload),previous,digest,POLICY_VERSION))
        return {**body,"entry_hash":digest}

    def list_entries(self,*,limit:int=500)->list[dict[str,Any]]:
        if not isinstance(limit,int) or isinstance(limit,bool) or not 1<=limit<=5000:
            raise ValueError("limit must be between 1 and 5000.")
        with self._connect() as db:
            rows=db.execute("SELECT * FROM audit_ledger ORDER BY sequence LIMIT ?",(limit,)).fetchall()
        return [{"sequence":r["sequence"],"entry_id":r["entry_id"],"actor_id":r["actor_id"],
                 "event_type":r["event_type"],"occurred_at":r["occurred_at"],
                 "payload":json.loads(r["payload_json"]),"previous_hash":r["previous_hash"],
                 "entry_hash":r["entry_hash"],"policy_version":r["policy_version"]} for r in rows]

    def verify(self)->dict[str,Any]:
        # Never label a partial prefix as a valid complete ledger. The bounded
        # verifier fails closed until a streaming verifier is implemented.
        with self._connect() as db:
            total=int(db.execute("SELECT COUNT(*) FROM audit_ledger").fetchone()[0])
        if total>5000:
            return {"valid":False,"entries":total,"verified_entries":0,"head_hash":None,
                    "errors":["VERIFICATION_LIMIT_EXCEEDED"],"policy_version":POLICY_VERSION,
                    "notice":"Ledger exceeds the 5,000-entry verification limit; no partial-validity claim is made."}
        entries=self.list_entries(limit=5000); errors=[]; previous=GENESIS_HASH
        for expected_sequence,e in enumerate(entries,1):
            if e["sequence"]!=expected_sequence: errors.append("SEQUENCE_GAP")
            if e["previous_hash"]!=previous: errors.append("PREVIOUS_HASH_MISMATCH:"+str(e["sequence"]))
            body={k:e[k] for k in ("sequence","entry_id","actor_id","event_type","occurred_at","payload","previous_hash","policy_version")}
            if _hash(body)!=e["entry_hash"]: errors.append("ENTRY_HASH_MISMATCH:"+str(e["sequence"]))
            previous=e["entry_hash"]
        return {"valid":not errors,"entries":total,"verified_entries":len(entries),"head_hash":previous,
                "errors":errors,"policy_version":POLICY_VERSION,
                "notice":"Tamper-evident hash chain only; privileged database/file access may rewrite the ledger and checkpoints must be independently protected."}

    def create_checkpoint(self,*,checkpoint_id:str,actor_id:str)->dict[str,Any]:
        if not checkpoint_id.strip() or not actor_id.strip(): raise ValueError("Checkpoint and actor IDs required.")
        result=self.verify()
        if not result["valid"]: raise ValueError("Cannot checkpoint an invalid ledger.")
        sequence=result["entries"]; head=result["head_hash"]
        timestamp=datetime.now(timezone.utc).isoformat()
        with self._connect() as db:
            db.execute("INSERT INTO audit_ledger_checkpoints VALUES(?,?,?,?,?)",
                (checkpoint_id,sequence,head,timestamp,actor_id))
        return {"checkpoint_id":checkpoint_id,"sequence":sequence,"entry_hash":head,
                "created_at":timestamp,"actor_id":actor_id,"policy_version":POLICY_VERSION}

    def list_checkpoints(self)->list[dict[str,Any]]:
        with self._connect() as db:
            rows=db.execute("SELECT * FROM audit_ledger_checkpoints ORDER BY sequence").fetchall()
        return [dict(r) for r in rows]
