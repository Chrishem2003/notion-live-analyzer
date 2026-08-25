"""
legacy_research_data.py — Real persistent storage for the three datasets that
Collaboration & Portfolio, Domain Analytics Hub, and Literature & Publishing
Hub read/write: venture projects, mcr gene surveillance, PPWR/DRA clinical
cohort entries, and the academic report vault.

Honesty note: this was previously a 1-line stub (`# Stub module for
legacy_research_data.py`) with none of the eight functions the calling pages
actually import, which meant those three pages threw a real ImportError on
load. The page copy on those tabs says the data was "migrated from an
earlier standalone build" / "genuine records, not demo data" — this module
does NOT fabricate that history. There is no earlier build's data available
to migrate here, so every table starts genuinely empty and is populated only
through the "Add" forms already built into those pages. No seed/sample rows
are inserted. If you do have the real historical export from the earlier
build, drop it in as a one-time import and these functions will read it
going forward exactly the same way.

Storage: a dedicated SQLite file (legacy_research_data.db) so this survives
Streamlit reruns and process restarts, consistent with how app.py's own
sovereign_apex_engine.db is used for user accounts.
"""

from __future__ import annotations

import sqlite3
import datetime
from pathlib import Path

import pandas as pd

APP_DIR = Path(__file__).resolve().parent.parent
DB_PATH = str(APP_DIR / "legacy_research_data.db")


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def _init_db() -> None:
    conn = _get_conn()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS business_projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_name TEXT UNIQUE NOT NULL,
                lead_entity TEXT,
                capital_ugx REAL,
                roi_projection_pct REAL,
                status TEXT,
                created_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mcr_surveillance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sample_id TEXT UNIQUE NOT NULL,
                sample_type TEXT,
                source_location TEXT,
                latitude REAL,
                longitude REAL,
                mcr_variant TEXT,
                colistin_mic REAL,
                isolation_date TEXT,
                notes TEXT,
                created_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ppwr_cohort (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                participant_age INTEGER,
                months_postpartum INTEGER,
                dra_gap_cm REAL,
                ppwr_kg REAL,
                created_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS academic_vault (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                course_code TEXT,
                department TEXT,
                status TEXT,
                abstract_text TEXT,
                created_at TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


_init_db()


# --------------------------------------------------------------------------
# Venture Portfolio (Collaboration & Portfolio hub)
# --------------------------------------------------------------------------

def get_business_projects_df() -> pd.DataFrame:
    conn = _get_conn()
    try:
        df = pd.read_sql_query(
            "SELECT project_name, lead_entity, capital_ugx, roi_projection_pct, status "
            "FROM business_projects ORDER BY id DESC",
            conn,
        )
    finally:
        conn.close()
    return df


def add_business_project(
    project_name: str, lead_entity: str, capital_ugx: float,
    roi_projection_pct: float, status: str,
) -> None:
    conn = _get_conn()
    try:
        conn.execute(
            """
            INSERT INTO business_projects (project_name, lead_entity, capital_ugx, roi_projection_pct, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(project_name) DO UPDATE SET
                lead_entity=excluded.lead_entity,
                capital_ugx=excluded.capital_ugx,
                roi_projection_pct=excluded.roi_projection_pct,
                status=excluded.status
            """,
            (project_name, lead_entity, capital_ugx, roi_projection_pct, status,
             datetime.datetime.now(datetime.UTC).isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


# --------------------------------------------------------------------------
# mcr Gene Resistance Surveillance (Domain Analytics Hub)
# --------------------------------------------------------------------------

def get_mcr_surveillance_df() -> pd.DataFrame:
    conn = _get_conn()
    try:
        df = pd.read_sql_query(
            "SELECT sample_id, sample_type, source_location, latitude, longitude, "
            "mcr_variant, colistin_mic, isolation_date, notes "
            "FROM mcr_surveillance ORDER BY id DESC",
            conn,
        )
    finally:
        conn.close()
    return df


def add_mcr_sample(
    sample_id: str, sample_type: str, source_location: str, latitude: float,
    longitude: float, mcr_variant: str, colistin_mic: float,
    isolation_date, notes: str = "",
) -> None:
    conn = _get_conn()
    try:
        existing = conn.execute(
            "SELECT 1 FROM mcr_surveillance WHERE sample_id = ?", (sample_id,)
        ).fetchone()
        if existing:
            raise ValueError(f"Sample ID '{sample_id}' already exists")
        iso = isolation_date.isoformat() if hasattr(isolation_date, "isoformat") else str(isolation_date)
        conn.execute(
            """
            INSERT INTO mcr_surveillance
                (sample_id, sample_type, source_location, latitude, longitude,
                 mcr_variant, colistin_mic, isolation_date, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (sample_id, sample_type, source_location, latitude, longitude,
             mcr_variant, colistin_mic, iso, notes,
             datetime.datetime.now(datetime.UTC).isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


# --------------------------------------------------------------------------
# PPWR / DRA Clinical Cohort (Domain Analytics Hub)
# --------------------------------------------------------------------------

def get_ppwr_df() -> pd.DataFrame:
    conn = _get_conn()
    try:
        df = pd.read_sql_query(
            "SELECT participant_age, months_postpartum, dra_gap_cm, ppwr_kg "
            "FROM ppwr_cohort ORDER BY id DESC",
            conn,
        )
    finally:
        conn.close()
    return df


def add_ppwr_entry(
    participant_age: int, months_postpartum: int, dra_gap_cm: float, ppwr_kg: float,
) -> None:
    conn = _get_conn()
    try:
        conn.execute(
            """
            INSERT INTO ppwr_cohort (participant_age, months_postpartum, dra_gap_cm, ppwr_kg, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (participant_age, months_postpartum, dra_gap_cm, ppwr_kg,
             datetime.datetime.now(datetime.UTC).isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


# --------------------------------------------------------------------------
# Academic Report Vault (Literature & Publishing Hub)
# --------------------------------------------------------------------------

def get_academic_vault_df() -> pd.DataFrame:
    conn = _get_conn()
    try:
        df = pd.read_sql_query(
            "SELECT title, course_code, department, status, abstract_text "
            "FROM academic_vault ORDER BY id DESC",
            conn,
        )
    finally:
        conn.close()
    return df


def add_academic_report(
    title: str, course_code: str, department: str, status: str, abstract_text: str,
) -> None:
    conn = _get_conn()
    try:
        conn.execute(
            """
            INSERT INTO academic_vault (title, course_code, department, status, abstract_text, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (title, course_code, department, status, abstract_text,
             datetime.datetime.now(datetime.UTC).isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


