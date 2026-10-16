
"""
Audit Portal  CHRISHEM Encrypted Submission & Analytics System
Provides:
  1. CHRISHEMSubmissionSystem  Fernet-encrypted student submissions with SQLite
"""
from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# ─── Paths ────────────────────────────────────────────────────────────
APP_DIR = Path(__file__).resolve().parent.parent
DB_PATH = APP_DIR / "research_workspace.db"

# ─── Cryptography for Fernet ─────────────────────────────────────────
try:
    from cryptography.fernet import Fernet, InvalidToken
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False
    Fernet = None
    InvalidToken = Exception

# Legacy static salt is retained only for decrypting existing records.
LEGACY_SALT = b"CHRISHEM_AUDIT_PORTAL_SALT_2024"
KDF_ITERATIONS = 600000
SALT_BYTES = 16


class CryptographyUnavailable(RuntimeError):
    """Raised when secure submission encryption is unavailable."""


def derive_fernet_key(password: str, salt: bytes = LEGACY_SALT) -> bytes:
    """Derive a Fernet key; never fall back to an insecure encoding."""
    if not HAS_CRYPTOGRAPHY:
        raise CryptographyUnavailable(
            "The 'cryptography' package is required for submission encryption."
        )
    if not isinstance(password, str) or not password.strip():
        raise ValueError("A non-empty password is required.")
    if not isinstance(salt, bytes) or len(salt) < 16:
        raise ValueError("A cryptographically secure salt of at least 16 bytes is required.")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=KDF_ITERATIONS,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


def encrypt_text(plaintext: str, password: str) -> str:
    """Encrypt with Fernet and a fresh random salt for every new record."""
    if not isinstance(plaintext, str):
        raise TypeError("Plaintext must be a string.")
    salt = os.urandom(SALT_BYTES)
    token = Fernet(derive_fernet_key(password, salt)).encrypt(plaintext.encode())
    return f"v2:{base64.urlsafe_b64encode(salt).decode()}:{token.decode()}"


def decrypt_text(ciphertext: str, password: str) -> str:
    """Decrypt v2 salted records and legacy Fernet records without exposing internals."""
    if not isinstance(ciphertext, str) or not ciphertext:
        raise ValueError("Ciphertext must be a non-empty string.")
    if not HAS_CRYPTOGRAPHY:
        raise CryptographyUnavailable(
            "The 'cryptography' package is required to decrypt submissions."
        )
    if not isinstance(password, str) or not password.strip():
        raise ValueError("A non-empty password is required.")
    try:
        if ciphertext.startswith("v2:"):
            _, salt_b64, token = ciphertext.split(":", 2)
            salt = base64.urlsafe_b64decode(salt_b64.encode("ascii"))
            if len(salt) != SALT_BYTES:
                raise ValueError("Invalid encrypted-record salt.")
        else:
            # Backward compatibility for records encrypted with the historic fixed salt.
            salt, token = LEGACY_SALT, ciphertext
        return Fernet(derive_fernet_key(password, salt)).decrypt(token.encode()).decode()
    except CryptographyUnavailable:
        raise
    except Exception:
        # Avoid leaking cryptographic implementation details to UI/log output.
        raise ValueError("Decryption failed: incorrect password or invalid ciphertext.") from None


