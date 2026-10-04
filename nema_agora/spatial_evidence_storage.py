from __future__ import annotations
import hashlib,json,re,sqlite3
from typing import Any,Mapping
POLICY_VERSION="phase68-v1"
ID_RE=re.compile(r"^[A-Za-z0-9._:-]{1,128}$"); SHA_RE=re.compile(r"^[0-9a-f]{64}$")
def fingerprint(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()).hexdigest()
def _id(v:Any)->bool:return isinstance(v,str) and bool(ID_RE.fullmatch(v.strip()))
def _sha(v:Any)->bool:return isinstance(v,str) and bool(SHA_RE.fullmatch(v.strip().lower()))
def validate_record(r:Mapping[str,Any])->dict[str,Any]:
 f=[]
 if not isinstance(r,Mapping):return {"state":"CONTROL_REQUIRED","findings":[{"code":"INVALID_RECORD"}]}
 for k in ("record_id","case_id","candidate_id"):
  if not _id(r.get(k)):f.append({"code":f"INVALID_{k.upper()}"})
 for k in ("record_fingerprint","case_fingerprint"):
  if not _sha(r.get(k)):f.append({"code":f"INVALID_{k.upper()}"})
 return {"state":"CONTROL_REQUIRED" if f else "VALID","findings":f}
class SpatialEvidenceStore:
 def __init__(self,database_path:str):
  self.database_path=str(database_path).strip()
  if not self.database_path:raise ValueError("Explicit database path required.")
  with sqlite3.connect(self.database_path) as db:
   db.execute("""CREATE TABLE IF NOT EXISTS spatial_evidence_history(
   record_id TEXT PRIMARY KEY,case_id TEXT NOT NULL,candidate_id TEXT NOT NULL,observed_at TEXT NOT NULL,sequence INTEGER NOT NULL,
   previous_record_fingerprint TEXT,case_fingerprint TEXT NOT NULL,spatial_identity_json TEXT NOT NULL,review_outcome TEXT,
   provenance_json TEXT NOT NULL,record_fingerprint TEXT NOT NULL UNIQUE,policy_version TEXT NOT NULL)""")
   db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_spatial_history_case_sequence ON spatial_evidence_history(case_id,sequence)")
   db.execute("CREATE TRIGGER IF NOT EXISTS spatial_history_no_update BEFORE UPDATE ON spatial_evidence_history BEGIN SELECT RAISE(ABORT,'spatial evidence history is append-only'); END")
   db.execute("CREATE TRIGGER IF NOT EXISTS spatial_history_no_delete BEFORE DELETE ON spatial_evidence_history BEGIN SELECT RAISE(ABORT,'spatial evidence history is append-only'); END")
 def append(self,record:Mapping[str,Any])->dict[str,Any]:
  check=validate_record(record)
  if check["state"]!="VALID":return {"policy_version":POLICY_VERSION,"state":"CONTROL_REQUIRED","findings":check["findings"]}
  cols=("record_id","case_id","candidate_id","observed_at","sequence","previous_record_fingerprint","case_fingerprint","spatial_identity_json","review_outcome","provenance_json","record_fingerprint","policy_version")
  vals=(record["record_id"],record["case_id"],record["candidate_id"],record["observed_at"],record["sequence"],record.get("previous_record_fingerprint"),record["case_fingerprint"],json.dumps(record["spatial_identity"],sort_keys=True,separators=(",",":")),record.get("review_outcome"),json.dumps(record["provenance"],sort_keys=True,separators=(",",":")),record["record_fingerprint"],POLICY_VERSION)
  try:
   with sqlite3.connect(self.database_path) as db:db.execute("INSERT INTO spatial_evidence_history VALUES ("+",".join("?" for _ in cols)+")",vals)
  except sqlite3.IntegrityError as e:raise ValueError("EVIDENCE_RECORD_CONFLICT") from e
  return {"policy_version":POLICY_VERSION,"state":"STORED","record_id":record["record_id"],"record_fingerprint":record["record_fingerprint"]}
 def list(self,case_id:str|None=None,limit:int=500)->list[dict[str,Any]]:
  q="SELECT * FROM spatial_evidence_history";args=[]
  if case_id is not None:q+=" WHERE case_id = ?";args.append(case_id)
  q+=" ORDER BY observed_at ASC, sequence ASC, record_id ASC LIMIT ?";args.append(max(1,min(int(limit),5000)))
  with sqlite3.connect(self.database_path) as db:
   db.row_factory=sqlite3.Row;rows=db.execute(q,args).fetchall()
  out=[]
  for x in rows:
   d=dict(x);d["spatial_identity"]=json.loads(d.pop("spatial_identity_json"));d["provenance"]=json.loads(d.pop("provenance_json"));out.append(d)
  return out
