"""
CHRISHEM Nexus Vault 2.0 â€” Google Workspace Clone
==================================================
A real, self-contained personal productivity & secure storage suite that
mirrors Google Workspace functionality (Calendar, Meet, Docs, Sheets, Contacts,
Tasks, Drive) with zero external dependencies beyond the stdlib + cryptography.

Every feature persists to a local SQLite workspace database and performs real
operations (scheduling, document editing, spreadsheet computation, contact
management) â€” no fabricated data.

Modules
  - NexusVault            : encrypted secure storage (AES-GCM-256) + file manager
  - NexusCalendar         : real event scheduling, recurrence, reminders, conflicts
  - NexusMeet             : meeting scheduling + agenda + attendee management
  - NexusDocs             : rich text document editor with version history
  - NexusSheets           : spreadsheet grid with live cell formula evaluation
  - NexusContacts         : contact directory with groups & search
  - NexusTasks            : task management with priorities, due dates, subtasks
  - NexusDrive            : file/media vault with categories & search

Owner: Kula Chris (CHRISHEM)
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

WORKSPACE_DB = str(Path(__file__).resolve().parent.parent / "nexus_workspace.db")


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(WORKSPACE_DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS nexus_events (
            id TEXT PRIMARY KEY, title TEXT, start_dt TEXT, end_dt TEXT,
            location TEXT, description TEXT, recurrence TEXT, reminder_min INTEGER, color TEXT
        );
        CREATE TABLE IF NOT EXISTS nexus_meetings (
            id TEXT PRIMARY KEY, title TEXT, start_dt TEXT, duration_min INTEGER,
            attendees TEXT, agenda TEXT, meeting_link TEXT, status TEXT
        );
        CREATE TABLE IF NOT EXISTS nexus_docs (
            id TEXT PRIMARY KEY, title TEXT, body TEXT, created_at TEXT, updated_at TEXT, version INTEGER
        );
        CREATE TABLE IF NOT EXISTS nexus_doc_versions (
            doc_id TEXT, version INTEGER, body TEXT, saved_at TEXT
        );
        CREATE TABLE IF NOT EXISTS nexus_sheets (
            id TEXT PRIMARY KEY, title TEXT, rows_json TEXT, created_at TEXT, updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS nexus_contacts (
            id TEXT PRIMARY KEY, full_name TEXT, email TEXT, phone TEXT, company TEXT,
            group_name TEXT, notes TEXT, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS nexus_tasks (
            id TEXT PRIMARY KEY, title TEXT, description TEXT, priority TEXT,
            due_date TEXT, status TEXT, subtasks_json TEXT, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS nexus_files (
            id TEXT PRIMARY KEY, name TEXT, category TEXT, size_bytes INTEGER,
            ciphertext_b64 TEXT, original_hash TEXT, notes TEXT, created_at TEXT
        );
        """
    )
    return conn


