"""
Production FastAPI Gateway for Notion Live Analyzer & NEMA Agora Intelligence
Author: Chrishem (Kula Chris)
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NemaAgoraAPI")

app = FastAPI(
    title="NEMA Agora & Notion Live Analyzer Enterprise API",
    version="2.0.0",
    description="High-performance backend for environmental intelligence and bioinformatics analytics."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "nema_agora_vault.db"

def init_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
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
    conn.close()

init_db()

class SensorReading(BaseModel):
    station_id: str
    parameter: str
    value: float
    unit: str

class BioSequencePayload(BaseModel):
    sample_code: str
    organism: str
    sequence: str

@app.get("/health")
def health_check():
    return {"status": "HEALTHY", "system": "Chrishem Sovereign Apex Hub", "timestamp": time.time()}

@app.post("/api/v1/telemetry/ingest")
def ingest_telemetry(reading: SensorReading):
    thresholds = {
        "turbidity_ntu": 50.0,
        "dissolved_oxygen_mg_l": 4.0,
        "ph": (6.5, 8.5)
    }
    
    status = "COMPLIANT"
    limit = thresholds.get(reading.parameter)
    if limit:
        if isinstance(limit, tuple):
            if not (limit[0] <= reading.value <= limit[1]):
                status = "WARNING_BREACH"
        elif reading.parameter == "dissolved_oxygen_mg_l" and reading.value < limit:
            status = "CRITICAL_DEFICIT"
        elif reading.value > limit:
            status = "CRITICAL_EXCEEDED"

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO environmental_metrics (station_id, parameter, value, unit, status) VALUES (?, ?, ?, ?, ?)",
            (reading.station_id, reading.parameter, reading.value, reading.unit, status)
        )
        conn.commit()

    return {"success": True, "station_id": reading.station_id, "status": status}

@app.post("/api/v1/bio/analyze")
def analyze_sequence(payload: BioSequencePayload):
    seq = payload.sequence.upper().strip()
    if not seq:
        raise HTTPException(status_code=400, detail="Sequence cannot be empty.")
    
    gc = round(((seq.count('G') + seq.count('C')) / len(seq)) * 100, 2)
    resistance = "CGT" in seq or gc > 58.0

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO bio_sequences (sample_code, organism, sequence_data, gc_content, resistance_marker_detected) VALUES (?, ?, ?, ?, ?)",
            (payload.sample_code, payload.organism, seq, gc, resistance)
        )
        conn.commit()

    return {
        "sample_code": payload.sample_code,
        "gc_content_pct": gc,
        "resistance_marker_detected": resistance,
        "alert": "HIGH RISK - RESISTANCE DETECTED" if resistance else "SAFE"
    }
