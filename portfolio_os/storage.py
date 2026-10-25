"""SQLite persistence for the first Portfolio Intelligence OS release.

Uses the application's existing research_os.db by default. Set
PORTFOLIO_OS_DB_PATH to override the location. Production deployments should
use durable managed storage and authenticated user/workspace isolation.
"""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping

DEFAULT_DB_PATH = os.getenv("PORTFOLIO_OS_DB_PATH", "research_os.db")
STATUSES = ("Hypothesis", "Research", "Validation", "Pilot", "Scaling", "Parked")


def _connect(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    path = Path(db_path)
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def _transaction(db_path: str | Path = DEFAULT_DB_PATH) -> Iterator[sqlite3.Connection]:
    conn = _connect(db_path)
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_store(db_path: str | Path = DEFAULT_DB_PATH) -> None:
    with _transaction(db_path) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS portfolio_os_opportunities (
                opportunity_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )"""
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_portfolio_os_updated_at "
            "ON portfolio_os_opportunities(updated_at DESC)"
        )


def save_opportunity(record: Mapping[str, Any], db_path: str | Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    payload = dict(record)
    title = str(payload.get("title", "")).strip()
    if not title:
        raise ValueError("Opportunity title is required")
    init_store(db_path)
    opportunity_id = str(payload.get("opportunity_id") or uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    payload["opportunity_id"] = opportunity_id
    payload["title"] = title
    with _transaction(db_path) as conn:
        existing = conn.execute(
            "SELECT created_at FROM portfolio_os_opportunities WHERE opportunity_id = ?",
            (opportunity_id,),
        ).fetchone()
        created_at = existing["created_at"] if existing else now
        conn.execute(
            """INSERT INTO portfolio_os_opportunities
               (opportunity_id, title, payload_json, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(opportunity_id) DO UPDATE SET
                 title = excluded.title,
                 payload_json = excluded.payload_json,
                 updated_at = excluded.updated_at""",
            (opportunity_id, title, json.dumps(payload, sort_keys=True), created_at, now),
        )
    payload["created_at"] = created_at
    payload["updated_at"] = now
    return payload


def list_opportunities(db_path: str | Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    init_store(db_path)
    with _transaction(db_path) as conn:
        rows = conn.execute(
            "SELECT payload_json, created_at, updated_at FROM portfolio_os_opportunities ORDER BY updated_at DESC"
        ).fetchall()
    result = []
    for row in rows:
        payload = json.loads(row["payload_json"])
        payload["created_at"] = row["created_at"]
        payload["updated_at"] = row["updated_at"]
        result.append(payload)
    return result


def seed_examples_if_empty(db_path: str | Path = DEFAULT_DB_PATH) -> None:
    """Add transparent starter hypotheses once; never overwrite user data."""
    init_store(db_path)
    with _transaction(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM portfolio_os_opportunities").fetchone()[0]
    if count:
        return
    examples = [
        {
            "title": "Climate-risk and environmental compliance intelligence",
            "sector": "Climate / public infrastructure",
            "problem": "Institutions need earlier, auditable signals about climate and ecosystem risks.",
            "target_customer": "Local authorities, infrastructure operators, conservation programmes",
            "source_url": "https://www.worldbank.org/en/news/press-release/2025/09/11/embracing-climate-smart-growth-is-a-net-win-for-uganda",
            "source_note": "World Bank Uganda climate report announcement; market willingness to pay remains unvalidated.",
            "impact": 5, "urgency": 5, "feasibility": 3, "willingness_to_pay": 2,
            "strategic_fit": 5, "evidence_quality": 4, "time_to_value": 3, "risk": 4,
            "monthly_price": 0, "variable_cost": 0, "monthly_fixed_cost": 0,
            "status": "Research", "next_experiment": "Interview 5 potential institutional buyers and identify their current reporting workflow.",
        },
        {
            "title": "Reliable AI workflow automation for small teams",
            "sector": "AI / operations",
            "problem": "Teams need automations with honest connector status, retries, audit trails, and safe approvals.",
            "target_customer": "SMEs, agencies, operations teams",
            "source_url": "https://www.weforum.org/publications/the-future-of-jobs-report-2025/in-full/3-skills-outlook/",
            "source_note": "WEF documents growing demand for AI, data and cybersecurity skills; buyer demand for this product still needs validation.",
            "impact": 4, "urgency": 4, "feasibility": 4, "willingness_to_pay": 3,
            "strategic_fit": 5, "evidence_quality": 3, "time_to_value": 4, "risk": 3,
            "monthly_price": 25, "variable_cost": 5, "monthly_fixed_cost": 100,
            "status": "Validation", "next_experiment": "Recruit 3 teams to test one end-to-end workflow with measured time saved and failure recovery.",
        },
        {
            "title": "Research reproducibility and evidence integrity workspace",
            "sector": "Research / education",
            "problem": "Researchers need traceable sources, reproducible runs, QC gates, and publication-ready evidence.",
            "target_customer": "University labs, research groups, science programmes",
            "source_url": "https://github.com/Chrishem2003/notion-live-analyzer",
            "source_note": "Grounded in existing repository capabilities; customer interviews and paid pilots are still required.",
            "impact": 4, "urgency": 3, "feasibility": 4, "willingness_to_pay": 2,
            "strategic_fit": 5, "evidence_quality": 2, "time_to_value": 3, "risk": 3,
            "monthly_price": 0, "variable_cost": 0, "monthly_fixed_cost": 0,
            "status": "Hypothesis", "next_experiment": "Observe one research team moving a study from intake through QC and record the time lost to handoffs.",
        },
        {
            "title": "Safe, outcome-based cybersecurity learning labs",
            "sector": "Cybersecurity / skills",
            "problem": "Learners and institutions need practical labs with bounded environments and demonstrated competence.",
            "target_customer": "Training institutions, bootcamps, employers, learners",
            "source_url": "https://www.weforum.org/media/future-of-jobs-report-2025-78-million-new-job-opportunities-by-2030-but-urgent-upskilling-needed-to-prepare-workforces/",
            "source_note": "WEF reports major skills transformation through 2030; local demand and pricing remain unvalidated.",
            "impact": 4, "urgency": 4, "feasibility": 3, "willingness_to_pay": 3,
            "strategic_fit": 4, "evidence_quality": 3, "time_to_value": 4, "risk": 4,
            "monthly_price": 10, "variable_cost": 3, "monthly_fixed_cost": 100,
            "status": "Research", "next_experiment": "Run a small instructor-led cohort and measure completion, lab safety, and willingness to pay.",
        },
    ]
    for example in examples:
        save_opportunity(example, db_path)
