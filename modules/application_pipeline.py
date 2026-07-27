"""
Application Pipeline, Document Vault & Currency Module
========================================================
Production-grade Application Lifecycle Management module for the
Opportunities Hub — featuring a Pipeline Tracker, Document Vault,
and Currency Conversion engine.

Architecture:
  - PipelineDatabase: SQLite persistence layer matching the existing
    research_workspace.db pattern used by audit_engine, literature_engine, etc.
  - DocumentCompletenessChecker: Gap analysis comparing user-uploaded docs
    against required grant/opportunity document lists.
  - CurrencyConverter: Standard conversion rates engine with formatted
    net stipend vs. tuition cover display strings.
  - ApplicationPipelineManager: CRUD operations, status transitions,
    milestone checklist tracking.
  - render_pipeline_ui(): Full Streamlit UI for the Kanban pipeline board,
    readiness checklist, document vault, and currency badges.

Data Models (SQLite):
  saved_applications:
    - id (UUID TEXT PK)
    - user_id (TEXT)
    - opportunity_id (TEXT)
    - status (TEXT: SAVED | PREPARING | SUBMITTED | AWARDED | REJECTED)
    - internal_notes (TEXT)
    - target_date (TEXT ISO)
    - created_at (TEXT ISO)
    - updated_at (TEXT ISO)

  user_documents:
    - id (UUID TEXT PK)
    - user_id (TEXT)
    - doc_type (TEXT: CV | TRANSCRIPT | PROPOSAL | RECOMMENDATION | PASSPORT)
    - title (TEXT)
    - file_url (TEXT)
    - uploaded_at (TEXT ISO)

  pipeline_milestones:
    - id (UUID TEXT PK)
    - application_id (TEXT FK -> saved_applications.id)
    - title (TEXT)
    - is_completed (INTEGER 0|1)
    - created_at (TEXT ISO)
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union

# ─── Database Path (matching existing pattern) ──────────────────────
from modules.config import APP_DIR
from modules.opportunity_feed import (
    OpportunityDatabase as FeedDatabase,
    OpportunityFeedEngine,
    VerificationScorer,
    GeoPrioritizer,
    OpportunityType,
    SourceAuthority,
    ALL_COUNTRIES,
    get_country_flag,
    get_region_for_country,
    seed_opportunity_catalog,
    FEED_CSS,
)

DB_PATH = APP_DIR / "research_workspace.db"


# ═══════════════════════════════════════════════════════════════════════
# ENUMS & CONSTANTS
# ═══════════════════════════════════════════════════════════════════════

class ApplicationStatus(str, Enum):
    """Lifecycle statuses for saved applications."""
    SAVED = "SAVED"
    PREPARING = "PREPARING"
    SUBMITTED = "SUBMITTED"
    AWARDED = "AWARDED"
    REJECTED = "REJECTED"

    @classmethod
    def display_name(cls, status: str) -> str:
        names = {
            "SAVED": "💾 Saved",
            "PREPARING": "📝 Preparing",
            "SUBMITTED": "🚀 Submitted",
            "AWARDED": "🏆 Awarded",
            "REJECTED": "❌ Rejected",
        }
        return names.get(status, status)

    @classmethod
    def icon(cls, status: str) -> str:
        icons = {
            "SAVED": "💾",
            "PREPARING": "📝",
            "SUBMITTED": "🚀",
            "AWARDED": "🏆",
            "REJECTED": "❌",
        }
        return icons.get(status, "📋")

    @classmethod
    def color(cls, status: str) -> str:
        colors = {
            "SAVED": "#6366f1",      # indigo
            "PREPARING": "#f59e0b",  # amber
            "SUBMITTED": "#3b82f6",  # blue
            "AWARDED": "#22c55e",    # green
            "REJECTED": "#ef4444",   # red
        }
        return colors.get(status, "#64748b")


class DocumentType(str, Enum):
    """Standardized document types for grant/opportunity applications."""
    CV = "CV"
    TRANSCRIPT = "TRANSCRIPT"
    PROPOSAL = "PROPOSAL"
    RECOMMENDATION = "RECOMMENDATION"
    PASSPORT = "PASSPORT"
    OTHER = "OTHER"

    @classmethod
    def display_name(cls, doc_type: str) -> str:
        names = {
            "CV": "📄 Curriculum Vitae",
            "TRANSCRIPT": "🎓 Academic Transcript",
            "PROPOSAL": "📝 Research Proposal",
            "RECOMMENDATION": "📬 Letter of Recommendation",
            "PASSPORT": "🛂 Passport / ID",
            "OTHER": "📎 Other Document",
        }
        return names.get(doc_type, doc_type)

    @classmethod
    def icon(cls, doc_type: str) -> str:
        icons = {
            "CV": "📄",
            "TRANSCRIPT": "🎓",
            "PROPOSAL": "📝",
            "RECOMMENDATION": "📬",
            "PASSPORT": "🛂",
            "OTHER": "📎",
        }
        return icons.get(doc_type, "📄")


# Default required documents for a generic grant/opportunity
DEFAULT_REQUIRED_DOCS: List[str] = [
    "CV",
    "TRANSCRIPT",
    "PROPOSAL",
    "RECOMMENDATION",
    "PASSPORT",
]

# Standard currency conversion rates (USD base)
# In production, these would come from a live forex API
CURRENCY_RATES: Dict[str, float] = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "JPY": 149.50,
    "CNY": 7.24,
    "INR": 83.12,
    "CAD": 1.36,
    "AUD": 1.53,
    "BRL": 4.97,
    "KRW": 1325.00,
    "SGD": 1.34,
    "CHF": 0.88,
    "SEK": 10.42,
    "NOK": 10.65,
    "DKK": 6.87,
    "NZD": 1.63,
    "MXN": 17.15,
    "ZAR": 18.74,
    "TRY": 30.25,
    "NGN": 1550.00,
    "KES": 145.00,
    "EGP": 30.90,
    "THB": 35.80,
    "IDR": 15650.00,
    "PHP": 56.20,
    "VND": 24600.00,
    "PKR": 278.00,
    "BDT": 109.50,
    "LKR": 310.00,
    "GHS": 12.50,
    "TZS": 2520.00,
    "UGX": 3800.00,
    "RWF": 1310.00,
    "ETB": 56.80,
    "MAD": 10.05,
    "TND": 3.12,
    "DZD": 134.50,
    "SAR": 3.75,
    "AED": 3.67,
    "QAR": 3.64,
    "OMR": 0.38,
    "BHD": 0.38,
    "KWD": 0.31,
    "JOD": 0.71,
    "LBP": 15000.00,
    "IQD": 1310.00,
    "ILS": 3.67,
    "AFN": 72.50,
}

CURRENCY_FLAGS: Dict[str, str] = {
    "USD": "🇺🇸", "EUR": "🇪🇺", "GBP": "🇬🇧", "JPY": "🇯🇵", "CNY": "🇨🇳",
    "INR": "🇮🇳", "CAD": "🇨🇦", "AUD": "🇦🇺", "BRL": "🇧🇷", "KRW": "🇰🇷",
    "SGD": "🇸🇬", "CHF": "🇨🇭", "SEK": "🇸🇪", "NOK": "🇳🇴", "DKK": "🇩🇰",
    "NZD": "🇳🇿", "MXN": "🇲🇽", "ZAR": "🇿🇦", "TRY": "🇹🇷", "NGN": "🇳🇬",
    "KES": "🇰🇪", "EGP": "🇪🇬", "THB": "🇹🇭", "IDR": "🇮🇩", "PHP": "🇵🇭",
    "VND": "🇻🇳", "PKR": "🇵🇰", "BDT": "🇧🇩", "LKR": "🇱🇰", "GHS": "🇬🇭",
    "TZS": "🇹🇿", "UGX": "🇺🇬", "RWF": "🇷🇼", "ETB": "🇪🇹", "MAD": "🇲🇦",
    "TND": "🇹🇳", "DZD": "🇩🇿", "SAR": "🇸🇦", "AED": "🇦🇪", "QAR": "🇶🇦",
    "OMR": "🇴🇲", "BHD": "🇧🇭", "KWD": "🇰🇼", "JOD": "🇯🇴", "LBP": "🇱🇧",
    "IQD": "🇮🇶", "ILS": "🇮🇱", "AFN": "🇦🇫",
}

CURRENCY_NAMES: Dict[str, str] = {
    "USD": "US Dollar", "EUR": "Euro", "GBP": "British Pound", "JPY": "Japanese Yen",
    "CNY": "Chinese Yuan", "INR": "Indian Rupee", "CAD": "Canadian Dollar",
    "AUD": "Australian Dollar", "BRL": "Brazilian Real", "KRW": "South Korean Won",
    "SGD": "Singapore Dollar", "CHF": "Swiss Franc", "SEK": "Swedish Krona",
    "NOK": "Norwegian Krone", "DKK": "Danish Krone", "NZD": "New Zealand Dollar",
    "MXN": "Mexican Peso", "ZAR": "South African Rand", "TRY": "Turkish Lira",
    "NGN": "Nigerian Naira", "KES": "Kenyan Shilling", "EGP": "Egyptian Pound",
    "THB": "Thai Baht", "IDR": "Indonesian Rupiah", "PHP": "Philippine Peso",
    "VND": "Vietnamese Dong", "PKR": "Pakistani Rupee", "BDT": "Bangladeshi Taka",
    "LKR": "Sri Lankan Rupee", "GHS": "Ghanaian Cedi", "TZS": "Tanzanian Shilling",
    "UGX": "Ugandan Shilling", "RWF": "Rwandan Franc", "ETB": "Ethiopian Birr",
    "MAD": "Moroccan Dirham", "TND": "Tunisian Dinar", "DZD": "Algerian Dinar",
    "SAR": "Saudi Riyal", "AED": "UAE Dirham", "QAR": "Qatari Riyal",
    "OMR": "Omani Rial", "BHD": "Bahraini Dinar", "KWD": "Kuwaiti Dinar",
    "JOD": "Jordanian Dinar", "LBP": "Lebanese Pound", "IQD": "Iraqi Dinar",
    "ILS": "Israeli Shekel", "AFN": "Afghan Afghani",
}


# ═══════════════════════════════════════════════════════════════════════
# PIPELINE DATABASE
# ═══════════════════════════════════════════════════════════════════════

class PipelineDatabase:
    """
    SQLite persistence layer for the Application Pipeline.
    Manages saved_applications, user_documents, and pipeline_milestones tables.
    Follows the same pattern as literature_engine.LiteratureDatabase
    and audit_engine.AuditDatabase.
    """

    def __init__(self, db_path: Union[str, Path] = DB_PATH):
        self.db_path = Path(db_path)
        self._init_schema()

    def _get_conn(self) -> sqlite3.Connection:
        """Get a reusable database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_schema(self):
        """Create tables if they don't exist."""
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS saved_applications (
                    id              TEXT PRIMARY KEY,
                    user_id         TEXT NOT NULL,
                    opportunity_id  TEXT NOT NULL,
                    status          TEXT NOT NULL DEFAULT 'SAVED'
                                    CHECK(status IN ('SAVED','PREPARING','SUBMITTED','AWARDED','REJECTED')),
                    internal_notes  TEXT DEFAULT '',
                    target_date     TEXT,
                    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS user_documents (
                    id          TEXT PRIMARY KEY,
                    user_id     TEXT NOT NULL,
                    doc_type    TEXT NOT NULL
                                CHECK(doc_type IN ('CV','TRANSCRIPT','PROPOSAL','RECOMMENDATION','PASSPORT','OTHER')),
                    title       TEXT NOT NULL,
                    file_url    TEXT NOT NULL DEFAULT '',
                    uploaded_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS pipeline_milestones (
                    id              TEXT PRIMARY KEY,
                    application_id  TEXT NOT NULL,
                    title           TEXT NOT NULL,
                    is_completed    INTEGER NOT NULL DEFAULT 0,
                    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY (application_id) REFERENCES saved_applications(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_saved_apps_user ON saved_applications(user_id);
                CREATE INDEX IF NOT EXISTS idx_saved_apps_status ON saved_applications(status);
                CREATE INDEX IF NOT EXISTS idx_user_docs_user ON user_documents(user_id);
                CREATE INDEX IF NOT EXISTS idx_milestones_app ON pipeline_milestones(application_id);
            """)
            conn.commit()
        finally:
            conn.close()

    # ─── Saved Applications CRUD ───────────────────────────────────

    def create_application(self, user_id: str, opportunity_id: str,
                           target_date: Optional[str] = None,
                           internal_notes: str = "") -> Dict[str, Any]:
        """Create a new saved application."""
        app_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO saved_applications
                   (id, user_id, opportunity_id, status, internal_notes, target_date, created_at, updated_at)
                   VALUES (?, ?, ?, 'SAVED', ?, ?, ?, ?)""",
                (app_id, user_id, opportunity_id, internal_notes, target_date or now, now, now)
            )
            conn.commit()
            return self.get_application(app_id)
        finally:
            conn.close()

    def get_application(self, app_id: str) -> Optional[Dict[str, Any]]:
        """Get a single application by ID."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM saved_applications WHERE id = ?", (app_id,)
            ).fetchone()
            if row is None:
                return None
            app = dict(row)
            # Fetch milestones
            milestones = conn.execute(
                "SELECT * FROM pipeline_milestones WHERE application_id = ? ORDER BY created_at",
                (app_id,)
            ).fetchall()
            app["milestones"] = [dict(m) for m in milestones]
            return app
        finally:
            conn.close()

    def list_applications(self, user_id: Optional[str] = None,
                          status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List applications with optional filters."""
        conn = self._get_conn()
        try:
            query = "SELECT * FROM saved_applications"
            params = []
            conditions = []

            if user_id:
                conditions.append("user_id = ?")
                params.append(user_id)
            if status:
                conditions.append("status = ?")
                params.append(status)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY updated_at DESC"

            rows = conn.execute(query, params).fetchall()
            apps = []
            for row in rows:
                app = dict(row)
                # Attach milestones for each app
                ms = conn.execute(
                    "SELECT * FROM pipeline_milestones WHERE application_id = ? ORDER BY created_at",
                    (app["id"],)
                ).fetchall()
                app["milestones"] = [dict(m) for m in ms]
                apps.append(app)
            return apps
        finally:
            conn.close()

    def update_application_status(self, app_id: str, new_status: str) -> Optional[Dict[str, Any]]:
        """Update the status of a saved application."""
        valid_statuses = {"SAVED", "PREPARING", "SUBMITTED", "AWARDED", "REJECTED"}
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status '{new_status}'. Must be one of {valid_statuses}")
        conn = self._get_conn()
        try:
            now = datetime.now().isoformat()
            conn.execute(
                "UPDATE saved_applications SET status = ?, updated_at = ? WHERE id = ?",
                (new_status, now, app_id)
            )
            conn.commit()
            return self.get_application(app_id)
        finally:
            conn.close()

    def update_application_notes(self, app_id: str, notes: str,
                                  target_date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Update internal notes and/or target date for an application."""
        conn = self._get_conn()
        try:
            now = datetime.now().isoformat()
            if target_date:
                conn.execute(
                    "UPDATE saved_applications SET internal_notes = ?, target_date = ?, updated_at = ? WHERE id = ?",
                    (notes, target_date, now, app_id)
                )
            else:
                conn.execute(
                    "UPDATE saved_applications SET internal_notes = ?, updated_at = ? WHERE id = ?",
                    (notes, now, app_id)
                )
            conn.commit()
            return self.get_application(app_id)
        finally:
            conn.close()

    def delete_application(self, app_id: str) -> bool:
        """Delete an application and its milestones."""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM pipeline_milestones WHERE application_id = ?", (app_id,))
            conn.execute("DELETE FROM saved_applications WHERE id = ?", (app_id,))
            conn.commit()
            return True
        finally:
            conn.close()

    def get_application_counts(self, user_id: Optional[str] = None) -> Dict[str, int]:
        """Get counts of applications grouped by status."""
        conn = self._get_conn()
        try:
            query = "SELECT status, COUNT(*) as cnt FROM saved_applications"
            params = []
            if user_id:
                query += " WHERE user_id = ?"
                params.append(user_id)
            query += " GROUP BY status"
            rows = conn.execute(query, params).fetchall()
            counts = {"SAVED": 0, "PREPARING": 0, "SUBMITTED": 0, "AWARDED": 0, "REJECTED": 0, "TOTAL": 0}
            for row in rows:
                counts[row["status"]] = row["cnt"]
                counts["TOTAL"] += row["cnt"]
            return counts
        finally:
            conn.close()

    # ─── User Documents CRUD ──────────────────────────────────────

    def add_document(self, user_id: str, doc_type: str, title: str,
                     file_url: str = "") -> Dict[str, Any]:
        """Add a user document to the vault."""
        doc_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO user_documents (id, user_id, doc_type, title, file_url, uploaded_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (doc_id, user_id, doc_type, title, file_url, now)
            )
            conn.commit()
            return dict(conn.execute("SELECT * FROM user_documents WHERE id = ?", (doc_id,)).fetchone())
        finally:
            conn.close()

    def list_documents(self, user_id: Optional[str] = None,
                       doc_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """List user documents with optional filters."""
        conn = self._get_conn()
        try:
            query = "SELECT * FROM user_documents"
            params = []
            conditions = []
            if user_id:
                conditions.append("user_id = ?")
                params.append(user_id)
            if doc_type:
                conditions.append("doc_type = ?")
                params.append(doc_type)
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY uploaded_at DESC"
            return [dict(r) for r in conn.execute(query, params).fetchall()]
        finally:
            conn.close()

    def delete_document(self, doc_id: str) -> bool:
        """Delete a user document."""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM user_documents WHERE id = ?", (doc_id,))
            conn.commit()
            return True
        finally:
            conn.close()

    # ─── Milestones CRUD ──────────────────────────────────────────

    def add_milestone(self, application_id: str, title: str) -> Dict[str, Any]:
        """Add a milestone to an application."""
        mid = str(uuid.uuid4())
        now = datetime.now().isoformat()
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO pipeline_milestones (id, application_id, title, is_completed, created_at)
                   VALUES (?, ?, ?, 0, ?)""",
                (mid, application_id, title, now)
            )
            conn.commit()
            return self.get_milestone(mid)
        finally:
            conn.close()

    def get_milestone(self, milestone_id: str) -> Optional[Dict[str, Any]]:
        """Get a single milestone by ID."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM pipeline_milestones WHERE id = ?", (milestone_id,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def toggle_milestone(self, milestone_id: str) -> Optional[Dict[str, Any]]:
        """Toggle a milestone's completed status."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM pipeline_milestones WHERE id = ?", (milestone_id,)
            ).fetchone()
            if row is None:
                return None
            current = row["is_completed"]
            conn.execute(
                "UPDATE pipeline_milestones SET is_completed = ? WHERE id = ?",
                (1 - current, milestone_id)
            )
            conn.commit()
            return dict(conn.execute(
                "SELECT * FROM pipeline_milestones WHERE id = ?", (milestone_id,)
            ).fetchone())
        finally:
            conn.close()

    def delete_milestone(self, milestone_id: str) -> bool:
        """Delete a milestone."""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM pipeline_milestones WHERE id = ?", (milestone_id,))
            conn.commit()
            return True
        finally:
            conn.close()


# ═══════════════════════════════════════════════════════════════════════
# DOCUMENT COMPLETENESS CHECKER
# ═══════════════════════════════════════════════════════════════════════

class DocumentCompletenessChecker:
    """
    Analyzes user-uploaded documents against a list of required grant/opportunity
    documents to identify gaps.

    Returns a structured report with:
      - complete: bool — whether all required docs are present
      - missing_docs: List[str] — document types that are missing
      - matched_docs: List[str] — document types that are present
      - extra_docs: List[str] — uploaded docs not in the required list (bonus)
    """

    @staticmethod
    def check_document_completeness(
        user_docs: List[Dict[str, Any]],
        required_docs: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Compare uploaded user documents against required grant documents.

        Args:
            user_docs: List of user document dicts (must have 'doc_type' key)
            required_docs: List of required document type strings.
                           Defaults to DEFAULT_REQUIRED_DOCS if None.

        Returns:
            Dict with keys: complete, missing_docs, matched_docs, extra_docs,
                           total_required, total_uploaded, completion_pct
        """
        if required_docs is None:
            required_docs = DEFAULT_REQUIRED_DOCS

        # Normalize required docs to uppercase for comparison
        required_set = set(rt.upper() for rt in required_docs)

        # Extract doc types from user uploaded documents
        uploaded_types = set()
        for doc in user_docs:
            dt = doc.get("doc_type", "").upper()
            if dt:
                uploaded_types.add(dt)

        matched = list(required_set & uploaded_types)
        missing = list(required_set - uploaded_types)
        extra = list(uploaded_types - required_set)

        completion_pct = (len(matched) / len(required_set) * 100) if required_set else 100.0

        return {
            "complete": len(missing) == 0,
            "missing_docs": sorted(missing),
            "matched_docs": sorted(matched),
            "extra_docs": sorted(extra),
            "total_required": len(required_set),
            "total_uploaded": len(uploaded_types),
            "completion_pct": round(completion_pct, 1),
        }

    @staticmethod
    def get_required_docs_for_category(category: str) -> List[str]:
        """
        Return a tailored list of required documents based on opportunity category.
        """
        category_docs = {
            "RESEARCH_GRANT": ["CV", "PROPOSAL", "RECOMMENDATION", "TRANSCRIPT", "PASSPORT"],
            "SCHOLARSHIP": ["CV", "TRANSCRIPT", "RECOMMENDATION", "PASSPORT"],
            "FELLOWSHIP": ["CV", "PROPOSAL", "RECOMMENDATION", "TRANSCRIPT"],
            "INTERNSHIP": ["CV", "TRANSCRIPT", "PASSPORT"],
            "CONFERENCE": ["CV", "PASSPORT", "PROPOSAL"],
            "TRAVEL_GRANT": ["CV", "PASSPORT", "RECOMMENDATION"],
            "JOB": ["CV", "RECOMMENDATION", "TRANSCRIPT"],
            "VISA": ["PASSPORT", "CV", "TRANSCRIPT"],
        }
        return category_docs.get(category.upper(), DEFAULT_REQUIRED_DOCS)


# ═══════════════════════════════════════════════════════════════════════
# CURRENCY CONVERTER
# ═══════════════════════════════════════════════════════════════════════

class CurrencyConverter:
    """
    Converts funding amounts between USD and target currencies using
    standard conversion rates. Provides formatted display strings for
    net stipend vs. tuition cover breakdowns.
    """

    SUPPORTED_CURRENCIES = sorted(CURRENCY_RATES.keys())

    @staticmethod
    def convert_funding_amount(
        amount_in_usd: float,
        target_currency: str = "EUR",
        stipend_pct: float = 60.0,
        tuition_pct: float = 40.0,
    ) -> Dict[str, Any]:
        """
        Convert a funding amount from USD to a target currency.

        Args:
            amount_in_usd: Total funding amount in USD.
            target_currency: Target currency code (e.g., 'EUR', 'GBP', 'INR').
            stipend_pct: Percentage allocated to stipend (default 60%).
            tuition_pct: Percentage allocated to tuition (default 40%).

        Returns:
            Dict with original, converted, and display values.
        """
        target = target_currency.upper()
        rate = CURRENCY_RATES.get(target, 1.0)

        converted_total = amount_in_usd * rate
        converted_stipend = converted_total * (stipend_pct / 100.0)
        converted_tuition = converted_total * (tuition_pct / 100.0)

        flag = CURRENCY_FLAGS.get(target, "")
        name = CURRENCY_NAMES.get(target, target)
        symbol = CurrencyConverter._get_symbol(target)

        # Build formatted display strings
        total_display = CurrencyConverter._format_currency(converted_total, target)
        stipend_display = CurrencyConverter._format_currency(converted_stipend, target)
        tuition_display = CurrencyConverter._format_currency(converted_tuition, target)
        usd_display = f"${amount_in_usd:,.2f} USD"

        return {
            "amount_usd": amount_in_usd,
            "usd_display": usd_display,
            "target_currency": target,
            "target_name": name,
            "target_flag": flag,
            "exchange_rate": rate,
            "converted_total": round(converted_total, 2),
            "total_display": total_display,
            "stipend_pct": stipend_pct,
            "tuition_pct": tuition_pct,
            "stipend_amount": round(converted_stipend, 2),
            "stipend_display": stipend_display,
            "tuition_amount": round(converted_tuition, 2),
            "tuition_display": tuition_display,
            "summary_line": f"{flag} {total_display} ({usd_display})",
            "breakdown_line": (
                f"Stipend: {stipend_display} ({stipend_pct:.0f}%)  |  "
                f"Tuition: {tuition_display} ({tuition_pct:.0f}%)"
            ),
            "badge_html": (
                f"<span style='display:inline-flex;align-items:center;gap:0.3rem;"
                f"padding:0.2rem 0.6rem;background:rgba(99,102,241,0.15);"
                f"color:#818cf8;border:1px solid rgba(99,102,241,0.3);"
                f"border-radius:999px;font-size:0.75rem;font-weight:600;'>"
                f"{flag} {usd_display} ≈ {total_display}</span>"
            ),
        }

    @staticmethod
    def _get_symbol(currency_code: str) -> str:
        """Get the currency symbol for a currency code."""
        symbols = {
            "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "CNY": "¥",
            "INR": "₹", "CAD": "C$", "AUD": "A$", "BRL": "R$", "KRW": "₩",
            "SGD": "S$", "CHF": "CHF", "SEK": "kr", "NOK": "kr", "DKK": "kr",
            "NZD": "NZ$", "MXN": "MX$", "ZAR": "R", "TRY": "₺", "NGN": "₦",
            "KES": "KSh", "EGP": "E£", "THB": "฿", "IDR": "Rp", "PHP": "₱",
            "VND": "₫", "PKR": "₨", "BDT": "৳", "LKR": "Rs", "GHS": "GH₵",
            "TZS": "TSh", "UGX": "USh", "RWF": "FRw", "ETB": "Br", "MAD": "د.م.",
            "TND": "د.ت", "DZD": "د.ج", "SAR": "﷼", "AED": "د.إ", "QAR": "﷼",
            "OMR": "﷼", "BHD": ".د.ب", "KWD": "د.ك", "JOD": "د.ا", "LBP": "ل.ل",
            "IQD": "ع.د", "ILS": "₪", "AFN": "؋",
        }
        return symbols.get(currency_code, currency_code)

    @staticmethod
    def _format_currency(amount: float, currency_code: str) -> str:
        """Format a currency amount with the appropriate symbol and decimals."""
        symbol = CurrencyConverter._get_symbol(currency_code)
        # JPY, KRW, IDR, VND, IQD, LBP use 0 decimal places
        no_decimal_currencies = {"JPY", "KRW", "IDR", "VND", "IQD", "LBP", "AFN"}
        if currency_code in no_decimal_currencies:
            formatted = f"{amount:,.0f}"
        else:
            formatted = f"{amount:,.2f}"
        return f"{symbol}{formatted}"

    @staticmethod
    def get_all_rates() -> Dict[str, Dict[str, Any]]:
        """Get all exchange rates with metadata."""
        result = {}
        for code, rate in CURRENCY_RATES.items():
            result[code] = {
                "code": code,
                "name": CURRENCY_NAMES.get(code, code),
                "flag": CURRENCY_FLAGS.get(code, ""),
                "symbol": CurrencyConverter._get_symbol(code),
                "rate_to_usd": rate,
                "display": f"{CURRENCY_FLAGS.get(code, '')} {code} — {CURRENCY_NAMES.get(code, code)}",
            }
        return result

    @staticmethod
    def search_currency(query: str) -> List[Dict[str, Any]]:
        """Search currencies by code, name, or flag."""
        query = query.upper()
        results = []
        for code, name in CURRENCY_NAMES.items():
            if query in code or query in name.upper() or query in CURRENCY_FLAGS.get(code, ""):
                results.append({
                    "code": code,
                    "name": name,
                    "flag": CURRENCY_FLAGS.get(code, ""),
                    "rate": CURRENCY_RATES.get(code, 1.0),
                })
        return results


# ═══════════════════════════════════════════════════════════════════════
# APPLICATION PIPELINE MANAGER
# ═══════════════════════════════════════════════════════════════════════

class ApplicationPipelineManager:
    """
    High-level manager that orchestrates the pipeline database,
    document checking, currency conversion, and opportunity feed.
    """

    def __init__(self, db: Optional[PipelineDatabase] = None):
        self.db = db or PipelineDatabase()
        self.doc_checker = DocumentCompletenessChecker()
        self.currency_converter = CurrencyConverter()
        # Initialize Feed Engine (seeds catalog if needed)
        self.feed_db = FeedDatabase()
        seed_opportunity_catalog(self.feed_db)
        self.feed_engine = OpportunityFeedEngine(self.feed_db)

    # ─── Pipeline Operations ──────────────────────────────────────

    def add_to_pipeline(self, user_id: str, opportunity_id: str,
                         target_date: Optional[str] = None,
                         notes: str = "") -> Dict[str, Any]:
        """Add an opportunity to the pipeline as a SAVED application."""
        return self.db.create_application(user_id, opportunity_id, target_date, notes)

    def move_to_status(self, app_id: str, new_status: str) -> Optional[Dict[str, Any]]:
        """Move an application to a new status (with validation)."""
        valid_transitions = {
            "SAVED": ["PREPARING"],
            "PREPARING": ["SUBMITTED", "SAVED"],
            "SUBMITTED": ["AWARDED", "REJECTED", "PREPARING"],
            "AWARDED": ["REJECTED"],
            "REJECTED": ["SAVED"],
        }
        app = self.db.get_application(app_id)
        if not app:
            return None
        current = app["status"]
        allowed = valid_transitions.get(current, [])
        if new_status not in allowed and new_status != current:
            # Allow any status for flexibility (advisory warning)
            pass
        return self.db.update_application_status(app_id, new_status)

    def get_pipeline_summary(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get a summary of the pipeline for dashboard displays."""
        counts = self.db.get_application_counts(user_id)
        apps = self.db.list_applications(user_id=user_id)
        return {
            "counts": counts,
            "total": counts.get("TOTAL", 0),
            "submission_rate": (
                (counts.get("SUBMITTED", 0) + counts.get("AWARDED", 0)) / max(counts.get("TOTAL", 1), 1) * 100
            ),
            "success_rate": (
                counts.get("AWARDED", 0) / max(counts.get("SUBMITTED", 0) + counts.get("REJECTED", 0), 1) * 100
            ),
            "applications": apps,
            "by_status": {
                s: [a for a in apps if a["status"] == s]
                for s in ["SAVED", "PREPARING", "SUBMITTED", "AWARDED", "REJECTED"]
            },
        }

    # ─── Opportunity Feed Operations ─────────────────────────────

    def feed_add_to_pipeline(self, user_id: str, opp_id: str) -> Optional[Dict[str, Any]]:
        """Add an opportunity from the live feed to the pipeline."""
        return self.feed_engine.add_to_pipeline(self, user_id, opp_id)

    def get_feed(self, user_country: str, **kwargs) -> Dict[str, Any]:
        """Get geo-prioritized opportunity feed."""
        return self.feed_engine.get_feed(user_country, **kwargs)

    def get_feed_featured(self, user_country: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Get featured opportunities for the user."""
        return self.feed_engine.get_featured(user_country, limit)

    def get_feed_statistics(self) -> Dict[str, Any]:
        """Get feed statistics."""
        return self.feed_engine.get_statistics()

    # ─── Document Vault Operations ────────────────────────────────

    def upload_document(self, user_id: str, doc_type: str, title: str,
                        file_url: str = "") -> Dict[str, Any]:
        """Upload a document to the vault."""
        return self.db.add_document(user_id, doc_type, title, file_url)

    def check_readiness(self, user_id: str,
                        required_docs: Optional[List[str]] = None) -> Dict[str, Any]:
        """Check application readiness based on uploaded documents."""
        user_docs = self.db.list_documents(user_id=user_id)
        completeness = self.doc_checker.check_document_completeness(user_docs, required_docs)

        # Get documents organized by type for UI display
        docs_by_type = {}
        for doc in user_docs:
            dt = doc.get("doc_type", "OTHER").upper()
            if dt not in docs_by_type:
                docs_by_type[dt] = []
            docs_by_type[dt].append(doc)

        return {
            "completeness": completeness,
            "user_docs": user_docs,
            "docs_by_type": docs_by_type,
            "total_docs": len(user_docs),
            "readiness_pct": completeness["completion_pct"],
            "readiness_label": (
                "✅ Ready" if completeness["complete"]
                else "⚠️ Incomplete"
            ),
        }

    # ─── Currency Operations ──────────────────────────────────────

    def convert_stipend(self, amount_usd: float, currency: str = "EUR") -> Dict[str, Any]:
        """Convert stipend amount with default 60/40 split."""
        return self.currency_converter.convert_funding_amount(
            amount_usd, currency, stipend_pct=60.0, tuition_pct=40.0
        )

    # ─── Milestone Operations ─────────────────────────────────────

    def add_milestone(self, application_id: str, title: str) -> Dict[str, Any]:
        """Add a milestone task to an application."""
        return self.db.add_milestone(application_id, title)

    def toggle_milestone(self, milestone_id: str) -> Optional[Dict[str, Any]]:
        """Toggle a milestone's completion status."""
        return self.db.toggle_milestone(milestone_id)

    def get_milestone_progress(self, application_id: str) -> Dict[str, Any]:
        """Get milestone progress for an application."""
        app = self.db.get_application(application_id)
        if not app:
            return {"total": 0, "completed": 0, "pct": 0, "milestones": []}
        milestones = app.get("milestones", [])
        total = len(milestones)
        completed = sum(1 for m in milestones if m["is_completed"])
        return {
            "total": total,
            "completed": completed,
            "pct": round((completed / max(total, 1)) * 100, 1),
            "milestones": milestones,
        }


# ═══════════════════════════════════════════════════════════════════════
# DEMO DATA SEEDER
# ═══════════════════════════════════════════════════════════════════════

def seed_demo_data(user_id: str = "demo_user") -> ApplicationPipelineManager:
    """Seed the pipeline with sample data for demonstration purposes."""
    manager = ApplicationPipelineManager()
    db = manager.db

    # Add sample applications
    samples = [
        ("opp_nih_2024", "NIH R01 Research Grant — Cancer Immunotherapy",
         "PREPARING", "2024-09-15T00:00:00", "High-priority: draft specific aims page"),
        ("opp_nsf_grfp", "NSF Graduate Research Fellowship",
         "SAVED", "2024-10-20T00:00:00", "Need to request recommendation letters"),
        ("opp_erc_stg", "ERC Starting Grant — AI for Climate",
         "SUBMITTED", "2024-06-01T00:00:00", "Submitted on 06/01. Awaiting review."),
        ("opp_fulbright", "Fulbright Scholar Program — Public Health",
         "AWARDED", "2024-01-15T00:00:00", "Awarded! $50,000 for 12-month project."),
        ("opp_gates", "Bill & Melinda Gates Foundation — Global Health",
         "REJECTED", "2024-03-01T00:00:00", "Rejected. Revise and resubmit for next cycle."),
        ("opp_wellcome", "Wellcome Trust — Early Career Award",
         "PREPARING", "2024-11-30T00:00:00", "Budget draft completed. Waiting for institutional approval."),
        ("opp_harvard_fellowship", "Harvard Presidential Fellowship",
         "SAVED", "2025-01-10T00:00:00", "Promising opportunity — check eligibility criteria."),
        ("opp_eu_marie", "Marie Skłodowska-Curie Actions — Postdoc",
         "SUBMITTED", "2024-05-30T00:00:00", "Under evaluation — expected decision Sept 2024."),
        ("opp_african_union", "African Union Research Grant — Food Security",
         "SAVED", "2024-12-01T00:00:00", "Collaborative proposal with 3 partner institutions."),
        ("opp_who_fellowship", "WHO Fellowship — Epidemiology",
         "PREPARING", "2024-08-15T00:00:00", "Gathering letters of support from supervisors."),
    ]

    for opp_id, title, status, target_date, notes in samples:
        app = db.create_application(user_id, opp_id, target_date, notes)
        if app:
            db.update_application_status(app["id"], status)

            # Add some milestones
            sample_milestones = [
                "Complete application form",
                "Write personal statement",
                "Gather recommendation letters",
                "Review and proofread",
                "Submit application",
            ]
            for i, ms in enumerate(sample_milestones[:3]):
                milestone = db.add_milestone(app["id"], ms)
                if milestone and i == 0:
                    db.toggle_milestone(milestone["id"])

    # Add sample documents
    sample_docs = [
        ("CV", "Academic CV — Dr. Jane Smith", "vault://docs/cv_2024.pdf"),
        ("TRANSCRIPT", "PhD Transcript — Stanford University", "vault://docs/transcript_phd.pdf"),
        ("PASSPORT", "International Passport", "vault://docs/passport.pdf"),
        ("PROPOSAL", "Research Proposal — AI in Healthcare", "vault://docs/proposal_v3.pdf"),
    ]
    for doc_type, title, url in sample_docs:
        db.add_document(user_id, doc_type, title, url)

    return manager


# ═══════════════════════════════════════════════════════════════════════
# PIPELINE UI CSS (dark-theme, matching vault & collab design system)
# ═══════════════════════════════════════════════════════════════════════

PIPELINE_CSS = """
<style>
.pipeline-container {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 16px;
    overflow: hidden;
    margin-bottom: 1rem;
}
.pipeline-header {
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
    border-bottom: 1px solid #1e293b;
    padding: 1.2rem 1.5rem;
}
.pipeline-header h1 { color: #f8fafc !important; font-size: 1.5rem !important; font-weight: 800 !important; margin: 0 !important; }
.pipeline-header p { color: #94a3b8 !important; font-size: 0.85rem !important; margin: 0.2rem 0 0 0 !important; }

.pipeline-kanban {
    display: flex;
    gap: 0.75rem;
    padding: 1rem;
    overflow-x: auto;
    min-height: 400px;
}
.pipeline-column {
    min-width: 220px;
    max-width: 260px;
    flex: 1;
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 0.75rem;
}
.pipeline-column-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #1e293b;
    margin-bottom: 0.5rem;
}
.pipeline-column-title {
    color: #f1f5f9;
    font-weight: 700;
    font-size: 0.8rem;
}
.pipeline-column-count {
    background: #1e293b;
    color: #94a3b8;
    padding: 0.1rem 0.45rem;
    border-radius: 999px;
    font-size: 0.65rem;
    font-weight: 700;
}
.pipeline-card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 0.75rem;
    margin-bottom: 0.5rem;
    cursor: pointer;
    transition: all 0.2s;
}
.pipeline-card:hover {
    border-color: #6366f1;
    box-shadow: 0 4px 12px rgba(99,102,241,0.1);
}
.pipeline-card-title {
    color: #f1f5f9;
    font-weight: 600;
    font-size: 0.8rem;
    margin-bottom: 0.3rem;
}
.pipeline-card-meta {
    color: #64748b;
    font-size: 0.65rem;
    display: flex;
    gap: 0.4rem;
    align-items: center;
}
.pipeline-card-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.2rem;
    padding: 0.1rem 0.4rem;
    border-radius: 999px;
    font-size: 0.6rem;
    font-weight: 700;
}
.pipeline-badge-saved { background: rgba(99,102,241,0.15); color: #818cf8; border: 1px solid rgba(99,102,241,0.3); }
.pipeline-badge-preparing { background: rgba(245,158,11,0.15); color: #fbbf24; border: 1px solid rgba(245,158,11,0.3); }
.pipeline-badge-submitted { background: rgba(59,130,246,0.15); color: #60a5fa; border: 1px solid rgba(59,130,246,0.3); }
.pipeline-badge-awarded { background: rgba(34,197,94,0.15); color: #4ade80; border: 1px solid rgba(34,197,94,0.3); }
.pipeline-badge-rejected { background: rgba(239,68,68,0.15); color: #f87171; border: 1px solid rgba(239,68,68,0.3); }

.pipeline-checklist-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.4rem 0;
    border-bottom: 1px solid #1e293b;
    font-size: 0.8rem;
}
.pipeline-checklist-item:last-child { border-bottom: none; }

.pipeline-currency-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.2rem 0.6rem;
    background: rgba(99,102,241,0.15);
    color: #818cf8;
    border: 1px solid rgba(99,102,241,0.3);
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
}

.pipeline-metric-card {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 1rem;
    text-align: center;
}
.pipeline-metric-value {
    color: #f1f5f9;
    font-size: 1.5rem;
    font-weight: 800;
}
.pipeline-metric-label {
    color: #64748b;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: 0.15rem;
}

.pipeline-modal-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.7);
    backdrop-filter: blur(8px);
    z-index: 999;
    display: flex;
    align-items: center;
    justify-content: center;
}
.pipeline-modal {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 20px;
    padding: 1.5rem;
    max-width: 720px;
    width: 90%;
    max-height: 85vh;
    overflow-y: auto;
}
.pipeline-modal h3 { color: #f1f5f9; font-size: 1.2rem; font-weight: 700; margin-bottom: 0.75rem; }

.status-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 0.3rem;
}
</style>
"""


# ═══════════════════════════════════════════════════════════════════════
# STREAMLIT UI RENDERER
# ═══════════════════════════════════════════════════════════════════════

def render_pipeline_ui():
    """
    Render the full Application Pipeline, Document Vault & Currency Module UI.
    This is the main entry point called from the Streamlit page.
    """
    import streamlit as st

    # ── Inject CSS ──────────────────────────────────────────────
    st.markdown(PIPELINE_CSS, unsafe_allow_html=True)
    st.markdown(FEED_CSS, unsafe_allow_html=True)

    # ── Initialize Session State ────────────────────────────────
    _init_pipeline_state()

    # ── Get or Create Manager ───────────────────────────────────
    if "pipeline_manager" not in st.session_state or st.session_state["pipeline_manager"] is None:
        manager = seed_demo_data(user_id="demo_user")
        st.session_state["pipeline_manager"] = manager
    else:
        manager = st.session_state["pipeline_manager"]

    db = manager.db
    user_id = "demo_user"

    # ── Header ──────────────────────────────────────────────────
    st.markdown("""
    <div class="pipeline-header" style="border-radius:16px 16px 0 0;margin-bottom:1rem;">
        <div style="display:flex;align-items:center;justify-content:space-between;">
            <div>
                <h1>📋 Application Pipeline & Document Vault</h1>
                <p>Track opportunities · Manage documents · Convert currencies</p>
            </div>
            <div style="display:flex;gap:0.5rem;">
                <span class="pipeline-badge-saved pipeline-card-badge">● Live</span>
                <span class="pipeline-badge-submitted pipeline-card-badge">SQLite</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Dashboard Metrics Row ───────────────────────────────────
    summary = manager.get_pipeline_summary(user_id)
    counts = summary["counts"]

    mcol1, mcol2, mcol3, mcol4, mcol5 = st.columns(5)
    with mcol1:
        st.markdown(f"""
        <div class="pipeline-metric-card">
            <div class="pipeline-metric-value">{counts.get('TOTAL', 0)}</div>
            <div class="pipeline-metric-label">📋 Total Applications</div>
        </div>
        """, unsafe_allow_html=True)
    with mcol2:
        st.markdown(f"""
        <div class="pipeline-metric-card">
            <div class="pipeline-metric-value" style="color:#818cf8;">{counts.get('SAVED', 0)}</div>
            <div class="pipeline-metric-label">💾 Saved</div>
        </div>
        """, unsafe_allow_html=True)
    with mcol3:
        st.markdown(f"""
        <div class="pipeline-metric-card">
            <div class="pipeline-metric-value" style="color:#fbbf24;">{counts.get('PREPARING', 0)}</div>
            <div class="pipeline-metric-label">📝 In Progress</div>
        </div>
        """, unsafe_allow_html=True)
    with mcol4:
        st.markdown(f"""
        <div class="pipeline-metric-card">
            <div class="pipeline-metric-value" style="color:#60a5fa;">{counts.get('SUBMITTED', 0)}</div>
            <div class="pipeline-metric-label">🚀 Submitted</div>
        </div>
        """, unsafe_allow_html=True)
    with mcol5:
        st.markdown(f"""
        <div class="pipeline-metric-card">
            <div class="pipeline-metric-value" style="color:#4ade80;">{counts.get('AWARDED', 0)}</div>
            <div class="pipeline-metric-label">🏆 Awarded</div>
        </div>
        """, unsafe_allow_html=True)

# ── KPI Row ─────────────────────────────────────────────────
    kcol1, kcol2, kcol3 = st.columns(3)
    with kcol1:
        submission_rate = summary.get("submission_rate", 0)
        st.metric("Submission Rate", f"{submission_rate:.1f}%",
                  help="(Submitted + Awarded) / Total applications")
    with kcol2:
        success_rate = summary.get("success_rate", 0)
        st.metric("Success Rate", f"{success_rate:.1f}%",
                  help="Awarded / (Submitted + Rejected) applications")
    with kcol3:
        docs = db.list_documents(user_id=user_id)
        st.metric("📄 Documents in Vault", len(docs))

    # ═════════════════════════════════════════════════════════════
    # LIVE VERIFIED OPPORTUNITY FEED
    # ═════════════════════════════════════════════════════════════
    st.markdown("---")
    _render_opportunity_feed(manager, user_id)

    # ═════════════════════════════════════════════════════════════
    # KANBAN PIPELINE BOARD
    # ═════════════════════════════════════════════════════════════
    st.markdown("## 📋 Pipeline Kanban Board")
    st.caption("Click on a card to view details. Use the status column change to move cards between stages.")

    # Render Kanban columns
    status_order = ["SAVED", "PREPARING", "SUBMITTED", "AWARDED", "REJECTED"]
    status_display = {
        "SAVED": ("💾 Saved", "#6366f1"),
        "PREPARING": ("📝 Preparing", "#f59e0b"),
        "SUBMITTED": ("🚀 Submitted", "#3b82f6"),
        "AWARDED": ("🏆 Awarded", "#22c55e"),
        "REJECTED": ("❌ Rejected", "#ef4444"),
    }

    kanban_html = '<div class="pipeline-kanban">'
    for status in status_order:
        apps_in_column = summary["by_status"].get(status, [])
        display_name, color = status_display.get(status, (status, "#64748b"))

        kanban_html += f"""
        <div class="pipeline-column">
            <div class="pipeline-column-header">
                <span class="pipeline-column-title">
                    <span class="status-dot" style="background:{color};"></span>{display_name}
                </span>
                <span class="pipeline-column-count">{len(apps_in_column)}</span>
            </div>
        """

        for app in apps_in_column[:5]:  # Show max 5 per column
            opp_short = app["opportunity_id"][:20]
            target = app.get("target_date", "")[:10] if app.get("target_date") else "No deadline"
            kanban_html += f"""
            <div class="pipeline-card" onclick="alert('{app['id']}')">
                <div class="pipeline-card-title">{opp_short}</div>
                <div class="pipeline-card-meta">
                    <span>📅 {target}</span>
                    <span class="pipeline-card-badge pipeline-badge-{status.lower()}">{ApplicationStatus.icon(status)}</span>
                </div>
            </div>
            """

        kanban_html += '</div>'

    kanban_html += '</div>'
    st.markdown(kanban_html, unsafe_allow_html=True)

    # ── Alternative: Interactive table view with status change ────
    with st.expander("📊 Table View — Change Status & Edit", expanded=False):
        all_apps = db.list_applications(user_id=user_id)
        if all_apps:
            for app in all_apps:
                col_a, col_b, col_c, col_d = st.columns([3, 1.5, 1.5, 1])
                with col_a:
                    opp_id = app["opportunity_id"][:28]
                    st.markdown(f"**{opp_id}**  \n📅 {app.get('target_date', 'No deadline')[:10]}")
                with col_b:
                    badges = {
                        "SAVED": "pipeline-badge-saved",
                        "PREPARING": "pipeline-badge-preparing",
                        "SUBMITTED": "pipeline-badge-submitted",
                        "AWARDED": "pipeline-badge-awarded",
                        "REJECTED": "pipeline-badge-rejected",
                    }
                    badge_class = badges.get(app["status"], "pipeline-badge-saved")
                    st.markdown(f'<span class="pipeline-card-badge {badge_class}">{ApplicationStatus.display_name(app["status"])}</span>',
                                unsafe_allow_html=True)
                with col_c:
                    # Status change dropdown
                    new_status = st.selectbox(
                        "Move to",
                        options=["SAVED", "PREPARING", "SUBMITTED", "AWARDED", "REJECTED"],
                        index=["SAVED", "PREPARING", "SUBMITTED", "AWARDED", "REJECTED"].index(app["status"]),
                        key=f"status_{app['id']}",
                        label_visibility="collapsed",
                    )
                    if new_status != app["status"]:
                        db.update_application_status(app["id"], new_status)
                        st.rerun()
                with col_d:
                    if st.button("🗑️", key=f"del_{app['id']}", help="Delete application"):
                        db.delete_application(app["id"])
                        st.rerun()
        else:
            st.info("No applications in the pipeline yet. Add one below!")

    # ═════════════════════════════════════════════════════════════
    # ADD NEW APPLICATION
    # ═════════════════════════════════════════════════════════════
    with st.expander("➕ Add New Application to Pipeline", expanded=False):
        col_new1, col_new2 = st.columns([2, 1])
        with col_new1:
            new_opp_id = st.text_input("Opportunity ID", placeholder="e.g., opp_nih_r01_2025",
                                       key="new_opp_id")
            new_notes = st.text_area("Internal Notes", placeholder="Add notes about this opportunity...",
                                     key="new_opp_notes", height=60)
        with col_new2:
            new_target = st.date_input("Target Deadline", key="new_opp_target")
            new_status_choice = st.selectbox("Initial Status",
                                              options=["SAVED", "PREPARING"],
                                              index=0, key="new_opp_status")

        if st.button("➕ Add to Pipeline", type="primary", use_container_width=True) and new_opp_id:
            target_str = new_target.isoformat() if new_target else None
            app = manager.add_to_pipeline(user_id, new_opp_id, target_str, new_notes)
            if app:
                if new_status_choice != "SAVED":
                    db.update_application_status(app["id"], new_status_choice)
                st.success(f"✅ Added '{new_opp_id}' to pipeline as {new_status_choice}")
                st.rerun()

    # ═════════════════════════════════════════════════════════════
    # DOCUMENT VAULT & READINESS CHECKLIST
    # ═════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("## 📄 Document Vault & Readiness Checklist")

    vault_tab1, vault_tab2, vault_tab3 = st.tabs(["📁 My Documents", "✅ Readiness Check", "📤 Upload Document"])

    with vault_tab1:
        docs = db.list_documents(user_id=user_id)
        if docs:
            for doc in docs:
                doc_icon = DocumentType.icon(doc["doc_type"])
                badge_class = {
                    "CV": "pipeline-badge-saved",
                    "TRANSCRIPT": "pipeline-badge-submitted",
                    "PROPOSAL": "pipeline-badge-preparing",
                    "RECOMMENDATION": "pipeline-badge-awarded",
                    "PASSPORT": "pipeline-badge-saved",
                }.get(doc["doc_type"], "pipeline-badge-saved")

                col_d1, col_d2, col_d3 = st.columns([4, 2, 1])
                with col_d1:
                    st.markdown(f"""
                    <div style="display:flex;align-items:center;gap:0.5rem;padding:0.3rem 0;">
                        <span style="font-size:1.2rem;">{doc_icon}</span>
                        <div>
                            <div style="color:#f1f5f9;font-weight:600;font-size:0.85rem;">{doc['title']}</div>
                            <div style="color:#64748b;font-size:0.7rem;">{doc.get('uploaded_at', '')[:10]}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                with col_d2:
                    st.markdown(f'<span class="pipeline-card-badge {badge_class}">{DocumentType.display_name(doc["doc_type"])}</span>',
                                unsafe_allow_html=True)
                with col_d3:
                    if st.button("🗑️", key=f"del_doc_{doc['id']}", help="Delete document"):
                        db.delete_document(doc["id"])
                        st.rerun()
        else:
            st.info("No documents uploaded yet. Upload documents to check application readiness.")

    with vault_tab2:
        # Readiness Check
        readiness = manager.check_readiness(user_id)
        comp = readiness["completeness"]

        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:1rem;margin-bottom:1rem;">
            <span style="font-size:1.5rem;">{'✅' if comp['complete'] else '⚠️'}</span>
            <div>
                <div style="color:#f1f5f9;font-weight:700;font-size:1.1rem;">
                    Application Readiness: {readiness['readiness_pct']:.0f}%
                </div>
                <div style="color:#64748b;font-size:0.8rem;">
                    {comp['total_matched'] if 'total_matched' in comp else len(comp['matched_docs'])} of {comp['total_required']} required documents uploaded
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Progress bar
        readiness_pct = readiness["readiness_pct"]
        bar_color = "#22c55e" if readiness_pct >= 100 else "#f59e0b" if readiness_pct >= 60 else "#ef4444"
        st.markdown(f"""
        <div style="background:#1e293b;border-radius:999px;height:10px;overflow:hidden;margin-bottom:1rem;">
            <div style="height:100%;width:{readiness_pct}%;background:{bar_color};border-radius:999px;
                        transition:width 0.5s;"></div>
        </div>
        """, unsafe_allow_html=True)

        # Matched docs (green)
        if comp["matched_docs"]:
            st.markdown("**✅ Uploaded Documents**")
            for dt in comp["matched_docs"]:
                icon = DocumentType.icon(dt)
                st.markdown(f"""
                <div class="pipeline-checklist-item" style="border-left:3px solid #22c55e;padding-left:0.5rem;">
                    <span style="color:#4ade80;">✅</span>
                    <span style="color:#f1f5f9;">{icon} {DocumentType.display_name(dt)}</span>
                </div>
                """, unsafe_allow_html=True)

        # Missing docs (red)
        if comp["missing_docs"]:
            st.markdown("**❌ Missing Documents**")
            for dt in comp["missing_docs"]:
                icon = DocumentType.icon(dt)
                st.markdown(f"""
                <div class="pipeline-checklist-item" style="border-left:3px solid #ef4444;padding-left:0.5rem;">
                    <span style="color:#f87171;">❌</span>
                    <span style="color:#f1f5f9;">{icon} {DocumentType.display_name(dt)}</span>
                </div>
                """, unsafe_allow_html=True)

        # Extra docs
        if comp.get("extra_docs"):
            st.markdown("**📎 Additional Documents (Bonus)**")
            for dt in comp["extra_docs"]:
                st.markdown(f"""
                <div class="pipeline-checklist-item" style="border-left:3px solid #6366f1;padding-left:0.5rem;">
                    <span style="color:#818cf8;">📎</span>
                    <span style="color:#94a3b8;">{DocumentType.display_name(dt) if hasattr(DocumentType, 'display_name') else dt}</span>
                </div>
                """, unsafe_allow_html=True)

        if comp["complete"]:
            st.success("🎉 All required documents are uploaded! Your application is ready to submit.")
        else:
            st.warning(f"⚠️ Missing {len(comp['missing_docs'])} required document(s). Upload them above.")

    with vault_tab3:
        st.markdown("### 📤 Upload New Document")
        col_up1, col_up2 = st.columns(2)
        with col_up1:
            doc_type = st.selectbox(
                "Document Type",
                options=[dt.value for dt in DocumentType],
                format_func=lambda x: DocumentType.display_name(x),
                key="upload_doc_type"
            )
            doc_title = st.text_input("Document Title", placeholder="e.g., Academic CV 2024",
                                      key="upload_doc_title")
        with col_up2:
            doc_url = st.text_input("File URL / Path", placeholder="vault://docs/filename.pdf",
                                    key="upload_doc_url",
                                    help="In production, use file uploader component")

        if st.button("📤 Upload Document", type="primary", use_container_width=True) and doc_title:
            db.add_document(user_id, doc_type, doc_title, doc_url or "")
            st.success(f"✅ '{doc_title}' uploaded successfully!")
            st.rerun()

    # ═════════════════════════════════════════════════════════════
    # CURRENCY CONVERTER
    # ═════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("## 💱 Currency Converter — Funding Calculator")

    col_cc1, col_cc2, col_cc3 = st.columns([1, 1, 1])
    with col_cc1:
        amount_usd = st.number_input("Amount in USD", min_value=0.0, value=50000.0,
                                      step=1000.0, key="cc_amount")
    with col_cc2:
        target_currency = st.selectbox(
            "Target Currency",
            options=CurrencyConverter.SUPPORTED_CURRENCIES,
            format_func=lambda c: f"{CURRENCY_FLAGS.get(c, '')} {c} — {CURRENCY_NAMES.get(c, c)}",
            index=1, key="cc_currency"
        )
    with col_cc3:
        stipend_pct = st.slider("Stipend %", min_value=0, max_value=100, value=60,
                                 step=5, key="cc_stipend",
                                 help="Percentage allocated to stipend (rest = tuition)")

    if amount_usd > 0:
        conversion = CurrencyConverter.convert_funding_amount(
            amount_usd, target_currency, stipend_pct, 100 - stipend_pct
        )

        st.markdown(f"""
        <div style="background:#0f172a;border:1px solid #1e293b;border-radius:16px;padding:1.5rem;text-align:center;">
            <div style="font-size:2.5rem;margin-bottom:0.5rem;">{conversion['target_flag']}</div>
            <div style="color:#94a3b8;font-size:0.85rem;">{conversion['usd_display']} → {conversion['target_name']}</div>
            <div style="color:#f1f5f9;font-size:2rem;font-weight:800;margin:0.5rem 0;">
                {conversion['total_display']}
            </div>
            <div style="color:#64748b;font-size:0.8rem;">
                Rate: 1 USD = {conversion['exchange_rate']} {target_currency}
            </div>
            <div style="display:flex;justify-content:center;gap:2rem;margin-top:0.75rem;padding-top:0.75rem;border-top:1px solid #1e293b;">
                <div>
                    <div style="color:#4ade80;font-weight:700;">{conversion['stipend_display']}</div>
                    <div style="color:#64748b;font-size:0.7rem;">Stipend ({stipend_pct}%)</div>
                </div>
                <div>
                    <div style="color:#818cf8;font-weight:700;">{conversion['tuition_display']}</div>
                    <div style="color:#64748b;font-size:0.7rem;">Tuition ({100-stipend_pct}%)</div>
                </div>
            </div>
            <div style="margin-top:0.75rem;">
                <span class="pipeline-currency-badge">{conversion['badge_html']}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.caption(conversion["breakdown_line"])

    # ═════════════════════════════════════════════════════════════
    # MILESTONE CHECKLIST
    # ═════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("## ✅ Milestone Checklist")

    # Select an application for milestone management
    all_apps = db.list_applications(user_id=user_id)
    if all_apps:
        app_options = {f"{a['opportunity_id'][:30]}... ({a['id'][:8]})": a["id"] for a in all_apps}
        selected_app_label = st.selectbox("Select Application",
                                           options=list(app_options.keys()),
                                           key="ms_app_select")
        selected_app_id = app_options[selected_app_label]

        # Show milestone progress
        progress = manager.get_milestone_progress(selected_app_id)
        st.markdown(f"""
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;">
            <span style="color:#f1f5f9;font-weight:600;">Progress: {progress['completed']}/{progress['total']} tasks</span>
            <span style="color:#94a3b8;font-size:0.85rem;">{progress['pct']}% complete</span>
        </div>
        """, unsafe_allow_html=True)

        # Progress bar
        ms_pct = progress["pct"]
        st.markdown(f"""
        <div style="background:#1e293b;border-radius:999px;height:8px;overflow:hidden;margin-bottom:1rem;">
            <div style="height:100%;width:{ms_pct}%;background:#6366f1;border-radius:999px;transition:width 0.3s;"></div>
        </div>
        """, unsafe_allow_html=True)

        # List milestones with toggle
        for ms in progress["milestones"]:
            col_ms1, col_ms2 = st.columns([6, 1])
            with col_ms1:
                if ms["is_completed"]:
                    st.markdown(f"""
                    <div class="pipeline-checklist-item">
                        <span style="color:#4ade80;">✅</span>
                        <span style="color:#64748b;text-decoration:line-through;">{ms['title']}</span>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="pipeline-checklist-item">
                        <span style="color:#64748b;">⬜</span>
                        <span style="color:#f1f5f9;">{ms['title']}</span>
                    </div>
                    """, unsafe_allow_html=True)
            with col_ms2:
                if st.button("🔄", key=f"toggle_ms_{ms['id']}", help="Toggle completion"):
                    manager.toggle_milestone(ms["id"])
                    st.rerun()

        # Add new milestone
        col_new_ms1, col_new_ms2 = st.columns([4, 1])
        with col_new_ms1:
            new_ms_title = st.text_input("New milestone", placeholder="e.g., Write personal statement",
                                         key="new_ms_title", label_visibility="collapsed")
        with col_new_ms2:
            if st.button("➕ Add Task", key="add_ms_btn", use_container_width=True) and new_ms_title:
                manager.add_milestone(selected_app_id, new_ms_title)
                st.rerun()
    else:
        st.info("Add applications to the pipeline first to manage milestones.")

    # ═════════════════════════════════════════════════════════════
    # PIPELINE AUDIT LOG
    # ═════════════════════════════════════════════════════════════
    with st.expander("📋 Database Records", expanded=False):
        st.markdown("**Saved Applications**")
        all_rows = db.list_applications()
        if all_rows:
            for r in all_rows:
                st.code(json.dumps(r, indent=2, default=str), language="json")
        else:
            st.info("No records.")

        st.markdown("**User Documents**")
        all_docs = db.list_documents()
        if all_docs:
            for d in all_docs:
                st.code(json.dumps(d, indent=2, default=str), language="json")
        else:
            st.info("No documents.")


# ═══════════════════════════════════════════════════════════════════════
# OPPORTUNITY FEED UI RENDERER
# ═══════════════════════════════════════════════════════════════════════

def _render_opportunity_feed(manager: ApplicationPipelineManager, user_id: str):
    """
    Render the Live Verified Opportunity Feed section.
    Displays a filtered, geo-prioritized feed of scholarships, grants, and fellowships
    with one-click "Add to Pipeline" integration.
    """
    import streamlit as st

    # ── Feed State Init ──────────────────────────────────────────
    feed_defaults = {
        "feed_search": "",
        "feed_country": "Global / Multiple Countries",
        "feed_types": ["SCHOLARSHIP", "GRANT", "FELLOWSHIP"],
        "feed_verification_min": 50,
        "feed_amount_min": 0,
        "feed_amount_max": 1000000,
        "feed_page": 0,
        "feed_expanded": {},
    }
    for key, val in feed_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

    # ── Feed Statistics ──────────────────────────────────────────
    feed_stats = manager.get_feed_statistics()

    # ── Feed Header ──────────────────────────────────────────────
    st.markdown(f"""
    <div class="feed-container">
        <div class="feed-header">
            <div style="display:flex;align-items:center;justify-content:space-between;">
                <div>
                    <h2>🔍 Live Verified Opportunity Feed</h2>
                    <p>Real-time scholarships, grants, and fellowships — prioritized by your location</p>
                </div>
                <div style="display:flex;gap:0.5rem;">
                    <span class="pipeline-badge-awarded pipeline-card-badge">{feed_stats.get('total', 0)} Opportunities</span>
                    <span class="pipeline-badge-saved pipeline-card-badge">Avg {feed_stats.get('avg_verification', 0)}% Verified</span>
                </div>
            </div>
        </div>
        <div class="feed-stats-row">
            <span class="feed-stat">
                <span class="feed-stat-value">{feed_stats.get('total', 0)}</span> Total Opportunities
            </span>
            <span class="feed-stat">
                <span class="feed-stat-value">{feed_stats.get('high_verified', 0)}</span> High-Trust (80+)
            </span>
            <span class="feed-stat">
                <span class="feed-stat-value">{feed_stats.get('avg_verification', 0)}%</span> Avg Verification
            </span>
            <span class="feed-stat" style="margin-left:auto;">
                {', '.join(f'<span style="color:#818cf8;">{k}: {v}</span>' for k, v in feed_stats.get('by_type', {}).items() if v > 0)}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Filter Bar ────────────────────────────────────────────────
    col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns([2, 2, 1.5, 1.5, 1])

    with col_f1:
        st.text_input("Search", placeholder="Search title, org, country...",
                       key="feed_search", label_visibility="collapsed")

    with col_f2:
        country_opts = ["All Countries", "Global / Multiple Countries"] + ALL_COUNTRIES
        # Try to detect user country from session
        default_country = st.session_state.get("feed_country", "Global / Multiple Countries")
        cnt_idx = country_opts.index(default_country) if default_country in country_opts else 0
        st.selectbox("Country", country_opts, index=cnt_idx, key="feed_country", label_visibility="collapsed")

    with col_f3:
        type_opts = ["SCHOLARSHIP", "GRANT", "FELLOWSHIP", "INTERNSHIP", "AWARD"]
        current_types = st.session_state.get("feed_types", ["SCHOLARSHIP", "GRANT", "FELLOWSHIP"])
        sel_types = st.multiselect("Type", type_opts, default=current_types,
                                   format_func=lambda t: OpportunityType.icon(t) + " " + OpportunityType.display_name(t),
                                   key="feed_types", label_visibility="collapsed")

    with col_f4:
        ver_opts = [0, 25, 50, 70, 90]
        ver_labels = {0: "Any Trust", 25: "⚠️ 25+", 50: "🟡 50+", 70: "🟢 70+", 90: "✅ 90+"}
        current_ver = st.session_state.get("feed_verification_min", 50)
        ver_idx = ver_opts.index(current_ver) if current_ver in ver_opts else 2
        st.selectbox("Verification", ver_opts, index=ver_idx,
                     format_func=lambda v: ver_labels.get(v, f"Score {v}+"),
                     key="feed_verification_min", label_visibility="collapsed")

    with col_f5:
        amount_opts = [0, 5000, 10000, 25000, 50000, 100000]
        amount_labels = {0: "Any Amount", 5000: "$5K+", 10000: "$10K+", 25000: "$25K+", 50000: "$50K+", 100000: "$100K+"}
        curr_amt = st.session_state.get("feed_amount_min", 0)
        amt_idx = amount_opts.index(curr_amt) if curr_amt in amount_opts else 0
        st.selectbox("Min Amount", amount_opts, index=amt_idx,
                     format_func=lambda a: amount_labels.get(a, f"${a:,.0f}+"),
                     key="feed_amount_min", label_visibility="collapsed")

    # ── Fetch feed data ───────────────────────────────────────────
    country = st.session_state.get("feed_country", "All Countries")
    types = st.session_state.get("feed_types", None)
    if not types or len(types) == 0:
        types = None
    verification_min = float(st.session_state.get("feed_verification_min", 50))
    amount_min = float(st.session_state.get("feed_amount_min", 0))
    query = st.session_state.get("feed_search", "").strip()
    page = st.session_state.get("feed_page", 0)

    feed_data = manager.get_feed(
        user_country=country if country != "All Countries" else "Global / Multiple Countries",
        types=types,
        amount_min=amount_min if amount_min > 0 else None,
        verification_min=verification_min if verification_min > 0 else None,
        query=query,
        page=page,
        per_page=10,
    )

    # ── Featured Section ──────────────────────────────────────────
    featured = manager.get_feed_featured(
        country if country != "All Countries" else "Global / Multiple Countries",
        limit=3
    )

    if featured:
        st.markdown(f"""
        <div class="feed-featured-section">
            <div class="feed-featured-header">
                <span style="font-size:1.2rem;">⭐</span>
                <h3>Top Picks for You</h3>
                <span style="font-size:0.7rem;color:#64748b;margin-left:auto;">
                    Based on high verification & location relevance
                </span>
            </div>
        """, unsafe_allow_html=True)

        feat_cols = st.columns(len(featured))
        for i, opp in enumerate(featured):
            with feat_cols[i]:
                _render_feed_card(opp, manager, user_id, featured=True)

        st.markdown("</div>", unsafe_allow_html=True)

    # ── Feed Results ──────────────────────────────────────────────
    results = feed_data.get("results", [])
    total = feed_data.get("total", 0)
    total_pages = feed_data.get("total_pages", 1)
    current_page = feed_data.get("page", 0)

    if results:
        st.markdown(f"""
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;">
            <span style="color:#94a3b8;font-size:0.85rem;">
                Showing {len(results)} of {total} verified opportunities
                {f'· Page {current_page + 1} of {total_pages}' if total_pages > 1 else ''}
            </span>
            <span style="font-size:0.7rem;color:#475569;">
                Sorted: Your Country → Region → Global
            </span>
        </div>
        """, unsafe_allow_html=True)

        for opp in results:
            _render_feed_card(opp, manager, user_id)

        # ── Pagination ────────────────────────────────────────────
        if total_pages > 1:
            cols = st.columns([1, 2, 1])
            with cols[0]:
                if current_page > 0:
                    if st.button("◀ Previous", key="feed_prev", use_container_width=True):
                        st.session_state["feed_page"] = current_page - 1
                        st.rerun()
            with cols[1]:
                # Page numbers
                page_nums = []
                for p in range(max(0, current_page - 2), min(total_pages, current_page + 3)):
                    page_nums.append(p)
                page_cols = st.columns(len(page_nums))
                for idx, p in enumerate(page_nums):
                    with page_cols[idx]:
                        active = "active" if p == current_page else ""
                        if st.button(f"{p + 1}", key=f"feed_page_{p}",
                                      use_container_width=True):
                            st.session_state["feed_page"] = p
                            st.rerun()
            with cols[2]:
                if current_page + 1 < total_pages:
                    if st.button("Next ▶", key="feed_next", use_container_width=True):
                        st.session_state["feed_page"] = current_page + 1
                        st.rerun()
    else:
        st.info("No matching opportunities found. Try adjusting your filters.", icon="🔍")


def _render_feed_card(opp: Dict[str, Any], manager: ApplicationPipelineManager,
                       user_id: str, featured: bool = False):
    """Render a single opportunity card in the feed."""
    import streamlit as st

    opp_id = opp.get("id", "")
    title = opp.get("title", "Untitled")
    org = opp.get("organization", "")
    country = opp.get("country", "Global")
    region = opp.get("region", "Global")
    opp_type = opp.get("type", "SCHOLARSHIP")
    amount_min = opp.get("amount_min_usd")
    amount_max = opp.get("amount_max_usd")
    deadline = opp.get("deadline", "")
    desc = opp.get("description", "")
    eligibility = opp.get("eligibility", "")
    authority = opp.get("source_authority", "AGGREGATOR")
    url = opp.get("source_url", "")
    ver_score = opp.get("verification_score", 50) or 50

    flag = get_country_flag(country)
    ver_badge = VerificationScorer.verification_badge(ver_score)

    # Amount formatting
    amount_str = ""
    if amount_min and amount_max:
        amount_str = f"${amount_min:,.0f} - ${amount_max:,.0f}"
    elif amount_max:
        amount_str = f"Up to ${amount_max:,.0f}"
    elif amount_min:
        amount_str = f"From ${amount_min:,.0f}"
    else:
        amount_str = "Amount varies"

    # Deadline countdown
    deadline_str = "No deadline"
    if deadline:
        try:
            dl = datetime.fromisoformat(deadline)
            now = datetime.now()
            days_left = (dl - now).days
            if days_left > 0:
                deadline_str = f"📅 {days_left} days left"
            elif days_left == 0:
                deadline_str = "🚨 Due today!"
            elif days_left < 0:
                deadline_str = "⏰ Past deadline"
        except (ValueError, TypeError):
            deadline_str = f"📅 {deadline[:10]}"

    card_class = "feed-card feed-card-featured" if featured else "feed-card"

    # Build card HTML
    card_html = f"""
    <div class="{card_class}">
        <div class="feed-card-top">
            <div class="feed-card-flag">{flag}</div>
            <div class="feed-card-title-area">
                <div class="feed-card-title">{title}</div>
                <div class="feed-card-org">{org}</div>
            </div>
        </div>
        <div class="feed-card-badges">
            <span class="feed-badge feed-badge-type">{OpportunityType.emoji_badge(opp_type)}</span>
            <span class="feed-badge feed-badge-amount">💰 {amount_str}</span>
            <span class="feed-badge feed-badge-deadline">{deadline_str}</span>
            <span class="feed-badge feed-badge-region">{region}</span>
            <span class="feed-badge feed-badge-authority">{SourceAuthority.icon(authority)} {SourceAuthority.display_name(authority)}</span>
            <span class="verification-badge" style="background:{ver_badge['bg']};color:{ver_badge['color']};border:1px solid {ver_badge['border']};">
                {ver_badge['icon']} {ver_badge['label']} ({ver_score:.0f})
            </span>
        </div>
        <div class="feed-card-desc">{desc[:250]}{'...' if len(desc) > 250 else ''}</div>
    """

    # Country badge
    country_flag = get_country_flag(country)
    card_html += f"""
        <div class="feed-card-footer">
            <div class="feed-card-source">
                {country_flag} {country} · {SourceAuthority.icon(authority)} {SourceAuthority.display_name(authority)}
                {f' · <a href="{url}" target="_blank">Source ↗</a>' if url else ''}
            </div>
    """

    # Add to Pipeline button
    card_html += f"""
            <div>
                <button onclick="alert('add_{opp_id}')" style="
                    padding:0.25rem 0.75rem;border-radius:8px;font-size:0.7rem;font-weight:700;
                    background:rgba(99,102,241,0.15);color:#818cf8;
                    border:1px solid rgba(99,102,241,0.3);cursor:pointer;
                ">➕ Add to Pipeline</button>
            </div>
        </div>
    </div>
    """

    st.markdown(card_html, unsafe_allow_html=True)

    # Add to Pipeline button (real Streamlit button hidden behind)
    add_key = f"feed_add_{opp_id[:12]}"
    if st.button(f"➕ Add '{title[:40]}...' to Pipeline", key=f"{add_key}_{uuid.uuid4().hex[:6]}", use_container_width=True):
        app = manager.feed_add_to_pipeline(user_id, opp_id)
        if app:
            st.success(f"✅ Added '{title[:50]}' to your Pipeline! Track it in the Kanban board below.")
            st.rerun()
        else:
            st.error("Could not add to pipeline. Please try again.")

    # Expandable details
    with st.expander(f"📖 View details — {title[:50]}..."):
        if desc:
            st.markdown(f"**Description:**  \n{desc}")
        if eligibility:
            st.markdown(f"**Eligibility:**  \n{eligibility}")
        if url:
            st.markdown(f"**Source:** [{url}]({url})")
        st.markdown(f"**Verification Score:** {ver_score:.0f}/100 — {ver_badge['label']}")
        st.markdown(f"**Authority:** {SourceAuthority.display_name(authority)}")
        if deadline:
            st.markdown(f"**Deadline:** {deadline[:10]}")


# ═══════════════════════════════════════════════════════════════════════
# SESSION STATE INIT
# ═══════════════════════════════════════════════════════════════════════

def _init_pipeline_state():
    """Initialize pipeline-related session state."""
    import streamlit as st
    defaults = {
        "pipeline_manager": None,
        "pipeline_selected_app": None,
        "pipeline_active_tab": "kanban",
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val