# ═══════════════════════════════════════════════════════════════════════
# 1. SUBMISSION SYSTEM  Encrypted Student → Professor Workflow
# ═══════════════════════════════════════════════════════════════════════
class CHRISHEMSubmissionSystem:
    """SQLite-backed encrypted submission system with blockchain audit trail."""

    def __init__(self, db_path: str | Path = DB_PATH):
        self.db_path = Path(db_path)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        """Create submission tables with blockchain tracking."""
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS portal_submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL DEFAULT 0,
                    student_name TEXT NOT NULL,
                    student_email TEXT DEFAULT '',
                    title TEXT NOT NULL,
                    file_name TEXT DEFAULT '',
                    file_type TEXT DEFAULT '',
                    file_size INTEGER DEFAULT 0,
                    encrypted_content TEXT NOT NULL,
                    content_hash TEXT,
                    status TEXT DEFAULT 'submitted',
                    professor_grade TEXT,
                    professor_score REAL,
                    professor_feedback TEXT,
                    submitted_at REAL NOT NULL,
                    reviewed_at REAL,
                    blockchain_hash TEXT,
                    session_id TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_portal_sub_project
                    ON portal_submissions(project_id);
                CREATE INDEX IF NOT EXISTS idx_portal_sub_student
                    ON portal_submissions(student_name);
                CREATE INDEX IF NOT EXISTS idx_portal_sub_status
                    ON portal_submissions(status);
                CREATE TABLE IF NOT EXISTS portal_audit_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    submission_id INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    previous_status TEXT,
                    new_status TEXT NOT NULL,
                    occurred_at REAL NOT NULL,
                    details_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE INDEX IF NOT EXISTS idx_portal_events_submission
                    ON portal_audit_events(submission_id, event_id);
            """)
            conn.commit()

    @staticmethod
    def _record_portal_event(
        conn: sqlite3.Connection,
        submission_id: int,
        event_type: str,
        previous_status: Optional[str],
        new_status: str,
        occurred_at: float,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Append a non-content event in the same transaction as its state change.

        This improves traceability but is not a tamper-proof ledger and does not
        identify an individual user when the shared professor gate is used.
        """
        conn.execute(
            """INSERT INTO portal_audit_events
               (submission_id, event_type, previous_status, new_status, occurred_at, details_json)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                submission_id,
                event_type,
                previous_status,
                new_status,
                occurred_at,
                json.dumps(details or {}, sort_keys=True),
            ),
        )

    def get_submission_events(self, submission_id: int) -> List[Dict[str, Any]]:
        """Return the chronological event history for one submission."""
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT event_id, submission_id, event_type, previous_status,
                          new_status, occurred_at, details_json
                   FROM portal_audit_events
                   WHERE submission_id = ?
                   ORDER BY event_id ASC""",
                (submission_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def submit(
        self,
        project_id: int,
        student_name: str,
        title: str,
        content: str,
        password: str,
        file_name: str = "",
        file_type: str = "",
        file_size: int = 0,
        student_email: str = "",
    ) -> Dict[str, Any]:
        """Submit encrypted work. Returns submission record."""
        encrypted = encrypt_text(content, password)
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        ts = time.time()

        # Generate blockchain-style hash for this submission
        block_raw = f"{student_name}-{title}-{ts}-{encrypted[:50]}"
        block_hash = hashlib.sha256(block_raw.encode()).hexdigest()

        with self._get_conn() as conn:
            cursor = conn.execute(
                """INSERT INTO portal_submissions
                   (project_id, student_name, student_email, title, file_name, file_type,
                    file_size, encrypted_content, content_hash, status, submitted_at, blockchain_hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'submitted', ?, ?)""",
                (project_id, student_name, student_email, title, file_name, file_type,
                 file_size, encrypted, content_hash, ts, block_hash),
            )
            sub_id = cursor.lastrowid
            self._record_portal_event(
                conn,
                int(sub_id),
                "submission_created",
                None,
                "submitted",
                ts,
                {"integrity_hash": block_hash},
            )
            conn.commit()

        # Record in audit ledger
        try:
            from modules.audit_engine import get_audit_orchestrator
            orch = get_audit_orchestrator(project_id)
            orch.ledger.record_node(
                session_id=f"portal_{project_id}",
                student_id=student_name,
                event_type="STUDENT_SUBMISSION",
                text_snapshot=f"Submitted: {title}",
                payload_metrics=json.dumps({"sub_id": sub_id, "hash": block_hash}),
                project_id=project_id,
            )
        except Exception:
            pass

        return {
            "id": sub_id,
            "blockchain_hash": block_hash,
            "message": "✅ Submission encrypted and stored successfully!",
        }

    def get_submissions(
        self,
        project_id: int = 0,
        student_name: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict]:
        """Get submissions with optional filters."""
        query = "SELECT * FROM portal_submissions WHERE 1=1"
        params = []
        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)
        if student_name:
            query += " AND student_name = ?"
            params.append(student_name)
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY submitted_at DESC"

        with self._get_conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_submission(self, submission_id: int) -> Optional[Dict]:
        """Get a single submission by ID."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM portal_submissions WHERE id = ?", (submission_id,)
            ).fetchone()
        return dict(row) if row else None

    def decrypt_submission(self, submission_id: int, password: str) -> Optional[str]:
        """Decrypt a submission's content."""
        sub = self.get_submission(submission_id)
        if not sub:
            return None
        return decrypt_text(sub["encrypted_content"], password)

    def review(
        self,
        submission_id: int,
        grade: str,
        score: float,
        feedback: str,
        professor_password: str,
    ) -> bool:
        """Professor reviews and grades a submission."""
        if not isinstance(grade, str) or not grade.strip():
            raise ValueError("A non-empty grade is required.")
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise ValueError("Score must be a finite number between 0 and 100.")
        try:
            numeric_score = float(score)
        except (OverflowError, TypeError, ValueError):
            raise ValueError("Score must be a finite number between 0 and 100.") from None
        if not math.isfinite(numeric_score) or not 0 <= numeric_score <= 100:
            raise ValueError("Score must be a finite number between 0 and 100.")
        if not isinstance(feedback, str) or not feedback.strip():
            raise ValueError("Non-empty review feedback is required.")
        if isinstance(submission_id, bool) or not isinstance(submission_id, int) or submission_id < 1:
            return False
        encrypted_feedback = encrypt_text(feedback.strip(), professor_password)
        with self._get_conn() as conn:
            existing = conn.execute(
                "SELECT status FROM portal_submissions WHERE id = ?", (submission_id,)
            ).fetchone()
            if existing is None:
                return False
            reviewed_at = time.time()
            cursor = conn.execute(
                """UPDATE portal_submissions SET
                   status = 'reviewed',
                   professor_grade = ?,
                   professor_score = ?,
                   professor_feedback = ?,
                   reviewed_at = ?
                   WHERE id = ?""",
                (grade.strip(), numeric_score, encrypted_feedback, reviewed_at, submission_id),
            )
            if cursor.rowcount == 1:
                self._record_portal_event(
                    conn,
                    submission_id,
                    "review_saved",
                    str(existing["status"]),
                    "reviewed",
                    reviewed_at,
                    {"grade_recorded": True, "score_recorded": True},
                )
            conn.commit()
        return cursor.rowcount == 1

    def return_for_revision(
        self,
        submission_id: int,
        feedback: str,
        professor_password: str,
    ) -> bool:
        """Return submission with feedback for revision."""
        if not isinstance(feedback, str) or not feedback.strip():
            raise ValueError("Non-empty revision feedback is required.")
        if isinstance(submission_id, bool) or not isinstance(submission_id, int) or submission_id < 1:
            return False
        encrypted_feedback = encrypt_text(feedback.strip(), professor_password)
        with self._get_conn() as conn:
            existing = conn.execute(
                "SELECT status FROM portal_submissions WHERE id = ?", (submission_id,)
            ).fetchone()
            if existing is None:
                return False
            reviewed_at = time.time()
            cursor = conn.execute(
                """UPDATE portal_submissions SET
                   status = 'returned',
                   professor_feedback = ?,
                   reviewed_at = ?
                   WHERE id = ?""",
                (encrypted_feedback, reviewed_at, submission_id),
            )
            if cursor.rowcount == 1:
                self._record_portal_event(
                    conn,
                    submission_id,
                    "returned_for_revision",
                    str(existing["status"]),
                    "returned",
                    reviewed_at,
                    {"feedback_recorded": True},
                )
            conn.commit()
        return cursor.rowcount == 1

    def get_student_stats(self, project_id: int, student_name: str) -> Dict[str, Any]:
        """Get submission statistics for a student."""
        with self._get_conn() as conn:
            total = conn.execute(
                "SELECT COUNT(*) as c FROM portal_submissions WHERE project_id=? AND student_name=?",
                (project_id, student_name),
            ).fetchone()["c"]
            reviewed = conn.execute(
                "SELECT COUNT(*) as c FROM portal_submissions WHERE project_id=? AND student_name=? AND status='reviewed'",
                (project_id, student_name),
            ).fetchone()["c"]
            pending = conn.execute(
                "SELECT COUNT(*) as c FROM portal_submissions WHERE project_id=? AND student_name=? AND status='submitted'",
                (project_id, student_name),
            ).fetchone()["c"]
            avg_score = conn.execute(
                "SELECT AVG(professor_score) as avg FROM portal_submissions "
                "WHERE project_id=? AND student_name=? AND professor_score IS NOT NULL",
                (project_id, student_name),
            ).fetchone()["avg"]

        return {
            "student_name": student_name,
            "project_id": project_id,
            "total_submissions": total,
            "reviewed": reviewed,
            "pending": pending,
            "returned": total - reviewed - pending,
            "average_score": round(float(avg_score), 2) if avg_score is not None else None,
        }

