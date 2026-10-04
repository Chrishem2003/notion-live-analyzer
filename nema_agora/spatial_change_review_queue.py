"""Phase 63 — persistent, append-only spatial-change review queue."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib, json, re, sqlite3, math
from typing import Any, Mapping

POLICY_VERSION = "phase63-v1"
QUEUE_STATE = "QUEUED"
_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_TIERS = frozenset({"HIGH", "MEDIUM", "LOW"})

def fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")).hexdigest()

def _id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value.strip()):
        raise ValueError(f"{label} must be a stable non-identifying ID.")
    return value.strip()

def _sha(value: Any, label: str) -> str:
    value = str(value).strip().lower()
    if not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{label} must be a lowercase SHA-256 fingerprint.")
    return value

def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))

def validate_scored_candidate(scored: Mapping[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    if not isinstance(scored, Mapping):
        return {"policy_version": POLICY_VERSION, "state": "CONTROL_REQUIRED", "findings": [{"code": "INVALID_SCORED_CANDIDATE"}]}
    if scored.get("state") != "REVIEW_PRIORITY_ASSIGNED":
        findings.append({"code": "SCORING_NOT_COMPLETE"})
    try:
        candidate_id = _id(scored.get("candidate_id"), "candidate_id")
    except ValueError:
        candidate_id = ""
        findings.append({"code": "INVALID_CANDIDATE_ID"})
    try:
        source_fp = _sha(scored.get("source_candidate_fingerprint"), "source_candidate_fingerprint")
    except ValueError:
        source_fp = ""
        findings.append({"code": "INVALID_SOURCE_CANDIDATE_FINGERPRINT"})
    if scored.get("tier") not in _ALLOWED_TIERS:
        findings.append({"code": "INVALID_PRIORITY_TIER"})
    if not _finite(scored.get("score")) or not 0 <= float(scored.get("score")) <= 1:
        findings.append({"code": "INVALID_PRIORITY_SCORE"})
    for key in ("spatial", "reason_codes", "components", "weights"):
        if key not in scored:
            findings.append({"code": f"MISSING_SCORING_FIELD_{key.upper()}"})
    spatial = scored.get("spatial")
    if not isinstance(spatial, Mapping):
        findings.append({"code": "INVALID_SPATIAL_METADATA"})
    else:
        for key in ("aoi_id", "grid_id"):
            try: _id(spatial.get(key), key)
            except ValueError: findings.append({"code": f"INVALID_SPATIAL_{key.upper()}"})
    reasons = scored.get("reason_codes")
    if not isinstance(reasons, list) or not reasons:
        findings.append({"code": "INVALID_REASON_CODES"})
    else:
        for reason in reasons:
            try: _id(reason, "reason_code")
            except ValueError: findings.append({"code": "INVALID_REASON_CODE"})
    components = scored.get("components")
    if not isinstance(components, Mapping):
        findings.append({"code": "INVALID_SCORE_COMPONENTS"})
    else:
        for key in ("ndvi_magnitude", "ndwi_magnitude", "quality", "uncertainty"):
            if not _finite(components.get(key)) or not 0 <= float(components.get(key)) <= 1:
                findings.append({"code": f"INVALID_COMPONENT_{key.upper()}"})
    return {"policy_version": POLICY_VERSION, "state": "CONTROL_REQUIRED" if findings else "VALID",
            "findings": findings, "candidate_id": candidate_id, "source_candidate_fingerprint": source_fp}

def build_review_record(scored: Mapping[str, Any], *, created_at: str | None = None) -> dict[str, Any]:
    check = validate_scored_candidate(scored)
    if check["state"] != "VALID":
        return {"policy_version": POLICY_VERSION, "state": "CONTROL_REQUIRED", "findings": check["findings"]}
    spatial = scored["spatial"]
    record = {
        "policy_version": POLICY_VERSION, "review_item_id": "",
        "candidate_id": check["candidate_id"], "source_candidate_fingerprint": check["source_candidate_fingerprint"],
        "priority_score": round(float(scored["score"]), 6), "priority_tier": scored["tier"],
        "reason_codes": list(scored["reason_codes"]),
        "spatial": {"aoi_id": _id(spatial["aoi_id"], "aoi_id"), "grid_id": _id(spatial["grid_id"], "grid_id")},
        "components": dict(scored["components"]), "weights": dict(scored["weights"]),
        "review_threshold": float(scored.get("review_threshold", 0.5)), "queue_state": QUEUE_STATE,
        "created_at": created_at or datetime.now(timezone.utc).isoformat(), "human_review_required": True,
        "interpretation": {"status": "HUMAN_REVIEW_REQUIRED", "environmental_conclusion": None,
                           "regulatory_conclusion": None, "violation": None, "enforcement_action": None},
    }
    record["review_item_id"] = f"REVIEW-{fingerprint({k:v for k,v in record.items() if k != 'review_item_id'})[:24]}"
    record["fingerprint"] = fingerprint(record)
    return record

class SpatialChangeReviewQueue:
    """SQLite-backed append-only queue. Review state changes are human-governed."""
    def __init__(self, database_path: str):
        self.database_path = str(database_path).strip()
        if not self.database_path: raise ValueError("Explicit database path required.")
        with sqlite3.connect(self.database_path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS spatial_change_review_queue (
                review_item_id TEXT PRIMARY KEY, candidate_id TEXT NOT NULL UNIQUE,
                source_candidate_fingerprint TEXT NOT NULL, priority_score REAL NOT NULL,
                priority_tier TEXT NOT NULL, reason_codes_json TEXT NOT NULL,
                spatial_json TEXT NOT NULL, components_json TEXT NOT NULL,
                weights_json TEXT NOT NULL, review_threshold REAL NOT NULL,
                queue_state TEXT NOT NULL, created_at TEXT NOT NULL,
                human_review_required INTEGER NOT NULL, record_fingerprint TEXT NOT NULL,
                policy_version TEXT NOT NULL)""")
            db.execute("""CREATE TRIGGER IF NOT EXISTS spatial_review_no_update
                BEFORE UPDATE ON spatial_change_review_queue BEGIN
                SELECT RAISE(ABORT,'spatial change review queue is append-only'); END""")
            db.execute("""CREATE TRIGGER IF NOT EXISTS spatial_review_no_delete
                BEFORE DELETE ON spatial_change_review_queue BEGIN
                SELECT RAISE(ABORT,'spatial change review queue is append-only'); END""")

    def enqueue(self, scored: Mapping[str, Any], *, created_at: str | None = None) -> dict[str, Any]:
        record = build_review_record(scored, created_at=created_at)
        if record["state"] == "CONTROL_REQUIRED": return record
        columns = ("review_item_id","candidate_id","source_candidate_fingerprint","priority_score","priority_tier",
                   "reason_codes_json","spatial_json","components_json","weights_json","review_threshold",
                   "queue_state","created_at","human_review_required","record_fingerprint","policy_version")
        values = (record["review_item_id"],record["candidate_id"],record["source_candidate_fingerprint"],record["priority_score"],
                  record["priority_tier"],json.dumps(record["reason_codes"],sort_keys=True,separators=(",",":")),
                  json.dumps(record["spatial"],sort_keys=True,separators=(",",":")),
                  json.dumps(record["components"],sort_keys=True,separators=(",",":")),
                  json.dumps(record["weights"],sort_keys=True,separators=(",",":")),record["review_threshold"],
                  record["queue_state"],record["created_at"],1,record["fingerprint"],record["policy_version"])
        with sqlite3.connect(self.database_path) as db:
            try:
                db.execute(f"INSERT INTO spatial_change_review_queue ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})", values)
            except sqlite3.IntegrityError as exc:
                raise ValueError("REVIEW_ITEM_CONFLICT: candidate already has an immutable queue record.") from exc
        return record

    def list(self, *, limit: int = 500) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 5000))
        with sqlite3.connect(self.database_path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute("SELECT * FROM spatial_change_review_queue ORDER BY created_at DESC, review_item_id DESC LIMIT ?", (limit,)).fetchall()
        output=[]
        for row in rows:
            item=dict(row)
            item["reason_codes"]=json.loads(item.pop("reason_codes_json"))
            item["spatial"]=json.loads(item.pop("spatial_json"))
            item["components"]=json.loads(item.pop("components_json"))
            item["weights"]=json.loads(item.pop("weights_json"))
            item["human_review_required"]=bool(item["human_review_required"])
            output.append(item)
        return output

    def counts(self) -> dict[str, int]:
        rows=self.list(limit=5000)
        return {"total":len(rows),"queued":sum(x["queue_state"]=="QUEUED" for x in rows),
                "human_review_required":sum(x["human_review_required"] for x in rows)}

def queue_scored_candidate(database_path: str, scored: Mapping[str, Any], *, created_at: str | None = None) -> dict[str, Any]:
    return SpatialChangeReviewQueue(database_path).enqueue(scored, created_at=created_at)
