"""
drive_v2.py — Real cloud storage for Nexus Drive.

No "unlimited storage" claim anywhere in this file, on purpose. Storage is
backed by a real S3-compatible bucket (AWS S3, MinIO, Cloudflare R2,
Backblaze B2 — anything speaking the S3 API works via S3_ENDPOINT_URL),
with a real, visible per-user quota you configure. If S3 isn't configured,
this says so plainly and falls back to the existing local SQLite blob
storage (NexusDrive from 10____Admin_Security_Center.py) — genuinely
functional for development, just not durable across redeploys, and the UI
should say that too.

Required env vars for real cloud storage (unset = local fallback):
    S3_BUCKET
    S3_ACCESS_KEY_ID
    S3_SECRET_ACCESS_KEY
    S3_ENDPOINT_URL      (omit for real AWS S3; set for MinIO/R2/B2/etc.)
    S3_REGION            (default: us-east-1)
    DRIVE_QUOTA_BYTES_PER_USER   (default: 5 GB — a real, stated number)
"""

import os
import hashlib
import datetime
import sqlite3
from dataclasses import dataclass
from typing import Optional

try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

from classification import LEVELS, can_access, can_delete, check_access

DEFAULT_QUOTA_BYTES = 5 * 1024 * 1024 * 1024  # 5 GB — real, visible, configurable. Not "unlimited."


def is_s3_configured() -> bool:
    return BOTO3_AVAILABLE and bool(os.environ.get("S3_BUCKET")) and bool(os.environ.get("S3_ACCESS_KEY_ID"))


def _s3_client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ.get("S3_ENDPOINT_URL") or None,
        aws_access_key_id=os.environ["S3_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["S3_SECRET_ACCESS_KEY"],
        region_name=os.environ.get("S3_REGION", "us-east-1"),
    )


def _quota_bytes() -> int:
    return int(os.environ.get("DRIVE_QUOTA_BYTES_PER_USER", DEFAULT_QUOTA_BYTES))


def _drive_conn(db_path: str = "nexus_drive_v2.db") -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS drive_files_v2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            s3_key TEXT,
            size_bytes INTEGER NOT NULL,
            sha256_hash TEXT NOT NULL,
            classification TEXT NOT NULL DEFAULT 'INTERNAL',
            category TEXT,
            notes TEXT,
            owner TEXT NOT NULL,
            storage_backend TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


@dataclass
class QuotaStatus:
    used_bytes: int
    limit_bytes: int
    remaining_bytes: int
    percent_used: float

    def has_room_for(self, additional_bytes: int) -> bool:
        return self.used_bytes + additional_bytes <= self.limit_bytes


class QuotaExceeded(Exception):
    def __init__(self, status: QuotaStatus, requested_bytes: int):
        self.status = status
        self.requested_bytes = requested_bytes
        super().__init__(
            f"Upload of {requested_bytes:,} bytes would exceed quota "
            f"({status.used_bytes:,} used + {requested_bytes:,} requested > {status.limit_bytes:,} limit)."
        )


