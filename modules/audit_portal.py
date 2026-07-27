"""
Audit Portal — CHRISHEM Encrypted Submission & Analytics System
Provides:
  1. CHRISHEMSubmissionSystem — Fernet-encrypted student submissions with SQLite
"""
from __future__ import annotations

import base64
import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# ─── Paths ────────────────────────────────────────────────────────────
APP_DIR = Path(__file__).resolve().parent.parent
DB_PATH = APP_DIR / "research_workspace.db"

# ─── Cryptography for Fernet ─────────────────────────────────────────
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False
    Fernet = None

CHRISHEM_SALT = b"CHRISHEM_AUDIT_PORTAL_SALT_2024"


def derive_fernet_key(password: str) -> bytes:
    """Derive a 32-byte Fernet key from a password."""
    if not HAS_CRYPTOGRAPHY:
        return hashlib.sha256(password.encode() + CHRISHEM_SALT).digest()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=CHRISHEM_SALT,
        iterations=600000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


def encrypt_text(plaintext: str, password: str) -> str:
    """Encrypt text using Fernet. Falls back to base64 if cryptography missing."""
    if not HAS_CRYPTOGRAPHY:
        return base64.b64encode(plaintext.encode()).decode()
    f = Fernet(derive_fernet_key(password))
    return f.encrypt(plaintext.encode()).decode()


def decrypt_text(ciphertext: str, password: str) -> str:
    """Decrypt Fernet-encrypted text."""
    if not HAS_CRYPTOGRAPHY:
        try:
            return base64.b64decode(ciphertext.encode()).decode()
        except Exception:
            return "[Decryption failed: cryptography package required]"
    try:
        f = Fernet(derive_fernet_key(password))
        return f.decrypt(ciphertext.encode()).decode()
    except Exception as e:
        return f"[🔒 Decryption failed: {str(e)}]"


# ═══════════════════════════════════════════════════════════════════════
# 1. SUBMISSION SYSTEM — Encrypted Student → Professor Workflow
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
            """)
            conn.commit()

    def submit(
        self,
        project_id: int,
        student_name: str,
        title: str,
        content: str,
        password: str = "CHRISHEM",
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
            conn.commit()
            sub_id = cursor.lastrowid

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
        professor_password: str = "CHRISHEM",
    ) -> bool:
        """Professor reviews and grades a submission."""
        encrypted_feedback = encrypt_text(feedback, professor_password)
        with self._get_conn() as conn:
            conn.execute(
                """UPDATE portal_submissions SET
                   status = 'reviewed',
                   professor_grade = ?,
                   professor_score = ?,
                   professor_feedback = ?,
                   reviewed_at = ?
                   WHERE id = ?""",
                (grade, score, encrypted_feedback, time.time(), submission_id),
            )
            conn.commit()
        return True

    def return_for_revision(
        self,
        submission_id: int,
        feedback: str,
        professor_password: str = "CHRISHEM",
    ) -> bool:
        """Return submission with feedback for revision."""
        encrypted_feedback = encrypt_text(feedback, professor_password)
        with self._get_conn() as conn:
            conn.execute(
                """UPDATE portal_submissions SET
                   status = 'returned',
                   professor_feedback = ?,
                   reviewed_at = ?
                   WHERE id = ?""",
                (encrypted_feedback, time.time(), submission_id),
            )
            conn.commit()
        return True

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
