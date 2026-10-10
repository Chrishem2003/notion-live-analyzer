"""Phase 53 — append-only decision receipt and audit binding."""
from __future__ import annotations
import hashlib,json,re,sqlite3
from typing import Any,Mapping
POLICY_VERSION="phase53-v1"
_ID=re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_DECISIONS={"APPROVE","REJECT","REVOKE","SUPERSEDE"}
def fingerprint(value:Any)->str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()).hexdigest()
def validate_receipt(*,decision:Mapping[str,Any],prepared_package:Mapping[str,Any],current_snapshot:Mapping[str,Any],actor_id:str)->dict[str,Any]:
    failures=[]; did=str(decision.get("decision_id","")).strip(); d=str(decision.get("decision","")).strip().upper()
    actor=str(actor_id).strip()
    if not _ID.fullmatch(did): failures.append("INVALID_DECISION_ID")
    if d not in _DECISIONS: failures.append("UNSUPPORTED_DECISION")
    if not actor: failures.append("ACTOR_REQUIRED")
    if prepared_package.get("decision_status")!="NOT_DECIDED": failures.append("PACKAGE_NOT_UNDECIDED")
    if dict(prepared_package.get("current_snapshot") or {})!=dict(current_snapshot): failures.append("SNAPSHOT_MISMATCH")
    if str(decision.get("reviewer_actor_id","")).strip()!=actor: failures.append("ACTOR_MISMATCH")
    state="READY_FOR_RECEIPT" if not failures else "CONTROL_REQUIRED"
    payload={"decision_id":did,"decision":d,"actor_id":actor,"prepared_package_fingerprint":fingerprint(prepared_package),"current_snapshot":dict(current_snapshot)}
    return {"policy_version":POLICY_VERSION,"state":state,"failures":failures,"receipt":payload,
            "receipt_fingerprint":fingerprint(payload),
            "notice":"A receipt is evidence of an already human-executed lifecycle decision. It is not the authoritative decision record and cannot create, alter or imply governance state."}
class DecisionReceiptRegistry:
    def __init__(self,db:sqlite3.Connection):
        self.db=db; self.db.execute("CREATE TABLE IF NOT EXISTS decision_receipts (receipt_id TEXT PRIMARY KEY, decision_id TEXT NOT NULL, receipt_fingerprint TEXT NOT NULL, payload_json TEXT NOT NULL, created_at TEXT NOT NULL, policy_version TEXT NOT NULL)"); self.db.execute("CREATE TRIGGER IF NOT EXISTS decision_receipts_no_update BEFORE UPDATE ON decision_receipts BEGIN SELECT RAISE(ABORT,'append-only'); END;"); self.db.execute("CREATE TRIGGER IF NOT EXISTS decision_receipts_no_delete BEFORE DELETE ON decision_receipts BEGIN SELECT RAISE(ABORT,'append-only'); END;"); self.db.commit()
    def register(self,*,receipt:Mapping[str,Any],created_at:str)->str:
        rid="RECEIPT-"+fingerprint(receipt)[:24].upper()
        self.db.execute("INSERT INTO decision_receipts VALUES (?,?,?,?,?,?)",(rid,str(receipt["decision_id"]),fingerprint(receipt),json.dumps(dict(receipt),sort_keys=True,separators=(",",":")),str(created_at),POLICY_VERSION)); self.db.commit(); return rid
    def list(self,limit:int=500):
        rows=self.db.execute("SELECT receipt_id,decision_id,receipt_fingerprint,payload_json,created_at,policy_version FROM decision_receipts ORDER BY created_at DESC LIMIT ?",(int(limit),)).fetchall()
        return [{"receipt_id":r[0],"decision_id":r[1],"receipt_fingerprint":r[2],"payload":json.loads(r[3]),"created_at":r[4],"policy_version":r[5]} for r in rows]
