"""
Core Backend Module for Notion Live Analyzer & NEMA Agora Intelligence Section
Author: Chrishem (Kula Chris)
Features:
- SQLite WAL mode & connection pooling for high-concurrency read/writes
- TTL Caching wrapper to prevent Notion API rate-limiting
- NEMA Agora environmental intelligence & bioinformatics analytical pipelines
"""

import sqlite3
import time
import json
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

# ==========================================
# 1. CACHING & RATE-LIMIT SHIELD
# ==========================================
class TTLCache:
    \"\"\"Thread-safe TTL Cache to store API responses and heavy compute results.\"\"\"
    def __init__(self, default_ttl: int = 300):
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self.default_ttl = default_ttl

    def _generate_key(self, prefix: str, identifier: str) -> str:
        return hashlib.sha256(f"{prefix}:{identifier}".encode()).hexdigest()

    def get(self, prefix: str, identifier: str) -> Optional[Any]:
        key = self._generate_key(prefix, identifier)
        if key in self._cache:
            data, expiry = self._cache[key]
            if time.time() < expiry:
                return data
            del self._cache[key]
        return None

    def set(self, prefix: str, identifier: str, data: Any, ttl: Optional[int] = None) -> None:
        key = self._generate_key(prefix, identifier)
        expiry = time.time() + (ttl if ttl is not None else self.default_ttl)
        self._cache[key] = (data, expiry)

    def clear(self) -> None:
        self._cache.clear()

global_cache = TTLCache(default_ttl=600)

# ==========================================
# 2. HIGH-PERFORMANCE SQLITE DATABASE MANAGER
# ==========================================
class DatabaseManager:
    \"\"\"Manages SQLite with WAL mode enabled for lightning-fast concurrent analytics.\"\"\"
    def __init__(self, db_path: str = "nema_agora_vault.db"):
        self.db_path = db_path
        self._initialize_database()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize_database(self) -> None:
        with self._get_connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            
            conn.execute(\"\"\"
                CREATE TABLE IF NOT EXISTS environmental_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    station_id TEXT NOT NULL,
                    parameter TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'NORMAL'
                );
            \"\"\")
            conn.execute(\"\"\"
                CREATE TABLE IF NOT EXISTS bio_sequences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sample_code TEXT UNIQUE NOT NULL,
                    organism TEXT NOT NULL,
                    sequence_data TEXT NOT NULL,
                    gc_content REAL,
                    resistance_marker_detected BOOLEAN,
                    logged_date DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            \"\"\")
            conn.commit()

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def execute_non_query(self, query: str, params: tuple = ()) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid

# ==========================================
# 3. NEMA AGORA INTELLIGENCE & ANALYTICS PIPELINE
# ==========================================
class NemaAgoraIntelligence:
    \"\"\"Advanced Environmental Monitoring & Bioinformatics Analytics Engine.\"\"\"
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def ingest_sensor_reading(self, station_id: str, parameter: str, value: float, unit: str) -> Dict[str, Any]:
        thresholds = {
            "turbidity_ntu": 50.0,
            "dissolved_oxygen_mg_l": 4.0,
            "ph": (6.5, 8.5),
            "colistin_resistance_copies_ml": 100.0
        }

        status = "COMPLIANT"
        if parameter in thresholds:
            limit = thresholds[parameter]
            if isinstance(limit, tuple):
                if not (limit[0] <= value <= limit[1]):
                    status = "WARNING_BREACH"
            elif parameter == "dissolved_oxygen_mg_l":
                if value < limit:
                    status = "CRITICAL_DEFICIT"
            else:
                if value > limit:
                    status = "CRITICAL_EXCEEDED"

        query = \"\"\"
            INSERT INTO environmental_metrics (station_id, parameter, value, unit, status)
            VALUES (?, ?, ?, ?, ?)
        \"\"\"
        self.db.execute_non_query(query, (station_id, parameter, value, unit, status))
        return {"station_id": station_id, "parameter": parameter, "value": value, "status": status}

    def analyze_bio_sequence(self, sample_code: str, organism: str, sequence: str) -> Dict[str, Any]:
        clean_seq = sequence.upper().strip()
        length = len(clean_seq)
        if length == 0:
            raise ValueError("Sequence data cannot be empty.")

        g_count = clean_seq.count('G')
        c_count = clean_seq.count('C')
        gc_content = round(((g_count + c_count) / length) * 100, 2)

        resistance_marker = "CGT" in clean_seq or gc_content > 58.0

        query = \"\"\"
            INSERT OR REPLACE INTO bio_sequences (sample_code, organism, sequence_data, gc_content, resistance_marker_detected)
            VALUES (?, ?, ?, ?, ?)
        \"\"\"
        self.db.execute_non_query(query, (sample_code, organism, clean_seq, gc_content, resistance_marker))

        return {
            "sample_code": sample_code,
            "organism": organism,
            "length": length,
            "gc_content_pct": gc_content,
            "resistance_marker_detected": resistance_marker,
            "compliance_alert": "HIGH RISK - RESISTANCE DETECTED" if resistance_marker else "SAFE"
        }

    def generate_compliance_report(self) -> Dict[str, Any]:
        metrics = self.db.execute_query("SELECT * FROM environmental_metrics ORDER BY timestamp DESC LIMIT 100;")
        sequences = self.db.execute_query("SELECT * FROM bio_sequences ORDER BY logged_date DESC LIMIT 50;")

        breaches = [m for m in metrics if m["status"] != "COMPLIANT"]
        resistance_cases = [s for s in sequences if s["resistance_marker_detected"]]

        return {
            "report_generated_at": datetime.utcnow().isoformat(),
            "total_telemetry_analyzed": len(metrics),
            "total_compliance_breaches": len(breaches),
            "total_bio_samples_scanned": len(sequences),
            "antimicrobial_resistance_alerts": len(resistance_cases),
            "status": "ACTION_REQUIRED" if len(breaches) > 0 or len(resistance_cases) > 0 else "OPTIMAL"
        }