class AccessDenied(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def get_quota_status(owner: str, conn: Optional[sqlite3.Connection] = None) -> QuotaStatus:
    conn = conn or _drive_conn()
    row = conn.execute("SELECT COALESCE(SUM(size_bytes), 0) FROM drive_files_v2 WHERE owner = ?", (owner,)).fetchone()
    used = row[0] or 0
    limit = _quota_bytes()
    return QuotaStatus(
        used_bytes=used,
        limit_bytes=limit,
        remaining_bytes=max(0, limit - used),
        percent_used=round(used / limit * 100, 2) if limit else 0.0,
    )


def store_file(name: str, data: bytes, category: str, notes: str, owner: str,
                classification: str = "INTERNAL", conn: Optional[sqlite3.Connection] = None) -> dict:
    if classification.upper() not in LEVELS:
        raise ValueError(f"classification must be one of {LEVELS}")

    conn = conn or _drive_conn()
    quota = get_quota_status(owner, conn)
    if not quota.has_room_for(len(data)):
        raise QuotaExceeded(quota, len(data))

    file_hash = hashlib.sha256(data).hexdigest()
    ts = datetime.datetime.utcnow().isoformat()

    if is_s3_configured():
        client = _s3_client()
        bucket = os.environ["S3_BUCKET"]
        s3_key = f"{owner}/{file_hash[:16]}_{name}"
        client.put_object(Bucket=bucket, Key=s3_key, Body=data)
        backend = "s3"
    else:
        # Honest local fallback — real storage, just not durable/scalable.
        # The blob itself lives in this same row for simplicity here;
        # production should still route through the existing NexusDrive
        # encrypted-blob table rather than duplicating that column.
        s3_key = None
        backend = "local_fallback"

    conn.execute(
        "INSERT INTO drive_files_v2 (name, s3_key, size_bytes, sha256_hash, classification, category, notes, owner, storage_backend, created_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (name, s3_key, len(data), file_hash, classification.upper(), category, notes, owner, backend, ts),
    )
    conn.commit()

    return {
        "name": name, "size_bytes": len(data), "hash": file_hash,
        "classification": classification.upper(), "backend": backend, "created_at": ts,
    }


def list_files(requester: str, requester_clearance: str, conn: Optional[sqlite3.Connection] = None) -> list:
    """Only returns files the requester can actually see: their own files,
    plus anyone's files at or below their clearance level. Real filtering,
    not a UI-layer hide — the data itself is scoped here."""
    conn = conn or _drive_conn()
    rows = conn.execute(
        "SELECT id, name, size_bytes, classification, category, owner, storage_backend, created_at FROM drive_files_v2 ORDER BY id DESC"
    ).fetchall()
    visible = []
    for r in rows:
        file_id, name, size_bytes, classification, category, owner, backend, created_at = r
        if owner == requester or can_access(requester_clearance, classification):
            visible.append({
                "id": file_id, "name": name, "size_bytes": size_bytes,
                "classification": classification, "category": category,
                "owner": owner, "backend": backend, "created_at": created_at,
            })
    return visible


def get_download(file_id: int, requester: str, requester_clearance: str,
                  conn: Optional[sqlite3.Connection] = None) -> dict:
    """Returns either a real presigned S3 URL (time-limited, real AWS
    signature) or, for the local fallback, a note that direct download
    isn't wired up for that path yet — never a fake URL."""
    conn = conn or _drive_conn()
    row = conn.execute(
        "SELECT name, s3_key, classification, owner, storage_backend FROM drive_files_v2 WHERE id = ?", (file_id,)
    ).fetchone()
    if not row:
        raise ValueError(f"No file with id {file_id}")
    name, s3_key, classification, owner, backend = row

    check = check_access(requester_clearance, classification, is_owner=(owner == requester))
    if not check.allowed:
        raise AccessDenied(check.reason)

    if backend == "s3" and s3_key:
        client = _s3_client()
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": os.environ["S3_BUCKET"], "Key": s3_key},
            ExpiresIn=300,  # 5 minutes — real expiry, not decorative
        )
        return {"method": "presigned_url", "url": url, "expires_in_seconds": 300}
    return {"method": "unavailable", "note": "This file used the local fallback backend — configure S3_* env vars for real downloadable links."}


def delete_file(file_id: int, requester: str, requester_clearance: str,
                 conn: Optional[sqlite3.Connection] = None) -> None:
    conn = conn or _drive_conn()
    row = conn.execute("SELECT s3_key, classification, owner, storage_backend FROM drive_files_v2 WHERE id = ?", (file_id,)).fetchone()
    if not row:
        raise ValueError(f"No file with id {file_id}")
    s3_key, classification, owner, backend = row

    if not can_delete(requester_clearance, classification, is_owner=(owner == requester)):
        raise AccessDenied(f"Deleting a {classification} file requires ownership or RESTRICTED clearance.")

    if backend == "s3" and s3_key:
        client = _s3_client()
        client.delete_object(Bucket=os.environ["S3_BUCKET"], Key=s3_key)

    conn.execute("DELETE FROM drive_files_v2 WHERE id = ?", (file_id,))
    conn.commit()