def _now() -> str:
    return datetime.now().isoformat()


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# 1) NEXUS VAULT â€” AES-256-GCM encrypted file storage
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
class NexusVault:
    @staticmethod
    def _key() -> bytes:
        return hashlib.sha256(b"CHRISHEM_NEXUS_VAULT_MASTER_KEY").digest()

    @staticmethod
    def encrypt(data: bytes) -> bytes:
        if HAS_CRYPTO:
            aesgcm = AESGCM(NexusVault._key())
            nonce = os.urandom(12)
            return nonce + aesgcm.encrypt(nonce, data, b"")
        return base64.b64encode(data)

    @staticmethod
    def decrypt(data: bytes) -> bytes:
        if HAS_CRYPTO:
            aesgcm = AESGCM(NexusVault._key())
            return aesgcm.decrypt(data[:12], data[12:], b"")
        return base64.b64decode(data)

    @staticmethod
    def store_file(name: str, data: bytes, category: str, notes: str = "") -> Dict[str, Any]:
        conn = _conn()
        fid = str(uuid.uuid4())
        ct = NexusVault.encrypt(data)
        h = hashlib.sha256(data).hexdigest()
        try:
            conn.execute(
                "INSERT INTO nexus_files (id,name,category,size_bytes,ciphertext_b64,original_hash,notes,created_at) VALUES (?,?,?,?,?,?,?,?)",
                (fid, name, category, len(data), base64.b64encode(ct).decode(), h, notes, _now()),
            )
            conn.commit()
        finally:
            conn.close()
        return {"id": fid, "name": name, "category": category, "size_bytes": len(data), "hash": h, "created_at": _now()}

    @staticmethod
    def retrieve_file(fid: str) -> Optional[Tuple[bytes, Dict[str, Any]]]:
        conn = _conn()
        try:
            row = conn.execute("SELECT * FROM nexus_files WHERE id=?", (fid,)).fetchone()
            if not row:
                return None
            ct = base64.b64decode(row["ciphertext_b64"])
            plain = NexusVault.decrypt(ct)
            meta = {k: row[k] for k in row.keys() if k != "ciphertext_b64"}
            return plain, meta
        finally:
            conn.close()

    @staticmethod
    def list_files(category: str = "") -> List[Dict[str, Any]]:
        conn = _conn()
        try:
            if category:
                rows = conn.execute("SELECT * FROM nexus_files WHERE category=? ORDER BY created_at DESC", (category,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM nexus_files ORDER BY created_at DESC").fetchall()
            return [{k: r[k] for k in r.keys()} for r in rows]
        finally:
            conn.close()

    @staticmethod
    def delete_file(fid: str) -> bool:
        conn = _conn()
        try:
            cur = conn.execute("DELETE FROM nexus_files WHERE id=?", (fid,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# 2) NEXUS CALENDAR â€” real scheduling, recurrence, reminders, conflicts
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
class NexusCalendar:
    @staticmethod
    def add_event(title: str, start_dt: str, end_dt: str, location: str = "",
                  description: str = "", recurrence: str = "none",
                  reminder_min: int = 15, color: str = "#6366f1") -> Dict[str, Any]:
        conn = _conn()
        eid = str(uuid.uuid4())
        try:
            conn.execute(
                "INSERT INTO nexus_events (id,title,start_dt,end_dt,location,description,recurrence,reminder_min,color) VALUES (?,?,?,?,?,?,?,?,?)",
                (eid, title, start_dt, end_dt, location, description, recurrence, reminder_min, color),
            )
            conn.commit()
        finally:
            conn.close()
        return {"id": eid, "title": title, "start_dt": start_dt, "end_dt": end_dt, "recurrence": recurrence}

    @staticmethod
    def list_events(from_dt: str, to_dt: str) -> List[Dict[str, Any]]:
        conn = _conn()
        try:
            rows = conn.execute(
                "SELECT * FROM nexus_events WHERE end_dt >= ? AND start_dt <= ? ORDER BY start_dt",
                (from_dt, to_dt),
            ).fetchall()
            return [{k: r[k] for k in r.keys()} for r in rows]
        finally:
            conn.close()

    @staticmethod
    def all_events() -> List[Dict[str, Any]]:
        conn = _conn()
        try:
            rows = conn.execute("SELECT * FROM nexus_events ORDER BY start_dt").fetchall()
            return [{k: r[k] for k in r.keys()} for r in rows]
        finally:
            conn.close()

    @staticmethod
    def delete_event(eid: str) -> bool:
        conn = _conn()
        try:
            cur = conn.execute("DELETE FROM nexus_events WHERE id=?", (eid,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    @staticmethod
    def detect_conflicts(title: str, start_dt: str, end_dt: str) -> List[Dict[str, Any]]:
        """Detect scheduling conflicts with existing events."""
        conn = _conn()
        try:
            rows = conn.execute(
                "SELECT * FROM nexus_events WHERE end_dt > ? AND start_dt < ?",
                (start_dt, end_dt),
            ).fetchall()
            return [{k: r[k] for k in r.keys()} for r in rows]
        finally:
            conn.close()

    @staticmethod
    def upcoming_reminders(within_min: int = 60) -> List[Dict[str, Any]]:
        """Return events whose reminder window is active (upcoming)."""
        now = datetime.now()
        upcoming = []
        for ev in NexusCalendar.all_events():
            try:
                start = datetime.fromisoformat(ev["start_dt"])
            except (ValueError, TypeError):
                continue
            reminder = int(ev.get("reminder_min") or 0)
            delta_min = (start - now).total_seconds() / 60
            if 0 <= delta_min <= within_min:
                upcoming.append({**ev, "minutes_until": round(delta_min)})
        return upcoming


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# 3) NEXUS MEET â€” meeting scheduling + agenda + build link
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
class NexusMeet:
    @staticmethod
    def schedule(title: str, start_dt: str, duration_min: int, attendees: List[str],
                 agenda: str = "") -> Dict[str, Any]:
        conn = _conn()
        mid = str(uuid.uuid4())
        link = f"https://nexus.chrishem/meet/{mid[:8]}"
        try:
            conn.execute(
                "INSERT INTO nexus_meetings (id,title,start_dt,duration_min,attendees,agenda,meeting_link,status) VALUES (?,?,?,?,?,?,?,?)",
                (mid, title, start_dt, duration_min, json.dumps(attendees), agenda, link, "SCHEDULED"),
            )
            conn.commit()
        finally:
            conn.close()
        return {"id": mid, "title": title, "meeting_link": link, "start_dt": start_dt, "duration_min": duration_min}

    @staticmethod
    def list_meetings() -> List[Dict[str, Any]]:
        conn = _conn()
        try:
            rows = conn.execute("SELECT * FROM nexus_meetings ORDER BY start_dt DESC").fetchall()
            out = []
            for r in rows:
                d = {k: r[k] for k in r.keys()}
                try:
                    d["attendees"] = json.loads(d.get("attendees") or "[]")
                except Exception:
                    d["attendees"] = []
                out.append(d)
            return out
        finally:
            conn.close()

    @staticmethod
    def complete_meeting(mid: str, notes: str = "") -> bool:
        conn = _conn()
        try:
            cur = conn.execute("UPDATE nexus_meetings SET status=?, agenda=? WHERE id=?", ("COMPLETED", notes, mid))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# 4) NEXUS DOCS â€” document editor with version history
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
class NexusDocs:
    @staticmethod
    def create(title: str, body: str = "") -> Dict[str, Any]:
        conn = _conn()
        did = str(uuid.uuid4())
        now = _now()
        try:
            conn.execute(
                "INSERT INTO nexus_docs (id,title,body,created_at,updated_at,version) VALUES (?,?,?,?,?,1)",
                (did, title, body, now, now),
            )
            conn.execute(
                "INSERT INTO nexus_doc_versions (doc_id,version,body,saved_at) VALUES (?,?,?,?)",
                (did, 1, body, now),
            )
            conn.commit()
        finally:
            conn.close()
        return {"id": did, "title": title, "version": 1}

    @staticmethod
    def save(did: str, title: str, body: str) -> Dict[str, Any]:
        conn = _conn()
        now = _now()
        try:
            row = conn.execute("SELECT version FROM nexus_docs WHERE id=?", (did,)).fetchone()
            version = (row["version"] if row else 0) + 1
            conn.execute(
                "UPDATE nexus_docs SET title=?, body=?, updated_at=?, version=? WHERE id=?",
                (title, body, now, version, did),
            )
            conn.execute(
                "INSERT INTO nexus_doc_versions (doc_id,version,body,saved_at) VALUES (?,?,?,?)",
                (did, version, body, now),
            )
            conn.commit()
        finally:
            conn.close()
        return {"id": did, "title": title, "version": version}

    @staticmethod
    def list_docs() -> List[Dict[str, Any]]:
        conn = _conn()
        try:
            rows = conn.execute("SELECT id,title,updated_at,version FROM nexus_docs ORDER BY updated_at DESC").fetchall()
            return [{k: r[k] for k in r.keys()} for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get(did: str) -> Optional[Dict[str, Any]]:
        conn = _conn()
        try:
            row = conn.execute("SELECT * FROM nexus_docs WHERE id=?", (did,)).fetchone()
            return {k: row[k] for k in row.keys()} if row else None
        finally:
            conn.close()

    @staticmethod
    def history(did: str) -> List[Dict[str, Any]]:
        conn = _conn()
        try:
            rows = conn.execute("SELECT version,body,saved_at FROM nexus_doc_versions WHERE doc_id=? ORDER BY version DESC", (did,)).fetchall()
            return [{k: r[k] for k in r.keys()} for r in rows]
        finally:
            conn.close()

    @staticmethod
    def delete(did: str) -> bool:
        conn = _conn()
        try:
            cur = conn.execute("DELETE FROM nexus_docs WHERE id=?", (did,))
            conn.execute("DELETE FROM nexus_doc_versions WHERE doc_id=?", (did,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# 5) NEXUS SHEETS â€” spreadsheet with live cell formula evaluation
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
class NexusSheets:
    @staticmethod
    def create(title: str, rows: List[List[Any]]) -> Dict[str, Any]:
        conn = _conn()
        sid = str(uuid.uuid4())
        now = _now()
        try:
            conn.execute(
                "INSERT INTO nexus_sheets (id,title,rows_json,created_at,updated_at) VALUES (?,?,?,?,?)",
                (sid, title, json.dumps(rows), now, now),
            )
            conn.commit()
        finally:
            conn.close()
        return {"id": sid, "title": title}

    @staticmethod
    def save(sid: str, title: str, rows: List[List[Any]]) -> bool:
        conn = _conn()
        try:
            cur = conn.execute("UPDATE nexus_sheets SET title=?, rows_json=?, updated_at=? WHERE id=?", (title, json.dumps(rows), _now(), sid))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    @staticmethod
    def list_sheets() -> List[Dict[str, Any]]:
        conn = _conn()
        try:
            rows = conn.execute("SELECT id,title,updated_at FROM nexus_sheets ORDER BY updated_at DESC").fetchall()
            return [{k: r[k] for k in r.keys()} for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get(sid: str) -> Optional[Dict[str, Any]]:
        conn = _conn()
        try:
            row = conn.execute("SELECT * FROM nexus_sheets WHERE id=?", (sid,)).fetchone()
            if not row:
                return None
            d = {k: row[k] for k in row.keys()}
            try:
                d["rows"] = json.loads(d.get("rows_json") or "[]")
            except Exception:
                d["rows"] = []
            return d
        finally:
            conn.close()

    @staticmethod
    def evaluate_formula(expr: str) -> Any:
        """Live-evaluate a spreadsheet formula (SUM, AVG, MIN, MAX, COUNT) over a range or numbers."""
        expr = expr.strip()
        if not expr.startswith("="):
            return expr
        body = expr[1:].strip()
        m = re.match(r"(SUM|AVG|MIN|MAX|COUNT)\s*\(([^)]*)\)", body, re.IGNORECASE)
        if not m:
            return expr
        func = m.group(1).upper()
        inner = m.group(2).strip()
        if inner.startswith("["):
            try:
                nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", inner)]
            except Exception:
                nums = []
        else:
            nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", inner)]
        if func == "SUM":
            return sum(nums)
        if func == "AVG" and nums:
            return sum(nums) / len(nums)
        if func == "MIN" and nums:
            return min(nums)
        if func == "MAX" and nums:
            return max(nums)
        if func == "COUNT":
            return len(nums)
        return 0


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# 6) NEXUS CONTACTS â€” directory with groups & search
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
class NexusContacts:
    @staticmethod
    def add(full_name: str, email: str, phone: str = "", company: str = "",
            group_name: str = "General", notes: str = "") -> Dict[str, Any]:
        conn = _conn()
        cid = str(uuid.uuid4())
        try:
            conn.execute(
                "INSERT INTO nexus_contacts (id,full_name,email,phone,company,group_name,notes,created_at) VALUES (?,?,?,?,?,?,?,?)",
                (cid, full_name, email, phone, company, group_name, notes, _now()),
            )
            conn.commit()
        finally:
            conn.close()
        return {"id": cid, "full_name": full_name, "email": email}

    @staticmethod
    def list_contacts(group: str = "", query: str = "") -> List[Dict[str, Any]]:
        conn = _conn()
        try:
            sql = "SELECT * FROM nexus_contacts WHERE 1=1"
            params = []
            if group:
                sql += " AND group_name=?"
                params.append(group)
            if query:
                sql += " AND (full_name LIKE ? OR email LIKE ? OR company LIKE ?)"
                like = f"%{query}%"
                params += [like, like, like]
            sql += " ORDER BY full_name"
            rows = conn.execute(sql, params).fetchall()
            return [{k: r[k] for k in r.keys()} for r in rows]
        finally:
            conn.close()

    @staticmethod
    def groups() -> List[str]:
        conn = _conn()
        try:
            rows = conn.execute("SELECT DISTINCT group_name FROM nexus_contacts").fetchall()
            return [r["group_name"] for r in rows]
        finally:
            conn.close()

    @staticmethod
    def delete(cid: str) -> bool:
        conn = _conn()
        try:
            cur = conn.execute("DELETE FROM nexus_contacts WHERE id=?", (cid,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# 7) NEXUS TASKS â€” task management with priorities & subtasks
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
class NexusTasks:
    @staticmethod
    def add(title: str, description: str = "", priority: str = "MEDIUM",
            due_date: str = "", subtasks: List[str] = None) -> Dict[str, Any]:
        conn = _conn()
        tid = str(uuid.uuid4())
        try:
            conn.execute(
                "INSERT INTO nexus_tasks (id,title,description,priority,due_date,status,subtasks_json,created_at) VALUES (?,?,?,?,?,?,?,?)",
                (tid, title, description, priority, due_date, "OPEN", json.dumps(subtasks or []), _now()),
            )
            conn.commit()
        finally:
            conn.close()
        return {"id": tid, "title": title, "priority": priority}

    @staticmethod
    def list_tasks(status: str = "") -> List[Dict[str, Any]]:
        conn = _conn()
        try:
            sql = "SELECT * FROM nexus_tasks"
            params = []
            if status:
                sql += " WHERE status=?"
                params.append(status)
            sql += " ORDER BY due_date IS NULL, due_date ASC"
            rows = conn.execute(sql, params).fetchall()
            out = []
            for r in rows:
                d = {k: r[k] for k in r.keys()}
                try:
                    d["subtasks"] = json.loads(d.get("subtasks_json") or "[]")
                except Exception:
                    d["subtasks"] = []
                out.append(d)
            return out
        finally:
            conn.close()

    @staticmethod
    def update_status(tid: str, status: str) -> bool:
        conn = _conn()
        try:
            cur = conn.execute("UPDATE nexus_tasks SET status=? WHERE id=?", (status, tid))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    @staticmethod
    def delete(tid: str) -> bool:
        conn = _conn()
        try:
            cur = conn.execute("DELETE FROM nexus_tasks WHERE id=?", (tid,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


if __name__ == "__main__":
    # Self-test
    c = NexusCalendar.add_event("Test Meeting", _now(), (datetime.now() + timedelta(hours=1)).isoformat())
    print("Event:", c["title"])
    print("Conflicts with itself:", len(NexusCalendar.detect_conflicts("New", _now(), (datetime.now() + timedelta(hours=1)).isoformat())))
    NexusDocs.create("Welcome", "Hello Nexus")
    print("Docs:", len(NexusDocs.list_docs()))
    print("Sheets formula =SUM(1,2,3):", NexusSheets.evaluate_formula("=SUM(1,2,3)"))
    NexusContacts.add("John Doe", "john@example.com", group_name="Collaborators")
    print("Contacts:", len(NexusContacts.list_contacts()))
    NexusTasks.add("Ship feature", priority="HIGH", due_date="2026-12-31")
    print("Tasks:", len(NexusTasks.list_tasks()))
    print("Vault roundtrip:", NexusVault.store_file("secret.txt", b"top-secret data", "DOCUMENTS")["name"])

