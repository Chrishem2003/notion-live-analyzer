"""Phase 64 — human review outcomes and append-only audit binding for spatial candidates."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib,json,re,sqlite3
from typing import Any,Mapping
POLICY_VERSION="phase64-v1"
OUTCOMES=frozenset({"CONFIRMED_CHANGE","NOT_CONFIRMED","INSUFFICIENT_EVIDENCE","ESCALATED"})
_ALLOWED_ROLES=frozenset({"reviewer","coordinator","admin"})
_ID_RE=re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_SHA_RE=re.compile(r"^[0-9a-f]{64}$")
def fingerprint(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()).hexdigest()
def _id(v:Any,n:str)->str:
    if not isinstance(v,str) or not _ID_RE.fullmatch(v.strip()):raise ValueError(f"{n} must be a stable non-identifying ID.")
    return v.strip()
def _sha(v:Any,n:str)->str:
    v=str(v).strip().lower()
    if not _SHA_RE.fullmatch(v):raise ValueError(f"{n} must be a lowercase SHA-256 fingerprint.")
    return v
def validate_review_input(item:Mapping[str,Any],reviewer_id:str,role:str,outcome:str,notes:str="")->dict[str,Any]:
    f=[]
    if not isinstance(item,Mapping):f.append("INVALID_QUEUE_ITEM")
    else:
        if item.get("queue_state")!="QUEUED":f.append("QUEUE_ITEM_NOT_QUEUED")
        for k in ("review_item_id","candidate_id","record_fingerprint"):
            try:_id(item.get(k),k) if k!="record_fingerprint" else _sha(item.get(k),k)
            except ValueError:f.append(f"INVALID_{k.upper()}")
    try:_id(reviewer_id,"reviewer_id")
    except ValueError:f.append("INVALID_REVIEWER_ID")
    if role not in _ALLOWED_ROLES:f.append("UNAUTHORIZED_REVIEWER_ROLE")
    if outcome not in OUTCOMES:f.append("UNSUPPORTED_REVIEW_OUTCOME")
    if not isinstance(notes,str) or len(notes)>2000:f.append("INVALID_REVIEW_NOTES")
    return {"policy_version":POLICY_VERSION,"state":"CONTROL_REQUIRED" if f else "VALID","findings":[{"code":x} for x in f]}
def build_review_event(*,item:Mapping[str,Any],reviewer_id:str,role:str,outcome:str,notes:str="",reviewed_at:str|None=None)->dict[str,Any]:
    check=validate_review_input(item,reviewer_id,role,outcome,notes)
    if check["state"]!="VALID":return check
    event={"policy_version":POLICY_VERSION,"review_event_id":"","review_item_id":item["review_item_id"],"candidate_id":item["candidate_id"],
           "source_queue_fingerprint":item["record_fingerprint"],"reviewer_id":_id(reviewer_id,"reviewer_id"),"reviewer_role":role,
           "outcome":outcome,"notes":notes,"reviewed_at":reviewed_at or datetime.now(timezone.utc).isoformat(),
           "audit_event_type":"SPATIAL_CHANGE_HUMAN_REVIEW","human_decision":True,
           "interpretation":{"environmental_conclusion":None,"regulatory_conclusion":None,"violation":None,"enforcement_action":None}}
    event["review_event_id"]=f"SPATIAL-REVIEW-{fingerprint({k:v for k,v in event.items() if k!='review_event_id'})[:24]}"
    event["event_fingerprint"]=fingerprint(event)
    return event
class SpatialChangeReviewAuditRegistry:
    """Append-only audit ledger for explicit human spatial-review outcomes."""
    def __init__(self,database_path:str):
        self.database_path=str(database_path).strip()
        if not self.database_path:raise ValueError("Explicit database path required.")
        with sqlite3.connect(self.database_path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS spatial_change_review_audit (
                review_event_id TEXT PRIMARY KEY,review_item_id TEXT NOT NULL,candidate_id TEXT NOT NULL,
                source_queue_fingerprint TEXT NOT NULL,reviewer_id TEXT NOT NULL,reviewer_role TEXT NOT NULL,
                outcome TEXT NOT NULL,notes TEXT NOT NULL,reviewed_at TEXT NOT NULL,audit_event_type TEXT NOT NULL,
                human_decision INTEGER NOT NULL,event_fingerprint TEXT NOT NULL,policy_version TEXT NOT NULL)""")
            db.execute("""CREATE UNIQUE INDEX IF NOT EXISTS uq_spatial_review_event_item ON spatial_change_review_audit(review_item_id)""")
            db.execute("""CREATE TRIGGER IF NOT EXISTS spatial_review_audit_no_update BEFORE UPDATE ON spatial_change_review_audit BEGIN SELECT RAISE(ABORT,'spatial review audit is append-only'); END""")
            db.execute("""CREATE TRIGGER IF NOT EXISTS spatial_review_audit_no_delete BEFORE DELETE ON spatial_change_review_audit BEGIN SELECT RAISE(ABORT,'spatial review audit is append-only'); END""")
    def record(self,**kwargs)->dict[str,Any]:
        event=build_review_event(**kwargs)
        if event["state"]=="CONTROL_REQUIRED":return event
        vals=(event["review_event_id"],event["review_item_id"],event["candidate_id"],event["source_queue_fingerprint"],event["reviewer_id"],event["reviewer_role"],event["outcome"],event["notes"],event["reviewed_at"],event["audit_event_type"],1,event["event_fingerprint"],event["policy_version"])
        with sqlite3.connect(self.database_path) as db:
            try:db.execute("INSERT INTO spatial_change_review_audit VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",vals)
            except sqlite3.IntegrityError as e:raise ValueError("REVIEW_ALREADY_RECORDED: queue item has an immutable review outcome.") from e
        return event
    def list(self,limit:int=500)->list[dict[str,Any]]:
        with sqlite3.connect(self.database_path) as db:
            db.row_factory=sqlite3.Row
            return [dict(r) for r in db.execute("SELECT * FROM spatial_change_review_audit ORDER BY reviewed_at DESC,review_event_id DESC LIMIT ?",(max(1,min(int(limit),5000)),)).fetchall()]
def bind_review_to_audit(*,database_path:str,item:Mapping[str,Any],reviewer_id:str,role:str,outcome:str,notes:str="",reviewed_at:str|None=None)->dict[str,Any]:
    return SpatialChangeReviewAuditRegistry(database_path).record(item=item,reviewer_id=reviewer_id,role=role,outcome=outcome,notes=notes,reviewed_at=reviewed_at)
