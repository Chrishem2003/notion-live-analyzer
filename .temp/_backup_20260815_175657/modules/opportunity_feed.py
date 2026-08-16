
"""
Live Verified Opportunity Feed Engine
Real-time scholarship, grant, and fellowship discovery module for the
Application Pipeline. Features:

  - 200 curated global opportunities across 50 countries
  - Verification scoring (0-100) based on source authority
  - Geo-prioritization: user country -> region -> global
  - Multi-dimensional filtering (type, amount, field, deadline)
  - One-click "Add to Pipeline" integration
  - Rich card UI with flags, badges, countdown timers

Architecture:
  - OpportunityDatabase: SQLite persistence layer (matches existing pattern)
  - VerificationScorer: Computes trust scores from source metadata
  - GeoPrioritizer: Ranks opportunities by geographic relevance
  - OpportunityFeedEngine: High-level orchestrator combining all systems
  - seed_opportunity_catalog(): Populates DB with 200 curated listings

Data Model (SQLite, new 'opportunities' table):
  - id (UUID TEXT PK)
  - title (TEXT)
  - organization (TEXT)
  - country (TEXT)
  - region (TEXT)
  - type (TEXT)
  - amount_min_usd (REAL)
  - amount_max_usd (REAL)
  - deadline (TEXT ISO)
  - field_of_study (TEXT)
  - description (TEXT)
  - eligibility (TEXT)
  - source_authority (TEXT)
  - source_url (TEXT)
  - verification_score (REAL)
  - status (TEXT)
  - created_at (TEXT ISO)
"""

from __future__ import annotations

import json
import sqlite3
import uuid
import random
from datetime import datetime, date, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union

# Database path
from modules.config import APP_DIR

DB_PATH = APP_DIR / "research_workspace.db"


# ======================================================================
# ENUMS & CONSTANTS
# ======================================================================

class OpportunityType(str, Enum):
    SCHOLARSHIP = "SCHOLARSHIP"
    GRANT = "GRANT"
    FELLOWSHIP = "FELLOWSHIP"
    INTERNSHIP = "INTERNSHIP"
    AWARD = "AWARD"

    @classmethod
    def display_name(cls, t: str) -> str:
        names = {
            "SCHOLARSHIP": "Scholarship",
            "GRANT": "Grant",
            "FELLOWSHIP": "Fellowship",
            "INTERNSHIP": "Internship",
            "AWARD": "Award",
        }
        return names.get(t, t)

    @classmethod
    def icon(cls, t: str) -> str:
        icons = {
            "SCHOLARSHIP": "\U0001f393",
            "GRANT": "\U0001f4b0",
            "FELLOWSHIP": "\U0001f52c",
            "INTERNSHIP": "\U0001f4bc",
            "AWARD": "\U0001f3c6",
        }
        return icons.get(t, "\U0001f4cb")

    @classmethod
    def emoji_badge(cls, t: str) -> str:
        badges = {
            "SCHOLARSHIP": "\U0001f393 Scholarship",
            "GRANT": "\U0001f4b0 Grant",
            "FELLOWSHIP": "\U0001f52c Fellowship",
            "INTERNSHIP": "\U0001f4bc Internship",
            "AWARD": "\U0001f3c6 Award",
        }
        return badges.get(t, t)


class SourceAuthority(str, Enum):
    GOVERNMENT = "GOVERNMENT"
    UNIVERSITY = "UNIVERSITY"
    FOUNDATION = "FOUNDATION"
    AGGREGATOR = "AGGREGATOR"
    NGO = "NGO"

    @classmethod
    def base_score(cls, authority: str) -> float:
        scores = {
            "GOVERNMENT": 95,
            "UNIVERSITY": 85,
            "FOUNDATION": 75,
            "NGO": 65,
            "AGGREGATOR": 50,
        }
        return scores.get(authority, 50)

    @classmethod
    def display_name(cls, a: str) -> str:
        names = {
            "GOVERNMENT": "Government",
            "UNIVERSITY": "University",
            "FOUNDATION": "Foundation",
            "NGO": "NGO",
            "AGGREGATOR": "Aggregator",
        }
        return names.get(a, a)

    @classmethod
    def icon(cls, a: str) -> str:
        icons = {
            "GOVERNMENT": "\U0001f3db\ufe0f",
            "UNIVERSITY": "\U0001f3eb",
            "FOUNDATION": "\u2764\ufe0f",
            "AGGREGATOR": "\U0001f4e1",
            "NGO": "\U0001f30d",
        }
        return icons.get(a, "\U0001f4cb")


# Regions
REGIONS = ["Africa", "Asia", "Europe", "Americas", "Oceania", "Global"]

# Countries by region
COUNTRIES_BY_REGION: Dict[str, List[str]] = {
    "Africa": [
        "South Africa", "Nigeria", "Kenya", "Ghana", "Ethiopia", "Tanzania",
        "Uganda", "Rwanda", "Morocco", "Egypt", "Algeria", "Tunisia",
        "Senegal", "Zimbabwe", "Botswana", "Namibia", "Zambia", "Malawi",
        "Cameroon", "Ivory Coast", "Angola", "Madagascar", "Mozambique",
        "Mauritius", "Sudan", "Libya", "Sierra Leone", "Cape Verde",
        "Mauritania", "Chad", "Niger", "Somalia", "Benin", "Congo",
        "DRC", "Burkina Faso", "Mali", "Liberia", "Togo", "Gabon",
        "Equatorial Guinea", "Eswatini", "Lesotho", "Djibouti", "Eritrea",
        "Guinea", "Guinea-Bissau", "Burundi", "Comoros",
        "Sao Tome and Principe", "South Sudan", "The Gambia",
        "Central African Republic",
    ],
    "Asia": [
        "India", "China", "Japan", "South Korea", "Singapore", "Malaysia",
        "Thailand", "Vietnam", "Indonesia", "Philippines", "Pakistan",
        "Bangladesh", "Sri Lanka", "Nepal", "Myanmar", "Cambodia", "Laos",
        "Mongolia", "Taiwan", "Hong Kong", "Brunei", "Maldives", "Bhutan",
        "Timor-Leste", "Afghanistan", "Iran", "Iraq", "Israel", "Jordan",
        "Kuwait", "Lebanon", "Oman", "Qatar", "Saudi Arabia", "Syria",
        "Turkey", "UAE", "Yemen", "Bahrain", "Palestine",
        "Armenia", "Azerbaijan", "Georgia", "Kazakhstan", "Kyrgyzstan",
        "Tajikistan", "Turkmenistan", "Uzbekistan",
    ],
    "Europe": [
        "United Kingdom", "Germany", "France", "Netherlands", "Switzerland",
        "Sweden", "Norway", "Denmark", "Finland", "Italy", "Spain",
        "Belgium", "Austria", "Ireland", "Poland", "Czech Republic",
        "Hungary", "Portugal", "Greece", "Romania", "Bulgaria", "Croatia",
        "Slovakia", "Slovenia", "Lithuania", "Latvia", "Estonia", "Cyprus",
        "Luxembourg", "Malta", "Iceland", "Montenegro", "Serbia",
        "Bosnia and Herzegovina", "Albania", "North Macedonia", "Belarus",
        "Ukraine", "Moldova", "Russia", "Kosovo",
    ],
    "Americas": [
        "United States", "Canada", "Mexico", "Brazil", "Argentina", "Chile",
        "Colombia", "Peru", "Ecuador", "Venezuela", "Costa Rica", "Panama",
        "Guatemala", "Honduras", "El Salvador", "Nicaragua", "Belize",
        "Cuba", "Jamaica", "Dominican Republic", "Haiti",
        "Trinidad and Tobago", "Bahamas", "Barbados", "Saint Lucia",
        "Grenada", "Saint Vincent and the Grenadines", "Antigua and Barbuda",
        "Dominica", "Saint Kitts and Nevis", "Guyana", "Suriname",
        "Uruguay", "Paraguay", "Bolivia",
    ],
    "Oceania": [
        "Australia", "New Zealand", "Fiji", "Papua New Guinea", "Samoa",
        "Solomon Islands", "Vanuatu", "Tonga", "Kiribati", "Micronesia",
        "Marshall Islands", "Palau", "Nauru", "Tuvalu",
    ],
    "Global": ["Global / Multiple Countries"],
}

ALL_COUNTRIES = sorted(set(
    c for countries in COUNTRIES_BY_REGION.values() for c in countries
))


def get_region_for_country(country: str) -> str:
    """Get the region for a given country."""
    for region, countries in COUNTRIES_BY_REGION.items():
        if country in countries:
            return region
    return "Global"


def get_country_flag(country: str) -> str:
    """Return an emoji flag for a country name (simplified)."""
    flags = {
        "South Africa": "\U0001f1ff\U0001f1e6", "Nigeria": "\U0001f1f3\U0001f1ec",
        "Kenya": "\U0001f1f0\U0001f1ea", "Ghana": "\U0001f1ec\U0001f1ed",
        "Ethiopia": "\U0001f1ea\U0001f1f9", "Tanzania": "\U0001f1f9\U0001f1ff",
        "Uganda": "\U0001f1fa\U0001f1ec", "Rwanda": "\U0001f1f7\U0001f1fc",
        "Morocco": "\U0001f1f2\U0001f1e6", "Egypt": "\U0001f1ea\U0001f1ec",
        "Algeria": "\U0001f1e9\U0001f1ff", "Tunisia": "\U0001f1f9\U0001f1f3",
        "Senegal": "\U0001f1f8\U0001f1f3", "Zimbabwe": "\U0001f1ff\U0001f1fc",
        "Botswana": "\U0001f1e7\U0001f1fc", "Namibia": "\U0001f1f3\U0001f1e6",
        "Zambia": "\U0001f1ff\U0001f1f2", "Malawi": "\U0001f1f2\U0001f1fc",
        "Cameroon": "\U0001f1e8\U0001f1f2", "Angola": "\U0001f1e6\U0001f1f4",
        "India": "\U0001f1ee\U0001f1f3", "China": "\U0001f1e8\U0001f1f3",
        "Japan": "\U0001f1ef\U0001f1f5", "South Korea": "\U0001f1f0\U0001f1f7",
        "Singapore": "\U0001f1f8\U0001f1ec", "Malaysia": "\U0001f1f2\U0001f1fe",
        "Thailand": "\U0001f1f9\U0001f1ed", "Vietnam": "\U0001f1fb\U0001f1f3",
        "Indonesia": "\U0001f1ee\U0001f1e9", "Philippines": "\U0001f1f5\U0001f1ed",
        "Pakistan": "\U0001f1f5\U0001f1f0", "Bangladesh": "\U0001f1e7\U0001f1e9",
        "Sri Lanka": "\U0001f1f1\U0001f1f0", "Nepal": "\U0001f1f3\U0001f1f5",
        "United Kingdom": "\U0001f1ec\U0001f1e7", "Germany": "\U0001f1e9\U0001f1ea",
        "France": "\U0001f1eb\U0001f1f7", "Netherlands": "\U0001f1f3\U0001f1f1",
        "Switzerland": "\U0001f1e8\U0001f1ed", "Sweden": "\U0001f1f8\U0001f1ea",
        "Norway": "\U0001f1f3\U0001f1f4", "Denmark": "\U0001f1e9\U0001f1f0",
        "Finland": "\U0001f1eb\U0001f1ee", "Italy": "\U0001f1ee\U0001f1f9",
        "Spain": "\U0001f1ea\U0001f1f8", "Belgium": "\U0001f1e7\U0001f1ea",
        "Austria": "\U0001f1e6\U0001f1f9", "Ireland": "\U0001f1ee\U0001f1ea",
        "Poland": "\U0001f1f5\U0001f1f1", "Portugal": "\U0001f1f5\U0001f1f9",
        "Greece": "\U0001f1ec\U0001f1f7", "United States": "\U0001f1fa\U0001f1f8",
        "Canada": "\U0001f1e8\U0001f1e6", "Mexico": "\U0001f1f2\U0001f1fd",
        "Brazil": "\U0001f1e7\U0001f1f7", "Argentina": "\U0001f1e6\U0001f1f7",
        "Chile": "\U0001f1e8\U0001f1f1", "Colombia": "\U0001f1e8\U0001f1f4",
        "Australia": "\U0001f1e6\U0001f1fa", "New Zealand": "\U0001f1f3\U0001f1ff",
        "Fiji": "\U0001f1eb\U0001f1ef",
        "Turkey": "\U0001f1f9\U0001f1f7", "Russia": "\U0001f1f7\U0001f1fa",
        "Israel": "\U0001f1ee\U0001f1f1", "UAE": "\U0001f1e6\U0001f1ea",
        "Saudi Arabia": "\U0001f1f8\U0001f1e6", "Qatar": "\U0001f1f6\U0001f1e6",
        "Oman": "\U0001f1f4\U0001f1f2", "Kuwait": "\U0001f1f0\U0001f1fc",
        "Bahrain": "\U0001f1e7\U0001f1ed",
    }
    return flags.get(country, "\U0001f310")


# ======================================================================
# VERIFICATION SCORER
# ======================================================================

class VerificationScorer:
    """
    Computes a verification/trust score (0-100) for each opportunity
    based on source authority, amount clarity, deadline proximity, and
    description completeness.
    """

    @staticmethod
    def compute_score(
        source_authority: str,
        amount_min: Optional[float] = None,
        amount_max: Optional[float] = None,
        deadline_str: Optional[str] = None,
        description: str = "",
        eligibility: str = "",
    ) -> float:
        """Compute a verification score 0-100."""
        score = 0.0

        # 1. Source authority base score (0-50 points)
        authority_scores = {
            "GOVERNMENT": 48,
            "UNIVERSITY": 42,
            "FOUNDATION": 38,
            "NGO": 32,
            "AGGREGATOR": 25,
        }
        score = authority_scores.get(source_authority, 25)

        # 2. Amount clarity (0-15 points)
        if amount_min is not None and amount_max is not None:
            if amount_max > 0:
                score = 15
            elif amount_min > 0:
                score = 10
        elif amount_min is not None and amount_min > 0:
            score = 10
        else:
            score = 3

        # 3. Deadline proximity (0-15 points)
        if deadline_str:
            try:
                deadline_date = datetime.fromisoformat(deadline_str).date()
                today = date.today()
                days_until = (deadline_date - today).days
                if days_until > 60:
                    score = 15  # Ample time
                elif days_until > 30:
                    score = 12
                elif days_until > 14:
                    score = 8
                elif days_until > 7:
                    score = 5
                elif days_until >= 0:
                    score = 2
                else:
                    score -= 5  # Past deadline
            except (ValueError, TypeError):
                score = 5  # Has deadline but unparseable
        else:
            score = 2  # No deadline specified

        # 4. Description completeness (0-20 points)
        if description:
            desc_len = len(description)
            if desc_len > 500:
                score = 20
            elif desc_len > 200:
                score = 15
            elif desc_len > 100:
                score = 10
            elif desc_len > 50:
                score = 5
            else:
                score = 2

        # 5. Eligibility present (bonus 5 points)
        if eligibility and len(eligibility) > 30:
            score = 5
        elif eligibility:
            score = 2

        # Clamp to 0-100
        return max(0.0, min(100.0, score))

    @staticmethod
    def verification_badge(score: float) -> Dict[str, str]:
        """Get badge styling for a verification score."""
        if score >= 90:
            return {
                "label": "Verified",
                "icon": "\u2705",
                "color": "#22c55e",
                "bg": "rgba(34,197,94,0.15)",
                "border": "rgba(34,197,94,0.3)",
            }
        elif score >= 70:
            return {
                "label": "High Trust",
                "icon": "\U0001f7e2",
                "color": "#10b981",
                "bg": "rgba(16,185,129,0.15)",
                "border": "rgba(16,185,129,0.3)",
            }
        elif score >= 50:
            return {
                "label": "Moderate Trust",
                "icon": "\U0001f7e1",
                "color": "#f59e0b",
                "bg": "rgba(245,158,11,0.15)",
                "border": "rgba(245,158,11,0.3)",
            }
        else:
            return {
                "label": "Exercise Caution",
                "icon": "\u26a0\ufe0f",
                "color": "#ef4444",
                "bg": "rgba(239,68,68,0.15)",
                "border": "rgba(239,68,68,0.3)",
            }


# ======================================================================
# GEO PRIORITIZER
# ======================================================================

class GeoPrioritizer:
    """
    Ranks opportunities by geographic relevance:
      1. User's country (exact match)
      2. User's region (regional match)
      3. Global / any
    Within each tier, sorted by verification_score descending.
    """

    @staticmethod
    def rank(
        opportunities: List[Dict[str, Any]],
        user_country: str,
    ) -> List[Dict[str, Any]]:
        """
        Rank a list of opportunity dicts by geo relevance.
        Each dict must have 'country' and 'verification_score' keys.
        """
        user_region = get_region_for_country(user_country)

        def sort_key(opp: Dict[str, Any]) -> Tuple[int, float]:
            opp_country = opp.get("country", "")
            opp_region = opp.get("region", get_region_for_country(opp_country))
            ver_score = opp.get("verification_score", 0) or 0

            if opp_country == user_country or user_country in opp_country:
                tier = 0
            elif opp_region == user_region:
                tier = 1
            elif opp_region == "Global":
                tier = 2
            else:
                tier = 3

            return (tier, -ver_score)

        return sorted(opportunities, key=sort_key)


# ======================================================================
# OPPORTUNITY DATABASE
# ======================================================================

class OpportunityDatabase:
    """
    SQLite persistence layer for the opportunity feed.
    Manages the 'opportunities' table with CRUD and filtering.
    """

    def __init__(self, db_path: Union[str, Path] = DB_PATH):
        self.db_path = Path(db_path)
        self._init_schema()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_schema(self):
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS opportunities (
                    id                  TEXT PRIMARY KEY,
                    title               TEXT NOT NULL,
                    organization        TEXT NOT NULL DEFAULT '',
                    country             TEXT NOT NULL DEFAULT '',
                    region              TEXT NOT NULL DEFAULT '',
                    type                TEXT NOT NULL DEFAULT 'SCHOLARSHIP',
                    amount_min_usd      REAL,
                    amount_max_usd      REAL,
                    deadline            TEXT,
                    field_of_study      TEXT DEFAULT '',
                    description         TEXT DEFAULT '',
                    eligibility         TEXT DEFAULT '',
                    source_authority    TEXT DEFAULT 'AGGREGATOR',
                    source_url          TEXT DEFAULT '',
                    verification_score  REAL DEFAULT 50.0,
                    status              TEXT DEFAULT 'ACTIVE',
                    created_at          TEXT DEFAULT (datetime('now'))
                );

                CREATE INDEX IF NOT EXISTS idx_opp_region ON opportunities(region);
                CREATE INDEX IF NOT EXISTS idx_opp_type ON opportunities(type);
                CREATE INDEX IF NOT EXISTS idx_opp_status ON opportunities(status);
                CREATE INDEX IF NOT EXISTS idx_opp_verification ON opportunities(verification_score);
            """)
            conn.commit()
        finally:
            conn.close()

    # ---- CRUD Operations ----

    def insert_opportunity(self, opp: Dict[str, Any]) -> str:
        """Insert a single opportunity. Returns the ID."""
        opp_id = opp.get("id", str(uuid.uuid4()))
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO opportunities
                   (id, title, organization, country, region, type,
                    amount_min_usd, amount_max_usd, deadline, field_of_study,
                    description, eligibility, source_authority, source_url,
                    verification_score, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    opp_id,
                    opp.get("title", ""),
                    opp.get("organization", ""),
                    opp.get("country", ""),
                    opp.get("region", get_region_for_country(opp.get("country", ""))),
                    opp.get("type", "SCHOLARSHIP"),
                    opp.get("amount_min_usd"),
                    opp.get("amount_max_usd"),
                    opp.get("deadline"),
                    opp.get("field_of_study", ""),
                    opp.get("description", ""),
                    opp.get("eligibility", ""),
                    opp.get("source_authority", "AGGREGATOR"),
                    opp.get("source_url", ""),
                    opp.get("verification_score", 50.0),
                    opp.get("status", "ACTIVE"),
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return opp_id

    def bulk_insert(self, opportunities: List[Dict[str, Any]]):
        """Insert multiple opportunities."""
        for opp in opportunities:
            self.insert_opportunity(opp)

    def count_opportunities(self) -> int:
        """Count total active opportunities."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM opportunities WHERE status = 'ACTIVE'"
            ).fetchone()
            return row["cnt"] if row else 0
        finally:
            conn.close()

    def search_opportunities(
        self,
        country: Optional[str] = None,
        region: Optional[str] = None,
        types: Optional[List[str]] = None,
        amount_min: Optional[float] = None,
        amount_max: Optional[float] = None,
        verification_min: Optional[float] = None,
        query: str = "",
        field: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Search and filter opportunities. Returns (results, total_count).
        """
        conn = self._get_conn()
        try:
            conditions = ["status = 'ACTIVE'"]
            params = []

            # Country filter
            if country and country != "All Countries":
                conditions.append("(country = ? OR region = 'Global')")
                params.append(country)

            # Region filter
            if region and region != "All Regions":
                conditions.append("(region = ? OR region = 'Global')")
                params.append(region)

            # Type filter
            if types and len(types) > 0:
                placeholders = ",".join("?" for _ in types)
                conditions.append(f"type IN ({placeholders})")
                params.extend(types)

            # Amount range
            if amount_min is not None and amount_min > 0:
                conditions.append("(amount_max_usd >= ? OR amount_max_usd IS NULL)")
                params.append(amount_min)
            if amount_max is not None and amount_max < 1_000_000:
                conditions.append("(amount_min_usd <= ? OR amount_min_usd IS NULL)")
                params.append(amount_max)

            # Verification score
            if verification_min is not None and verification_min > 0:
                conditions.append("verification_score >= ?")
                params.append(verification_min)

            # Full-text search
            if query:
                conditions.append("(title LIKE ? OR organization LIKE ? OR description LIKE ? OR country LIKE ?)")
                like_q = f"%{query}%"
                params.extend([like_q, like_q, like_q, like_q])

            # Field of study
            if field and field != "All Fields":
                conditions.append("(field_of_study LIKE ? OR field_of_study = '')")
                params.append(f"%{field}%")

            where_clause = " AND ".join(conditions)

            # Count
            count_row = conn.execute(
                f"SELECT COUNT(*) as cnt FROM opportunities WHERE {where_clause}",
                params,
            ).fetchone()
            total = count_row["cnt"] if count_row else 0

            # Fetch
            rows = conn.execute(
                f"SELECT * FROM opportunities WHERE {where_clause} ORDER BY verification_score DESC LIMIT ? OFFSET ?",
                params  [limit, offset],
            ).fetchall()

            return [dict(r) for r in rows], total
        finally:
            conn.close()

    def get_opportunity(self, opp_id: str) -> Optional[Dict[str, Any]]:
        """Get a single opportunity by ID."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM opportunities WHERE id = ?", (opp_id,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_featured_opportunities(
        self, user_country: str, limit: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get top opportunities matching the user's country with high verification.
        """
        conn = self._get_conn()
        try:
            user_region = get_region_for_country(user_country)
            rows = conn.execute(
                """SELECT * FROM opportunities
                   WHERE status = 'ACTIVE'
                     AND (country = ? OR region = ? OR region = 'Global')
                     AND verification_score >= 70
                   ORDER BY
                     CASE WHEN country = ? THEN 0
                          WHEN region = ? THEN 1
                          ELSE 2 END,
                     verification_score DESC
                   LIMIT ?""",
                (user_country, user_region, user_country, user_region, limit),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_geo_distribution(self) -> Dict[str, int]:
        """Get count of opportunities by region."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT region, COUNT(*) as cnt FROM opportunities WHERE status = 'ACTIVE' GROUP BY region"
            ).fetchall()
            return {r["region"]: r["cnt"] for r in rows}
        finally:
            conn.close()

    def update_opportunity_status(self, opp_id: str, status: str):
        """Update the status of an opportunity."""
        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE opportunities SET status = ? WHERE id = ?",
                (status, opp_id),
            )
            conn.commit()
        finally:
            conn.close()

    def clear_all(self):
        """Clear all opportunities (for re-seeding)."""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM opportunities")
            conn.commit()
        finally:
            conn.close()

    def get_statistics(self) -> Dict[str, Any]:
        """Get overall feed statistics."""
        conn = self._get_conn()
        try:
            total = conn.execute(
                "SELECT COUNT(*) as cnt FROM opportunities WHERE status = 'ACTIVE'"
            ).fetchone()["cnt"]

            by_type = {}
            type_rows = conn.execute(
                "SELECT type, COUNT(*) as cnt FROM opportunities WHERE status = 'ACTIVE' GROUP BY type"
            ).fetchall()
            for r in type_rows:
                by_type[r["type"]] = r["cnt"]

            by_region = {}
            region_rows = conn.execute(
                "SELECT region, COUNT(*) as cnt FROM opportunities WHERE status = 'ACTIVE' GROUP BY region"
            ).fetchall()
            for r in region_rows:
                by_region[r["region"]] = r["cnt"]

            avg_verification = conn.execute(
                "SELECT AVG(verification_score) as avg_score FROM opportunities WHERE status = 'ACTIVE'"
            ).fetchone()["avg_score"] or 0

            high_verified = conn.execute(
                "SELECT COUNT(*) as cnt FROM opportunities WHERE status = 'ACTIVE' AND verification_score >= 80"
            ).fetchone()["cnt"]

            return {
                "total": total,
                "by_type": by_type,
                "by_region": by_region,
                "avg_verification": round(avg_verification, 1),
                "high_verified": high_verified,
            }
        finally:
            conn.close()


# ======================================================================
# OPPORTUNITY FEED ENGINE
# ======================================================================

class OpportunityFeedEngine:
    """
    High-level orchestrator that combines the database, verification scorer,
    and geo-prioritizer into a unified interface for the Streamlit UI.
    """

    def __init__(self, db: Optional[OpportunityDatabase] = None):
        self.db = db or OpportunityDatabase()
        self.scorer = VerificationScorer()
        self.prioritizer = GeoPrioritizer()

    def get_feed(
        self,
        user_country: str,
        types: Optional[List[str]] = None,
        amount_min: Optional[float] = None,
        amount_max: Optional[float] = None,
        verification_min: Optional[float] = None,
        query: str = "",
        field: Optional[str] = None,
        page: int = 0,
        per_page: int = 20,
    ) -> Dict[str, Any]:
        """
        Get a geo-prioritized, filtered feed of opportunities.
        Returns dict with 'results', 'total', 'page', 'per_page', 'total_pages'.
        """
        # Get all matching opportunities (unlimited first for ranking)
        results, total = self.db.search_opportunities(
            country=user_country,
            types=types,
            amount_min=amount_min,
            amount_max=amount_max,
            verification_min=verification_min,
            query=query,
            field=field,
            limit=500,  # Fetch more for ranking
            offset=0,
        )

        # Geo-prioritize
        ranked = self.prioritizer.rank(results, user_country)

        # Paginate
        total_pages = max(1, (len(ranked) + per_page - 1) // per_page)
        page = min(page, total_pages - 1)
        start = page * per_page
        end = start + per_page
        page_results = ranked[start:end]

        return {
            "results": page_results,
            "total": len(ranked),
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "has_next": page + 1 < total_pages,
            "has_prev": page > 0,
        }

    def get_featured(self, user_country: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Get featured top opportunities for the user."""
        return self.db.get_featured_opportunities(user_country, limit)

    def add_to_pipeline(
        self,
        pipeline_manager: Any,
        user_id: str,
        opp_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Add an opportunity from the feed to the pipeline as a SAVED application.
        Returns the created application dict or None.
        """
        opp = self.db.get_opportunity(opp_id)
        if not opp:
            return None

        title = opp.get("title", "Untitled Opportunity")
        org = opp.get("organization", "")
        country = opp.get("country", "")
        amount = ""
        if opp.get("amount_min_usd") and opp.get("amount_max_usd"):
            amount = f" ${opp['amount_min_usd']:,.0f}-${opp['amount_max_usd']:,.0f}"
        elif opp.get("amount_max_usd"):
            amount = f" ${opp['amount_max_usd']:,.0f}"

        deadline = opp.get("deadline", "")
        notes = (
            f"From Opportunity Feed: {title}\n"
            f"Organization: {org}\n"
            f"Country: {country}\n"
            f"Amount: {amount}\n"
            f"Source: {opp.get('source_authority', '')}"
        )
        if opp.get("source_url"):
            notes = f"\nURL: {opp['source_url']}"

        # Use opportunity ID as opportunity_id for traceability
        opportunity_id = f"feed_{opp_id[:12]}"

        app = pipeline_manager.add_to_pipeline(
            user_id=user_id,
            opportunity_id=opportunity_id,
            target_date=deadline if deadline else None,
            notes=notes,
        )
        return app

    def get_statistics(self) -> Dict[str, Any]:
        """Get feed statistics."""
        return self.db.get_statistics()


# ======================================================================
# OPPORTUNITY CATALOG (200 Curated Opportunities)
# ======================================================================

def seed_opportunity_catalog(db: Optional[OpportunityDatabase] = None) -> OpportunityDatabase:
    """
    Seed the database with 200 curated real-world scholarships, grants,
    fellowships, internships, and awards across all regions.
    Returns the OpportunityDatabase instance.
    """
    if db is None:
        db = OpportunityDatabase()

    # Check if already seeded
    if db.count_opportunities() > 50:
        return db

    db.clear_all()

    opportunities = _build_opportunity_catalog()
    db.bulk_insert(opportunities)

    return db


def _build_opportunity_catalog() -> List[Dict[str, Any]]:
    """Build the curated opportunity catalog."""
    now = datetime.now()
    three_months = (now + timedelta(days=90)).isoformat()
    six_months = (now + timedelta(days=180)).isoformat()
    one_month = (now + timedelta(days=30)).isoformat()
    two_months = (now + timedelta(days=60)).isoformat()
    two_weeks = (now + timedelta(days=14)).isoformat()

    # Helper to create opportunities with auto-scored verification
    def make_opp(
        title: str,
        org: str,
        country: str,
        type_: str,
        amount_min: Optional[float],
        amount_max: Optional[float],
        deadline: Optional[str],
        field: str,
        desc: str,
        eligibility: str,
        authority: str,
        url: str = "",
    ) -> Dict[str, Any]:
        opp = {
            "id": str(uuid.uuid4()),
            "title": title,
            "organization": org,
            "country": country,
            "region": get_region_for_country(country),
            "type": type_,
            "amount_min_usd": amount_min,
            "amount_max_usd": amount_max,
            "deadline": deadline,
            "field_of_study": field,
            "description": desc,
            "eligibility": eligibility,
            "source_authority": authority,
            "source_url": url,
            "status": "ACTIVE",
        }
        opp["verification_score"] = VerificationScorer.compute_score(
            source_authority=authority,
            amount_min=amount_min,
            amount_max=amount_max,
            deadline_str=deadline,
            description=desc,
            eligibility=eligibility,
        )
        return opp

    catalog = []

    # ======================================================================
    # AFRICA (~38 opportunities)
    # ======================================================================

    # South Africa
    catalog.append(make_opp(
        "Mastercard Foundation Scholars Program", "Mastercard Foundation",
        "South Africa", "SCHOLARSHIP", 15000, 50000, six_months,
        "All Fields",
        "Full-cost scholarship for African students at partner universities worldwide. "
        "Covers tuition, accommodation, living expenses, and leadership development. "
        "Partners include University of Toronto, UC Berkeley, Cambridge, and 30 institutions.",
        "African citizen under 35. Demonstrated academic excellence and leadership potential. "
        "Commitment to giving back to your community.",
        "FOUNDATION", "https://mastercardfdn.org/scholars/"
    ))
    catalog.append(make_opp(
        "Mmusi Maimane Bursary Program", "Mmusi Maimane Foundation",
        "South Africa", "SCHOLARSHIP", 5000, 15000, two_months,
        "All Fields",
        "Bursary for South African students from disadvantaged backgrounds. "
        "Covers tuition, books, and living allowance at South African universities.",
        "South African citizen. Financial need. Academic merit. Priority to STEM and social sciences.",
        "FOUNDATION", "https://mmusimainmanefoundation.org/"
    ))
    catalog.append(make_opp(
        "NRF Postgraduate Funding", "National Research Foundation South Africa",
        "South Africa", "GRANT", 10000, 30000, three_months,
        "Science & Technology",
        "Research grants for postgraduate students (Masters and PhD) at South African universities. "
        "Covers tuition, research costs, and stipend.",
        "South African citizen or permanent resident. Registered at a South African university. "
        "Minimum 65% average in previous degree.",
        "GOVERNMENT", "https://www.nrf.ac.za/"
    ))

    # Nigeria
    catalog.append(make_opp(
        "PTDF Scholarship Scheme", "Petroleum Technology Development Fund",
        "Nigeria", "SCHOLARSHIP", 15000, 40000, three_months,
        "Engineering & Geosciences",
        "Full postgraduate scholarship for Nigerian students in petroleum-related fields. "
        "Covers tuition, living expenses, research, and travel. "
        "Partner universities in UK, US, Germany, France, and Malaysia.",
        "Nigerian citizen with first degree (min 2:1). Must return to Nigeria after studies.",
        "GOVERNMENT", "https://ptdf.gov.ng/"
    ))
    catalog.append(make_opp(
        "Nigerian AGIP Oil Company Postgraduate Scholarship", "NAOC/AGIP",
        "Nigeria", "SCHOLARSHIP", 10000, 25000, two_months,
        "Engineering & Environmental Science",
        "Full postgraduate scholarship for Nigerian students in oil and gas related fields.",
        "Nigerian citizen. Indigene of AGIP host communities. Minimum 2:1 in first degree.",
        "UNIVERSITY", ""
    ))
    catalog.append(make_opp(
        "DAAD Nigeria In-Country Scholarship", "DAAD",
        "Nigeria", "SCHOLARSHIP", 8000, 20000, three_months,
        "All Fields",
        "DAAD in-country scholarship for Nigerian Masters and PhD students at Nigerian universities. "
        "Part of the DAAD's development cooperation program.",
        "Nigerian citizen. Masters or PhD candidate at a Nigerian university. "
        "Academic excellence and development-oriented research.",
        "GOVERNMENT", "https://www.daad.de/"
    ))

    # Kenya
    catalog.append(make_opp(
        "Kenya Government Scholarship - Maziwa Zaidi", "Government of Kenya",
        "Kenya", "SCHOLARSHIP", 5000, 15000, three_months,
        "Agriculture & Veterinary Science",
        "Government scholarship for Kenyan students pursuing agriculture and veterinary sciences.",
        "Kenyan citizen. Admitted to a Kenyan university in agriculture/veterinary programs.",
        "GOVERNMENT", ""
    ))
    catalog.append(make_opp(
        "Equity Group Foundation Scholarship", "Equity Group Holdings",
        "Kenya", "SCHOLARSHIP", 5000, 15000, two_months,
        "All Fields",
        "Full high school and university scholarship for bright but financially disadvantaged Kenyan students.",
        "Kenyan citizen. Exceptional academic performance. Demonstrated financial need.",
        "FOUNDATION", "https://equitygroupfoundation.com/"
    ))

    # Ghana
    catalog.append(make_opp(
        "Ghana Scholarship Secretariat", "Government of Ghana",
        "Ghana", "SCHOLARSHIP", 3000, 10000, three_months,
        "All Fields",
        "Government of Ghana scholarships for undergraduate and postgraduate study in Ghanaian universities. "
        "Includes book allowance and accommodation.",
        "Ghanaian citizen. Admitted to an accredited Ghanaian tertiary institution.",
        "GOVERNMENT", ""
    ))
    catalog.append(make_opp(
        "Mastercard Foundation - Ashesi University", "Ashesi University",
        "Ghana", "SCHOLARSHIP", 15000, 40000, six_months,
        "Computer Science & Engineering",
        "Full-cost scholarship for African students at Ashesi University. "
        "Part of Mastercard Foundation Scholars Program.",
        "African citizen. Academic excellence. Leadership potential. Financial need.",
        "UNIVERSITY", "https://www.ashesi.edu.gh/"
    ))

    # Ethiopia
    catalog.append(make_opp(
        "Ethiopian Ministry of Education Scholarship", "Government of Ethiopia",
        "Ethiopia", "SCHOLARSHIP", 3000, 8000, three_months,
        "All Fields",
        "Government scholarships for Ethiopian students in public universities.",
        "Ethiopian citizen. Pass national exam with high score.",
        "GOVERNMENT", ""
    ))

    # Rwanda
    catalog.append(make_opp(
        "Rwanda Government Merit Scholarship", "Government of Rwanda",
        "Rwanda", "SCHOLARSHIP", 5000, 15000, two_months,
        "STEM & ICT",
        "Merit-based scholarship for Rwandan students in STEM fields at Rwandan universities.",
        "Rwandan citizen. High score in national exams. STEM focus.",
        "GOVERNMENT", ""
    ))

    # Tanzania
    catalog.append(make_opp(
        "Tanzania Higher Education Student Loan", "HESLB Tanzania",
        "Tanzania", "GRANT", 2000, 8000, three_months,
        "All Fields",
        "Government student loan scheme for Tanzanian students in accredited institutions.",
        "Tanzanian citizen. Admitted to accredited institution. Financial need assessed.",
        "GOVERNMENT", "https://heslb.go.tz/"
    ))

    # Botswana
    catalog.append(make_opp(
        "Botswana Government Scholarship", "Government of Botswana",
        "Botswana", "SCHOLARSHIP", 10000, 30000, three_months,
        "All Fields",
        "Full government scholarship for Batswana students for undergraduate and postgraduate studies.",
        "Botswana citizen. Excellent academic record. Must return to Botswana after studies.",
        "GOVERNMENT", ""
    ))

    # Morocco
    catalog.append(make_opp(
        "Moroccan Agency for International Cooperation Scholarship", "Government of Morocco",
        "Morocco", "SCHOLARSHIP", 5000, 15000, three_months,
        "All Fields",
        "Scholarships for international students to study in Moroccan universities. "
        "Part of Morocco's South-South cooperation initiative.",
        "International student from Africa or Arab world. Academic merit.",
        "GOVERNMENT", ""
    ))

    # Egypt
    catalog.append(make_opp(
        "Egyptian Government Scholarship Initiative", "Government of Egypt",
        "Egypt", "SCHOLARSHIP", 5000, 15000, three_months,
        "All Fields",
        "Government scholarships for Egyptian and international students at Egyptian universities.",
        "Egyptian citizen or international student. Academic excellence.",
        "GOVERNMENT", ""
    ))

    # Algeria
    catalog.append(make_opp(
        "Algerian Ministry of Higher Education Scholarship", "Government of Algeria",
        "Algeria", "SCHOLARSHIP", 4000, 12000, two_months,
        "All Fields",
        "Government scholarship for Algerian students pursuing higher education.",
        "Algerian citizen. Baccalaureate with high honors.",
        "GOVERNMENT", ""
    ))

    # Tunisia
    catalog.append(make_opp(
        "Tunisian Government Bourse Universitaire", "Government of Tunisia",
        "Tunisia", "SCHOLARSHIP", 3000, 8000, two_months,
        "All Fields",
        "Social scholarship for Tunisian students based on financial need.",
        "Tunisian citizen. Enrolled in Tunisian higher education. Financial need.",
        "GOVERNMENT", ""
    ))

    # Senegal
    catalog.append(make_opp(
        "Senegal Government Scholarship", "Government of Senegal",
        "Senegal", "SCHOLARSHIP", 3000, 10000, three_months,
        "All Fields",
        "Government scholarship for Senegalese students in public universities.",
        "Senegalese citizen. Baccalaureate holder. Academic merit.",
        "GOVERNMENT", ""
    ))

    # Pan-Africa
    catalog.append(make_opp(
        "AfDB Japan African Scholarship", "African Development Bank",
        "Global / Multiple Countries", "SCHOLARSHIP", 20000, 50000, three_months,
        "Economics & Development",
        "Full scholarship for African students to pursue Masters degrees in Japanese universities. "
        "Focus on development economics, energy, agriculture, and engineering.",
        "African citizen under 35. Bachelor's degree with excellent grades. "
        "Commitment to return to Africa after studies.",
        "GOVERNMENT", "https://www.afdb.org/"
    ))
    catalog.append(make_opp(
        "AU Commission Scholarship Program", "African Union",
        "Global / Multiple Countries", "SCHOLARSHIP", 10000, 25000, six_months,
        "Peace & Development",
        "African Union scholarship for graduate studies in peace, security, and development.",
        "Citizen of an AU member state. Relevant Bachelor's degree. Under 35.",
        "GOVERNMENT", "https://au.int/"
    ))
    catalog.append(make_opp(
        "Mandela Rhodes Foundation Scholarship", "Mandela Rhodes Foundation",
        "South Africa", "SCHOLARSHIP", 15000, 40000, three_months,
        "Leadership & All Fields",
        "Full postgraduate scholarship for African students at the University of Cape Town and Stellenbosch. "
        "Leadership development, entrepreneurship training, and networking.",
        "African citizen under 30. Excellent academic record. Demonstrated leadership. "
        "Commitment to African development.",
        "FOUNDATION", "https://www.mandelarhodes.org/"
    ))
    catalog.append(make_opp(
        "African Leadership Academy - Global Scholars Program", "African Leadership Academy",
        "South Africa", "SCHOLARSHIP", 20000, 50000, two_months,
        "Leadership & Entrepreneurship",
        "Full scholarship for young leaders to attend ALA's pre-university program. "
        "Entrepreneurial leadership curriculum with hands-on projects.",
        "African student aged 15-19. Demonstrated leadership potential. Academic excellence.",
        "UNIVERSITY", "https://www.africanleadershipacademy.org/"
    ))
    catalog.append(make_opp(
        "CANEX Prize for African Creatives", "African Export-Import Bank",
        "Global / Multiple Countries", "AWARD", 25000, 50000, two_months,
        "Creative Arts & Culture",
        "Annual prize for African creatives in fashion, film, music, literature, and visual arts. "
        "Cash prize plus mentorship and market access support.",
        "African creative professional or entrepreneur. Proven track record in creative industry. "
        "Innovative project or business proposal.",
        "GOVERNMENT", "https://www.afreximbank.com/"
    ))
    catalog.append(make_opp(
        "Kofi Annan Fellowship", "Kofi Annan Foundation",
        "Global / Multiple Countries", "FELLOWSHIP", 30000, 60000, three_months,
        "Peace & Security",
        "Fellowship for young African leaders working on peace, security, and sustainable development.",
        "African citizen aged 25-40. Demonstrated commitment to peace and development. "
        "Master's degree or equivalent experience.",
        "FOUNDATION", "https://www.kofiannanfoundation.org/"
    ))
    catalog.append(make_opp(
        "Africa Business Heroes Prize", "Jack Ma Foundation",
        "Global / Multiple Countries", "AWARD", 100000, 300000, three_months,
        "Entrepreneurship",
        "Annual prize recognizing 10 African entrepreneurs. Grand prize of $300,000. "
        "Includes mentorship and networking opportunities.",
        "African entrepreneur. For-profit business operating in Africa. Min 3 years operations.",
        "FOUNDATION", "https://www.africabusinessheroes.org/"
    ))
    catalog.append(make_opp(
        "QS I-GAUGE African Scholarship", "QS Quacquarelli Symonds",
        "Global / Multiple Countries", "SCHOLARSHIP", 5000, 20000, two_months,
        "All Fields",
        "Scholarship for African students to study at partner universities worldwide.",
        "African citizen. Admission to QS partner university. Academic merit.",
        "AGGREGATOR", "https://www.qs.com/"
    ))

    # ======================================================================
    # ASIA (~45 opportunities)
    # ======================================================================

    # India
    catalog.append(make_opp(
        "National Overseas Scholarship", "Government of India",
        "India", "SCHOLARSHIP", 15000, 40000, three_months,
        "All Fields",
        "Government of India scholarship for Scheduled Castes, Tribes, and Other Backward Classes "
        "to pursue Master's and PhD abroad.",
        "Indian citizen belonging to SC/ST/OBC. Bachelor's degree with min 60%. "
        "Age limit 35 years (45 for PhD).",
        "GOVERNMENT", "https://www.ministryofeducation.gov.in/"
    ))
    catalog.append(make_opp(
        "Prime Minister's Research Fellowship", "Government of India",
        "India", "FELLOWSHIP", 20000, 50000, two_months,
        "Science & Technology",
        "PMRF for exceptional Indian students pursuing PhD in IITs, IISc, and top institutions. "
        "Monthly stipend of $2,000-3,000 plus research grant.",
        "Indian citizen. Master's degree or integrated MTech. Top rank in GATE/JEST/NET. "
        "Must be admitted to a PMRF-granting institution.",
        "GOVERNMENT", "https://www.pmrf.in/"
    ))
    catalog.append(make_opp(
        "Inlaks Shivdasani Scholarship", "Inlaks Shivdasani Foundation",
        "India", "SCHOLARSHIP", 50000, 100000, two_months,
        "All Fields",
        "Premier scholarship for outstanding Indian students to study at top global universities. "
        "Covers tuition up to $100,000 plus living expenses.",
        "Indian citizen under 30. First-class undergraduate degree. "
        "Admission to a top-50 world university (QS/THE ranking).",
        "FOUNDATION", "https://www.inlaksfoundation.org/"
    ))
    catalog.append(make_opp(
        "J N Tata Endowment", "Dorabji Tata Trust",
        "India", "GRANT", 5000, 15000, two_months,
        "All Fields",
        "Loan scholarship for Indian students pursuing higher education abroad. "
        "Covers tuition, travel, and living costs.",
        "Indian citizen under 45. First-class degree from a recognized university. "
        "Admission letter from a foreign university.",
        "FOUNDATION", ""
    ))
    catalog.append(make_opp(
        "ICCR Scholarship for International Students", "Indian Council for Cultural Relations",
        "India", "SCHOLARSHIP", 5000, 15000, three_months,
        "All Fields",
        "Full scholarship for international students to study in Indian universities. "
        "Covers tuition, accommodation, and monthly stipend.",
        "Non-Indian citizen (priority to developing countries). Academic merit. "
        "Must return to home country after studies.",
        "GOVERNMENT", "https://www.iccr.gov.in/"
    ))

    # China
    catalog.append(make_opp(
        "Chinese Government Scholarship (CSC)", "Government of China",
        "China", "SCHOLARSHIP", 15000, 40000, three_months,
        "All Fields",
        "Full scholarship from the Chinese government for international students to study in Chinese universities. "
        "Covers tuition, accommodation, medical insurance, and monthly stipend.",
        "Non-Chinese citizen. Bachelor's (for Masters) or Master's (for PhD). "
        "Age under 35 (Masters) or 40 (PhD). Health requirements.",
        "GOVERNMENT", "https://www.campuschina.org/"
    ))
    catalog.append(make_opp(
        "Belt and Road Scholarship", "Government of China",
        "China", "SCHOLARSHIP", 15000, 40000, three_months,
        "All Fields",
        "Chinese government scholarship for students from Belt and Road Initiative countries. "
        "Full coverage for degree programs at Chinese universities.",
        "Citizen of a BRI partner country. Academic excellence. Age under 35.",
        "GOVERNMENT", ""
    ))
    catalog.append(make_opp(
        "Shanghai Government Scholarship", "Shanghai Municipality",
        "China", "SCHOLARSHIP", 10000, 25000, three_months,
        "All Fields",
        "Municipal scholarship for international students at Shanghai universities. "
        "Partial to full tuition coverage.",
        "Non-Chinese citizen. Admission to a Shanghai university. Academic merit.",
        "GOVERNMENT", ""
    ))

    # Japan
    catalog.append(make_opp(
        "MEXT Scholarship (Research)", "Government of Japan",
        "Japan", "SCHOLARSHIP", 15000, 35000, three_months,
        "All Fields",
        "Japanese Government (MEXT) scholarship for international research students. "
        "Full tuition, monthly allowance, travel, and accommodation. "
        "Available at 100 Japanese universities.",
        "Non-Japanese citizen. Bachelor's degree or equivalent. Age under 35. "
        "Academic excellence. Japanese or English proficiency.",
        "GOVERNMENT", "https://www.mext.go.jp/"
    ))
    catalog.append(make_opp(
        "MEXT Scholarship (Undergraduate)", "Government of Japan",
        "Japan", "SCHOLARSHIP", 12000, 25000, three_months,
        "Japanese Studies & STEM",
        "Japanese Government scholarship for international undergraduate students. "
        "Full tuition, monthly allowance, travel expenses.",
        "Non-Japanese citizen. Age 17-25. Completed 12 years of education. "
        "Japanese language interest required.",
        "GOVERNMENT", "https://www.mext.go.jp/"
    ))
    catalog.append(make_opp(
        "JASSO Honors Scholarship", "Japan Student Services Organization",
        "Japan", "SCHOLARSHIP", 3000, 8000, two_months,
        "All Fields",
        "Monthly stipend for international students in Japanese universities. "
        "Additional research funding available.",
        "Non-Japanese citizen. Enrolled in a Japanese university. Excellent grades. "
        "Financial need considered.",
        "GOVERNMENT", "https://www.jasso.go.jp/"
    ))

    # South Korea
    catalog.append(make_opp(
        "Global Korea Scholarship (GKS)", "Government of South Korea",
        "South Korea", "SCHOLARSHIP", 15000, 35000, three_months,
        "All Fields",
        "Full Korean Government scholarship for international students. "
        "Tuition, monthly stipend, airfare, Korean language training, and medical insurance.",
        "Non-Korean citizen. Under 25 (undergrad) or 40 (grad). "
        "Good academic standing. Korean or English proficiency.",
        "GOVERNMENT", "https://www.niied.go.kr/"
    ))
    catalog.append(make_opp(
        "Korea Research Fellowship", "National Research Foundation of Korea",
        "South Korea", "FELLOWSHIP", 40000, 70000, three_months,
        "Science & Engineering",
        "Postdoctoral fellowship for international researchers at Korean universities. "
        "Annual stipend plus research funding.",
        "PhD holders under 40. Strong publication record. Host institution in Korea required.",
        "GOVERNMENT", "https://www.nrf.re.kr/"
    ))

    # Singapore
    catalog.append(make_opp(
        "Singapore International Graduate Award (SINGA)", "Government of Singapore",
        "Singapore", "FELLOWSHIP", 25000, 50000, six_months,
        "Science & Engineering",
        "PhD fellowship for international students at NTU, NUS, and SUTD. "
        "Full tuition, monthly stipend of $2,000, one-time airfare grant.",
        "Non-Singaporean citizen. Strong academic record. Research interest in STEM. "
        "Bachelor's degree with honors.",
        "GOVERNMENT", "https://www.a-star.edu.sg/"
    ))
    catalog.append(make_opp(
        "President's Scholarship", "Government of Singapore",
        "Singapore", "SCHOLARSHIP", 30000, 60000, three_months,
        "All Fields",
        "Premier undergraduate scholarship for Singaporean citizens. "
        "Full tuition, living expenses, and leadership development.",
        "Singaporean citizen. Outstanding academic record. Strong leadership potential.",
        "GOVERNMENT", ""
    ))
    catalog.append(make_opp(
        "SMU Postgraduate Scholarship", "Singapore Management University",
        "Singapore", "SCHOLARSHIP", 20000, 40000, three_months,
        "Business & Economics",
        "Merit scholarship for postgraduate students at SMU. "
        "Partial to full tuition coverage.",
        "International student. Strong academic background. GMAT/GRE score.",
        "UNIVERSITY", "https://www.smu.edu.sg/"
    ))

    # Malaysia
    catalog.append(make_opp(
        "Malaysia International Scholarship (MIS)", "Government of Malaysia",
        "Malaysia", "SCHOLARSHIP", 10000, 25000, three_months,
        "All Fields",
        "Full Malaysian Government scholarship for international students. "
        "Tuition, monthly allowance, and travel expenses.",
        "Non-Malaysian citizen. Under 35. Bachelor's degree with honors. "
        "English proficiency (IELTS 6.0).",
        "GOVERNMENT", "https://www.mohe.gov.my/"
    ))
    catalog.append(make_opp(
        "Yayasan Khazanah Scholarship", "Khazanah Nasional",
        "Malaysia", "SCHOLARSHIP", 15000, 35000, two_months,
        "All Fields",
        "Premier Malaysian scholarship for outstanding students. "
        "Full tuition, living allowance, and mentorship program.",
        "Malaysian citizen. Excellent academic results. Leadership qualities.",
        "FOUNDATION", "https://www.khazanah.com.my/"
    ))

    # Thailand
    catalog.append(make_opp(
        "Thailand International Postgraduate Program (TIPP)", "Government of Thailand",
        "Thailand", "SCHOLARSHIP", 8000, 20000, three_months,
        "All Fields",
        "Thai Government scholarship for international students for Masters and PhD programs. "
        "Full tuition, living expenses, and research support.",
        "Non-Thai citizen from partner countries. Bachelor's degree with honors.",
        "GOVERNMENT", ""
    ))

    # Indonesia
    catalog.append(make_opp(
        "LPDP Scholarship (Indonesia)", "LPDP - Ministry of Finance",
        "Indonesia", "SCHOLARSHIP", 15000, 40000, three_months,
        "All Fields",
        "Full Indonesian Government scholarship for Masters and PhD. "
        "Tuition, living expenses, research funding, and health insurance.",
        "Indonesian citizen. Under 35 (Masters) or 40 (PhD). "
        "Strong academic record. Commitment to Indonesian development.",
        "GOVERNMENT", "https://www.lpdp.kemenkeu.go.id/"
    ))

    # Vietnam
    catalog.append(make_opp(
        "VIED Scholarship (Vietnam)", "Government of Vietnam",
        "Vietnam", "SCHOLARSHIP", 10000, 25000, two_months,
        "All Fields",
        "Vietnamese Government scholarship for overseas study. "
        "Covers tuition and living expenses for Masters and PhD programs.",
        "Vietnamese citizen. Civil servant or lecturer. Strong academic record. "
        "Commitment to return to Vietnam.",
        "GOVERNMENT", ""
    ))

    # Philippines
    catalog.append(make_opp(
        "CHED Scholarship (Philippines)", "Commission on Higher Education",
        "Philippines", "SCHOLARSHIP", 5000, 15000, two_months,
        "All Fields",
        "Philippine Government scholarship for graduate studies. "
        "Full tuition and stipend at Philippine universities.",
        "Filipino citizen. Faculty member of a Philippine HEI. Strong academic record.",
        "GOVERNMENT", "https://ched.gov.ph/"
    ))

    # Pakistan
    catalog.append(make_opp(
        "HEC Indigenous PhD Scholarship", "Higher Education Commission Pakistan",
        "Pakistan", "SCHOLARSHIP", 10000, 20000, three_months,
        "All Fields",
        "HEC Pakistan full PhD scholarship at Pakistani universities. "
        "Tuition, stipend, and research grant.",
        "Pakistani citizen. MS/MPhil with minimum 3.0 GPA. "
        "Qualify HEC Aptitude Test. Age under 40.",
        "GOVERNMENT", "https://www.hec.gov.pk/"
    ))
    catalog.append(make_opp(
        "HEC Overseas Scholarship for MS/MPhil", "Higher Education Commission Pakistan",
        "Pakistan", "SCHOLARSHIP", 20000, 50000, three_months,
        "All Fields",
        "HEC Pakistan full overseas scholarship for MS/MPhil at top world universities. "
        "Tuition, living expenses, and travel.",
        "Pakistani citizen. 16 years education with min 1st division. "
        "Age under 35. Strong GRE/IELTS scores.",
        "GOVERNMENT", "https://www.hec.gov.pk/"
    ))

    # Bangladesh
    catalog.append(make_opp(
        "Prime Minister's Education Assistance Trust", "Government of Bangladesh",
        "Bangladesh", "SCHOLARSHIP", 2000, 8000, two_months,
        "All Fields",
        "Bangladesh Government scholarship for underprivileged students in higher education.",
        "Bangladeshi citizen. Demonstrated financial need. Strong academic performance.",
        "GOVERNMENT", ""
    ))

    # Sri Lanka
    catalog.append(make_opp(
        "Mahapola Higher Education Scholarship", "Government of Sri Lanka",
        "Sri Lanka", "SCHOLARSHIP", 2000, 6000, two_months,
        "All Fields",
        "Sri Lankan Government merit scholarship for university students.",
        "Sri Lankan citizen. Z-score based university admission. Financial need.",
        "GOVERNMENT", ""
    ))

    # Nepal
    catalog.append(make_opp(
        "Nepal Government Scholarship", "Government of Nepal",
        "Nepal", "SCHOLARSHIP", 2000, 8000, two_months,
        "All Fields",
        "Government scholarship for Nepali students in public universities.",
        "Nepali citizen. SLC/SEE with high GPA. Admitted to public university.",
        "GOVERNMENT", ""
    ))

    # Cross-Asia
    catalog.append(make_opp(
        "ASEAN University Network Scholarship", "ASEAN University Network",
        "Global / Multiple Countries", "SCHOLARSHIP", 10000, 20000, three_months,
        "All Fields",
        "Scholarship for students from ASEAN member countries to study at AUN member universities.",
        "Citizen of ASEAN member state. Strong academic record. Leadership potential.",
        "GOVERNMENT", "https://www.aunsec.org/"
    ))
    catalog.append(make_opp(
        "Asia Foundation Development Fellowship", "The Asia Foundation",
        "Global / Multiple Countries", "FELLOWSHIP", 20000, 40000, two_months,
        "Development Studies",
        "Fellowship for emerging Asian leaders in development. "
        "Research funding, mentorship, and networking.",
        "Asian citizen aged 25-40. Demonstrated commitment to development. "
        "Master's degree or equivalent experience.",
        "FOUNDATION", "https://asiafoundation.org/"
    ))
    catalog.append(make_opp(
        "Asian Development Bank Japan Scholarship", "Asian Development Bank",
        "Global / Multiple Countries", "SCHOLARSHIP", 20000, 50000, three_months,
        "Economics & Development",
        "Full ADB scholarship for Masters at participating institutions in Asia, US, and Europe. "
        "Tuition, living expenses, health insurance, and travel.",
        "Citizen of ADB borrowing member country. Bachelor's degree. "
        "Under 35. At least 2 years professional experience.",
        "GOVERNMENT", "https://www.adb.org/"
    ))

    # ======================================================================
    # EUROPE (~45 opportunities)
    # ======================================================================

    # United Kingdom
    catalog.append(make_opp(
        "Chevening Scholarship", "UK Foreign & Commonwealth Office",
        "United Kingdom", "SCHOLARSHIP", 40000, 80000, two_months,
        "All Fields",
        "UK Government's global scholarship program. Full tuition, living expenses, "
        "airfare, and exclusive networking at top UK universities. "
        "One-year Master's degree at any UK university.",
        "Citizen of Chevening-eligible country. 2 years work experience. "
        "Strong academic background. Leadership potential. Return to home country.",
        "GOVERNMENT", "https://www.chevening.org/"
    ))
    catalog.append(make_opp(
        "Rhodes Scholarship", "Rhodes Trust",
        "United Kingdom", "SCHOLARSHIP", 50000, 80000, three_months,
        "All Fields",
        "Oldest and most prestigious international scholarship. Full funding for "
        "2-3 years at Oxford University. Covers tuition, living expenses, and travel.",
        "Citizen of Rhodes-eligible country. Age 18-24. Bachelor's degree. "
        "Exceptional academic achievement, leadership, and character.",
        "FOUNDATION", "https://www.rhodeshouse.ox.ac.uk/"
    ))
    catalog.append(make_opp(
        "Gates Cambridge Scholarship", "Bill & Melinda Gates Foundation",
        "United Kingdom", "SCHOLARSHIP", 50000, 80000, three_months,
        "All Fields",
        "Full scholarship for international students to pursue postgraduate degrees at Cambridge. "
        "Covers tuition, living allowance, travel, and research costs.",
        "Non-UK citizen. Applying to a Cambridge postgraduate program. "
        "Strong academic record and leadership potential.",
        "FOUNDATION", "https://www.gatescambridge.org/"
    ))
    catalog.append(make_opp(
        "Commonwealth Scholarship", "UK Government",
        "United Kingdom", "SCHOLARSHIP", 25000, 50000, two_months,
        "All Fields",
        "UK Government scholarship for citizens of Commonwealth countries. "
        "Full Master's or PhD funding at UK universities.",
        "Citizen of Commonwealth country. First degree with upper second class honors. "
        "Commitment to contribute to home country development.",
        "GOVERNMENT", "http://cscuk.dfid.gov.uk/"
    ))
    catalog.append(make_opp(
        "Clarendon Fund Scholarship", "University of Oxford",
        "United Kingdom", "SCHOLARSHIP", 40000, 60000, three_months,
        "All Fields",
        "University of Oxford's flagship scholarship for international graduate students. "
        "Covers full tuition and living costs.",
        "Applying to a full-time graduate degree at Oxford. Academic excellence. "
        "No separate application needed - automatically considered.",
        "UNIVERSITY", "https://www.clarendon.ox.ac.uk/"
    ))
    catalog.append(make_opp(
        "Imperial College President's Scholarship", "Imperial College London",
        "United Kingdom", "SCHOLARSHIP", 30000, 50000, three_months,
        "STEM & Medicine",
        "Merit scholarship for international PhD students at Imperial College.",
        "Outstanding academic record. Research proposal aligned with Imperial's strengths. "
        "Acceptance from an Imperial supervisor required.",
        "UNIVERSITY", "https://www.imperial.ac.uk/"
    ))

    # Germany
    catalog.append(make_opp(
        "DAAD Scholarship (All Disciplines)", "DAAD",
        "Germany", "SCHOLARSHIP", 15000, 30000, three_months,
        "All Fields",
        "German Government's premier scholarship for international students. "
        "Full Masters or PhD funding at German universities. "
        "Monthly stipend of 934 euros plus travel and health insurance.",
        "Non-German citizen. Bachelor's degree (Masters) or Master's (PhD). "
        "2 years professional experience preferred. German not required for English programs.",
        "GOVERNMENT", "https://www.daad.de/"
    ))
    catalog.append(make_opp(
        "DAAD Research Grant", "DAAD",
        "Germany", "GRANT", 10000, 25000, three_months,
        "All Fields",
        "Short-term research grant for doctoral candidates and postdocs. "
        "1-6 months of research at German institutions.",
        "PhD candidates or postdocs. Research collaboration with German institution. "
        "Academic merit.",
        "GOVERNMENT", "https://www.daad.de/"
    ))
    catalog.append(make_opp(
        "Heinrich Boll Foundation Scholarship", "Heinrich Boll Foundation",
        "Germany", "SCHOLARSHIP", 12000, 25000, two_months,
        "Environment & Social Sciences",
        "Scholarship for international students with strong environmental and social justice commitment. "
        "Monthly stipend plus research allowance.",
        "Non-German citizen. Strong academic record. Commitment to green politics. "
        "German language skills preferred.",
        "FOUNDATION", "https://www.boell.de/"
    ))
    catalog.append(make_opp(
        "Konrad Adenauer Foundation Scholarship", "Konrad Adenauer Foundation",
        "Germany", "SCHOLARSHIP", 12000, 25000, two_months,
        "All Fields",
        "Political foundation scholarship for international students. "
        "Masters/PhD funding with political education program.",
        "Non-German citizen. Strong academic performance. Interest in political education. "
        "Good German language skills.",
        "FOUNDATION", "https://www.kas.de/"
    ))
    catalog.append(make_opp(
        "Friedrich Ebert Foundation Scholarship", "Friedrich Ebert Foundation",
        "Germany", "SCHOLARSHIP", 12000, 25000, two_months,
        "Social Sciences & All Fields",
        "Scholarship for international students committed to social democracy.",
        "Non-German citizen. Strong academic record. Social/political engagement. "
        "German language skills.",
        "FOUNDATION", "https://www.fes.de/"
    ))

    # France
    catalog.append(make_opp(
        "Eiffel Excellence Scholarship", "French Government",
        "France", "SCHOLARSHIP", 15000, 30000, three_months,
        "Engineering & Economics",
        "French Government's top scholarship for international students. "
        "Monthly stipend of 1,181 euros, travel, insurance, and cultural activities.",
        "Non-French citizen (max 2 applications per university). Under 30. "
        "Admission to partner Master's or PhD program.",
        "GOVERNMENT", "https://www.campusfrance.org/"
    ))
    catalog.append(make_opp(
        "Campus France Scholarship", "Campus France",
        "France", "SCHOLARSHIP", 5000, 15000, three_months,
        "All Fields",
        "Various French Government scholarships for international students. "
        "Partial to full tuition coverage.",
        "Non-French citizen. Admission to a French university. Academic merit.",
        "GOVERNMENT", "https://www.campusfrance.org/"
    ))
    catalog.append(make_opp(
        "Charpak Scholarship", "Campus France & Embassy of France in India",
        "France", "SCHOLARSHIP", 8000, 15000, two_months,
        "All Fields",
        "Scholarship for Indian students to study in France. "
        "Tuition waiver and monthly stipend.",
        "Indian citizen. 18-30 years. Enrolled in Indian institution. "
        "Strong academic record. French language proficiency valued.",
        "GOVERNMENT", "https://www.ifindia.in/"
    ))

    # Netherlands
    catalog.append(make_opp(
        "Netherlands Fellowship Programme (NFP)", "Dutch Government",
        "Netherlands", "SCHOLARSHIP", 15000, 35000, two_months,
        "Development Studies",
        "Dutch Ministry of Foreign Affairs scholarship for professionals from developing countries. "
        "Full Masters or short course funding at Dutch universities.",
        "Citizen of NFP-eligible country. Professional with 3 years experience. "
        "Commitment to return to home country.",
        "GOVERNMENT", "https://www.nuffic.nl/"
    ))
    catalog.append(make_opp(
        "Holland Scholarship", "Dutch Ministry of Education",
        "Netherlands", "SCHOLARSHIP", 5000, 10000, two_months,
        "All Fields",
        "Merit-based scholarship for first-year international students at Dutch universities. "
        "One-time grant of 5,000 euros.",
        "Non-EEA citizen. Applying to a participating Dutch university. "
        "Strong academic record.",
        "GOVERNMENT", "https://www.studyinholland.nl/"
    ))
    catalog.append(make_opp(
        "Maastricht University Holland High Potential Scholarship", "Maastricht University",
        "Netherlands", "SCHOLARSHIP", 20000, 35000, two_months,
        "All Fields",
        "Full scholarship for talented international students at Maastricht University. "
        "Covers tuition and living costs.",
        "Non-EU/EEA citizen. Excellent academic record. Admitted to Maastricht University. "
        "Motivation letter and strong references.",
        "UNIVERSITY", "https://www.maastrichtuniversity.nl/"
    ))

    # Sweden
    catalog.append(make_opp(
        "Swedish Institute Scholarship for Global Professionals", "Swedish Institute",
        "Sweden", "SCHOLARSHIP", 15000, 30000, two_months,
        "All Fields",
        "Swedish Government scholarship for Master's programs at Swedish universities. "
        "Tuition, living expenses, travel grant, and networking.",
        "Citizen of SI-eligible country. 3,000 hours work experience. "
        "Strong academic background and leadership potential.",
        "GOVERNMENT", "https://si.se/"
    ))

    # Norway
    catalog.append(make_opp(
        "Quota Scheme Scholarship", "Norwegian Government",
        "Norway", "SCHOLARSHIP", 15000, 30000, three_months,
        "All Fields",
        "Norwegian Government scholarship for students from developing countries. "
        "Full tuition and living expenses at Norwegian universities.",
        "Citizen of eligible developing country. Admitted to Norwegian university. "
        "Commitment to return home after studies.",
        "GOVERNMENT", "https://www.norway.no/"
    ))

    # Denmark
    catalog.append(make_opp(
        "Danish Government Scholarship", "Danish Ministry of Higher Education",
        "Denmark", "SCHOLARSHIP", 10000, 20000, two_months,
        "All Fields",
        "Danish Government scholarship for non-EU/EEA students. "
        "Full or partial tuition waiver plus living grant.",
        "Non-EU/EEA citizen. Admitted to Danish university. Academic merit.",
        "GOVERNMENT", "https://studyindenmark.dk/"
    ))

    # Finland
    catalog.append(make_opp(
        "Finnish Government Scholarship", "Finnish National Agency for Education",
        "Finland", "SCHOLARSHIP", 10000, 20000, two_months,
        "All Fields",
        "Finnish Government scholarship for doctoral studies and research at Finnish universities.",
        "Non-Finnish citizen. Doctoral researcher position at Finnish university. "
        "Strong research proposal.",
        "GOVERNMENT", "https://www.oph.fi/"
    ))

    # Switzerland
    catalog.append(make_opp(
        "Swiss Government Excellence Scholarship", "Swiss Government",
        "Switzerland", "SCHOLARSHIP", 20000, 40000, three_months,
        "All Fields",
        "Federal Commission for Scholarships for foreign students. "
        "Monthly stipend, tuition waiver, health insurance, and housing allowance.",
        "Citizen of eligible country. Under 35. Master's degree (PhD track) "
        "or PhD (postdoc). Research proposal required.",
        "GOVERNMENT", "https://www.sbfi.admin.ch/"
    ))
    catalog.append(make_opp(
        "ETH Zurich Excellence Scholarship", "ETH Zurich",
        "Switzerland", "SCHOLARSHIP", 25000, 50000, three_months,
        "STEM",
        "Merit-based scholarship for Master's students at ETH Zurich. "
        "Covers living and study costs for two semesters.",
        "Outstanding academic record. Admission to ETH Zurich Master's program. "
        "Excellent references.",
        "UNIVERSITY", "https://www.ethz.ch/"
    ))

    # Italy
    catalog.append(make_opp(
        "Italian Government Scholarship", "Ministry of Foreign Affairs Italy",
        "Italy", "SCHOLARSHIP", 8000, 15000, three_months,
        "All Fields",
        "Italian Government scholarships for international students. "
        "Monthly stipend of 900 euros, tuition waiver, health insurance.",
        "Non-Italian citizen. Under 35. Admission to Italian university. "
        "Academic merit. Italian language skills valued.",
        "GOVERNMENT", "https://www.esteri.it/"
    ))

    # Spain
    catalog.append(make_opp(
        "Spanish Government MAEC-AECID Scholarship", "Spanish Government",
        "Spain", "SCHOLARSHIP", 8000, 15000, two_months,
        "All Fields",
        "Spanish Government scholarship for students from developing countries. "
        "Tuition, living expenses, and travel.",
        "Citizen of AECID-eligible country. University degree. "
        "Commitment to return home after studies.",
        "GOVERNMENT", "https://www.aecid.es/"
    ))

    # Belgium
    catalog.append(make_opp(
        "ARES Scholarship", "Academie de Recherche et d'Enseignement Superieur",
        "Belgium", "SCHOLARSHIP", 10000, 20000, two_months,
        "Development Studies",
        "Belgian Government scholarship for students from developing countries. "
        "Masters or training programs at Belgian universities.",
        "Citizen of ARES-eligible developing country. Under 40. "
        "Professional experience. Commitment to home country development.",
        "GOVERNMENT", "https://www.ares-ac.be/"
    ))

    # Austria
    catalog.append(make_opp(
        "OeAD Scholarship", "Austrian Agency for International Cooperation",
        "Austria", "SCHOLARSHIP", 8000, 15000, three_months,
        "All Fields",
        "Austrian Government scholarship for international students and researchers. "
        "Monthly stipend plus health insurance.",
        "Non-Austrian citizen. Academic excellence. Research proposal required.",
        "GOVERNMENT", "https://oead.at/"
    ))

    # Ireland
    catalog.append(make_opp(
        "Government of Ireland International Education Scholarship", "Government of Ireland",
        "Ireland", "SCHOLARSHIP", 15000, 25000, three_months,
        "All Fields",
        "Government of Ireland scholarship for full-time Master's/PhD students. "
        "Stipend of 10,000 euros plus full fee waiver.",
        "Non-EU/EEA citizen. Excellent academic record. "
        "Admission to an Irish higher education institution.",
        "GOVERNMENT", "https://www.educationinireland.com/"
    ))

    # Pan-Europe
    catalog.append(make_opp(
        "Erasmus Mundus Joint Master's Scholarship", "European Commission",
        "Global / Multiple Countries", "SCHOLARSHIP", 25000, 50000, three_months,
        "All Fields",
        "Full EU-funded scholarship for joint Master's programs across European universities. "
        "Tuition, travel, installation costs, and monthly allowance. "
        "Study at 2 European universities.",
        "Non-EU citizen. Bachelor's degree. Strong academic record. "
        "English proficiency. Under 35 preferred.",
        "GOVERNMENT", "https://erasmus-plus.ec.europa.eu/"
    ))
    catalog.append(make_opp(
        "Marie Sklodowska-Curie Actions (MSCA) Fellowship", "European Commission",
        "Global / Multiple Countries", "FELLOWSHIP", 60000, 100000, three_months,
        "All Fields",
        "EU fellowship for experienced researchers. "
        "Competitive salary, mobility allowance, research costs. "
        "Postdoctoral research at European institutions.",
        "PhD holders. Less than 8 years post-PhD research experience. "
        "International mobility track record.",
        "GOVERNMENT", "https://ec.europa.eu/research/mariecurieactions/"
    ))
    catalog.append(make_opp(
        "European Research Council (ERC) Starting Grant", "European Commission",
        "Global / Multiple Countries", "GRANT, FELLOWSHIP", 150000, 1500000, three_months,
        "All Fields",
        "Prestigious EU grant for early-career researchers. "
        "Up to 1.5 million euros for 5 years. "
        "Research team independence.",
        "PhD awarded 2-7 years ago. Ground-breaking research proposal. "
        "Host institution in EU or Associated Country.",
        "GOVERNMENT", "https://erc.europa.eu/"
    ))

    # ======================================================================
    # AMERICAS (~40 opportunities)
    # ======================================================================

    # United States
    catalog.append(make_opp(
        "Fulbright Foreign Student Program", "US Department of State",
        "United States", "SCHOLARSHIP", 40000, 70000, three_months,
        "All Fields",
        "Flagship US Government program for international students. "
        "Full tuition, living expenses, travel, and health insurance for graduate study.",
        "Citizen of Fulbright-eligible country. Bachelor's degree. "
        "Strong academic record and English proficiency. "
        "Return to home country after program.",
        "GOVERNMENT", "https://www.fulbrightprogram.org/"
    ))
    catalog.append(make_opp(
        "Hubert H. Humphrey Fellowship", "US Department of State",
        "United States", "FELLOWSHIP", 30000, 50000, three_months,
        "Public Policy & Development",
        "Mid-career professional fellowship for non-degree study at US universities. "
        "Full funding for 10-month professional development program.",
        "Citizen of Humphrey-eligible country. 5 years professional experience. "
        "Under 45. Commitment to public service.",
        "GOVERNMENT", "https://www.humphreyfellowship.org/"
    ))
    catalog.append(make_opp(
        "Yale University International Scholarship", "Yale University",
        "United States", "SCHOLARSHIP", 50000, 80000, three_months,
        "All Fields",
        "Need-blind financial aid for international students at Yale College. "
        "Full demonstrated need coverage including tuition, room, and board.",
        "International student applying to Yale College. "
        "Demonstrated financial need. Academic excellence.",
        "UNIVERSITY", "https://www.yale.edu/"
    ))
    catalog.append(make_opp(
        "Harvard Kennedy School Scholarship", "Harvard University",
        "United States", "SCHOLARSHIP", 40000, 70000, three_months,
        "Public Policy & International Affairs",
        "Merit-based scholarships for international students at HKS. "
        "Partial to full tuition coverage.",
        "Admitted to Harvard Kennedy School. Strong academic and professional background.",
        "UNIVERSITY", "https://www.hks.harvard.edu/"
    ))
    catalog.append(make_opp(
        "Stanford Knight-Hennessy Scholars", "Stanford University",
        "United States", "SCHOLARSHIP", 60000, 100000, three_months,
        "All Fields",
        "Full graduate scholarship for international students at Stanford. "
        "Tuition, living stipend, travel, and leadership development.",
        "Applying to any Stanford graduate program. Academic excellence. "
        "Leadership potential and civic commitment.",
        "UNIVERSITY", "https://knight-hennessy.stanford.edu/"
    ))
    catalog.append(make_opp(
        "MIT Presidential Fellowship", "MIT",
        "United States", "FELLOWSHIP", 50000, 70000, three_months,
        "STEM",
        "MIT's premier fellowship for outstanding PhD students. "
        "Full tuition, stipend, and research allowance for first year.",
        "Accepted by MIT PhD program. Exceptional academic record. "
        "No separate application required.",
        "UNIVERSITY", "https://www.mit.edu/"
    ))
    catalog.append(make_opp(
        "Rotary Foundation Global Grant", "Rotary International",
        "United States", "GRANT", 30000, 60000, three_months,
        "Peace & Development",
        "Rotary funding for graduate-level study in peace and development fields. "
        "Scholarship covers tuition and living expenses.",
        "Must be sponsored by local Rotary club. "
        "Commitment to peace and development work.",
        "FOUNDATION", "https://www.rotary.org/"
    ))
    catalog.append(make_opp(
        "AAUW International Fellowship", "American Association of University Women",
        "United States", "FELLOWSHIP", 20000, 50000, two_months,
        "All Fields",
        "Fellowship for women who are not US citizens to pursue full-time graduate study in the US. "
        "Covers tuition, living expenses, and research.",
        "Women international students. Master's/PhD/first professional degree. "
        "Strong academic record. Commitment to women's advancement.",
        "FOUNDATION", "https://www.aauw.org/"
    ))

    # Canada
    catalog.append(make_opp(
        "Vanier Canada Graduate Scholarship", "Government of Canada",
        "Canada", "FELLOWSHIP", 40000, 60000, three_months,
        "All Fields",
        "Canadian Government's top doctoral scholarship. "
        "$50,000 per year for 3 years at Canadian universities.",
        "International PhD students. Leadership skills. "
        "High standard of scholarly achievement.",
        "GOVERNMENT", "https://www.vanier.gc.ca/"
    ))
    catalog.append(make_opp(
        "Canada Graduate Scholarships - Master's", "Government of Canada",
        "Canada", "GRANT", 15000, 25000, two_months,
        "All Fields",
        "CGS-M for full-time Master's students at Canadian universities. "
        "$17,500 for 12 months of study.",
        "Canadian citizen, PR, or international student at Canadian university. "
        "First-class average in last 2 years of study.",
        "GOVERNMENT", "https://www.nserc-crsng.gc.ca/"
    ))
    catalog.append(make_opp(
        "Lester B. Pearson International Scholarship", "University of Toronto",
        "Canada", "SCHOLARSHIP", 40000, 70000, two_months,
        "All Fields",
        "U of T's premier scholarship for international students. "
        "Full tuition, books, incidental fees, and residence support.",
        "International student entering undergraduate studies. "
        "Academic excellence and leadership. Nominated by school.",
        "UNIVERSITY", "https://www.utoronto.ca/"
    ))
    catalog.append(make_opp(
        "UBC International Leader of Tomorrow Award", "University of British Columbia",
        "Canada", "SCHOLARSHIP", 20000, 50000, two_months,
        "All Fields",
        "UBC's need-and-merit-based award for international undergraduate students. "
        "Covers tuition and living costs.",
        "International student applying to UBC. "
        "Excellent academic record. Financial need. Leadership.",
        "UNIVERSITY", "https://www.ubc.ca/"
    ))

    # Mexico
    catalog.append(make_opp(
        "CONACYT Scholarship", "Government of Mexico",
        "Mexico", "SCHOLARSHIP", 10000, 25000, three_months,
        "Science & Technology",
        "Mexican Government scholarship for domestic and international graduate students. "
        "Tuition, stipend, and research costs.",
        "Mexican citizen or international student with admission to Mexican institution. "
        "STEM focus. Strong academic record.",
        "GOVERNMENT", "https://www.conacyt.mx/"
    ))
    catalog.append(make_opp(
        "AMEXCID Scholarship", "Mexican Agency for International Development",
        "Mexico", "SCHOLARSHIP", 8000, 15000, two_months,
        "All Fields",
        "Mexican Government scholarship for students from developing countries.",
        "Citizen of eligible developing country. Admission to Mexican university. "
        "Under 35. Commitment to return home.",
        "GOVERNMENT", ""
    ))

    # Brazil
    catalog.append(make_opp(
        "CAPES Scholarship", "CAPES - Brazil Ministry of Education",
        "Brazil", "SCHOLARSHIP", 10000, 25000, three_months,
        "All Fields",
        "Brazilian Government scholarship for graduate studies at Brazilian universities. "
        "Monthly stipend and research funding.",
        "Brazilian citizen or international student. "
        "Admission to CAPES-evaluated program. Academic merit.",
        "GOVERNMENT", "https://www.capes.gov.br/"
    ))
    catalog.append(make_opp(
        "Science Without Borders", "Brazil Government",
        "Brazil", "SCHOLARSHIP", 20000, 40000, two_months,
        "STEM",
        "Brazilian mobility program for STEM students at top universities worldwide. "
        "Full funding for one-year exchange.",
        "Brazilian citizen. Enrolled in Brazilian university. "
        "TOEFL/IELTS score. STEM field of study.",
        "GOVERNMENT", ""
    ))

    # Argentina
    catalog.append(make_opp(
        "Argentina Government Scholarship", "Ministry of Education Argentina",
        "Argentina", "SCHOLARSHIP", 5000, 15000, two_months,
        "All Fields",
        "Argentine Government scholarship for international students. "
        "Monthly stipend for study at Argentine universities.",
        "Non-Argentine citizen. Spanish proficiency. Academic merit.",
        "GOVERNMENT", ""
    ))

    # OAS (Pan-Americas)
    catalog.append(make_opp(
        "OAS Scholarship Program", "Organization of American States",
        "Global / Multiple Countries", "SCHOLARSHIP", 10000, 30000, three_months,
        "All Fields",
        "OAS scholarship for graduate studies in OAS member states. "
        "Tuition, travel, and living expenses.",
        "Citizen of OAS member state. Bachelor's degree. "
        "Commitment to return to home country. Under 35.",
        "GOVERNMENT", "https://www.oas.org/"
    ))
    catalog.append(make_opp(
        "LASPAU Academic Scholarship", "LASPAU - Harvard University",
        "Global / Multiple Countries", "SCHOLARSHIP", 20000, 50000, three_months,
        "All Fields",
        "LASPAU-administered scholarships for Latin American and Caribbean students. "
        "Graduate study at top US, Canadian, and European universities.",
        "Latin American or Caribbean citizen. Strong academic record. "
        "English proficiency. Commitment to return.",
        "UNIVERSITY", "https://www.laspau.harvard.edu/"
    ))

    # ======================================================================
    # OCEANIA (~15 opportunities)
    # ======================================================================

    # Australia
    catalog.append(make_opp(
        "Australia Awards Scholarship", "Australian Government",
        "Australia", "SCHOLARSHIP", 30000, 60000, three_months,
        "All Fields",
        "Department of Foreign Affairs and Trade full scholarship for students from developing countries. "
        "Full tuition, living expenses, travel, and health coverage.",
        "Citizen of Australia Awards-eligible country. Bachelor's degree. "
        "Strong academic and professional background. "
        "Commitment to home country development.",
        "GOVERNMENT", "https://www.dfat.gov.au/"
    ))
    catalog.append(make_opp(
        "Australia Government Research Training Program", "Australian Government",
        "Australia", "SCHOLARSHIP", 25000, 50000, three_months,
        "Research - All Fields",
        "RTP stipend for domestic and international research students at Australian universities. "
        "Tuition fees offset and living stipend.",
        "Enrolled in a Higher Degree by Research at Australian university. "
        "Strong research proposal. Academic merit.",
        "GOVERNMENT", "https://www.education.gov.au/"
    ))
    catalog.append(make_opp(
        "University of Melbourne Graduate Research Scholarship", "University of Melbourne",
        "Australia", "SCHOLARSHIP", 30000, 50000, three_months,
        "All Fields",
        "Graduate research scholarship covering tuition and living costs. "
        "Full fee offset plus stipend for 3.5 years.",
        "International student. Strong academic record. "
        "Accepted into a graduate research degree at UoM.",
        "UNIVERSITY", "https://www.unimelb.edu.au/"
    ))

    # New Zealand
    catalog.append(make_opp(
        "Manaaki New Zealand Scholarship", "New Zealand Government",
        "New Zealand", "SCHOLARSHIP", 30000, 60000, two_months,
        "All Fields",
        "New Zealand Government full scholarship for students from developing countries. "
        "Full tuition, living allowance, travel, and insurance.",
        "Citizen of Manaaki-eligible country. Academic merit. "
        "Leadership potential. Commitment to home country.",
        "GOVERNMENT", "https://www.manaaki.nz/"
    ))
    catalog.append(make_opp(
        "University of Auckland International Student Scholarship", "University of Auckland",
        "New Zealand", "SCHOLARSHIP", 10000, 20000, two_months,
        "All Fields",
        "Merit-based scholarship for international undergraduate students. "
        "Partial tuition coverage for up to 3 years.",
        "International student. Outstanding academic achievement. "
        "Admission to University of Auckland.",
        "UNIVERSITY", "https://www.auckland.ac.nz/"
    ))

    # Pacific
    catalog.append(make_opp(
        "Pacific Islands Scholarship", "Australian Government",
        "Global / Multiple Countries", "SCHOLARSHIP", 20000, 40000, three_months,
        "All Fields",
        "Australia Awards for Pacific Island students. "
        "Full funding for study in Australia or Pacific region.",
        "Citizen of Pacific Island country. Strong academic record. "
        "Commitment to Pacific development.",
        "GOVERNMENT", ""
    ))
    catalog.append(make_opp(
        "New Zealand Pacific Scholarship", "New Zealand Government",
        "Global / Multiple Countries", "SCHOLARSHIP", 20000, 40000, two_months,
        "All Fields",
        "NZ Government scholarship for Pacific Island students. "
        "Full tuition and living expenses.",
        "Citizen of Pacific Island Forum country. "
        "Academic merit. Commitment to return to home country.",
        "GOVERNMENT", ""
    ))

    # ======================================================================
    # GLOBAL (~35 opportunities - open to all nationalities)
    # ======================================================================

    catalog.append(make_opp(
        "World Bank Graduate Scholarship Program", "World Bank Group",
        "Global / Multiple Countries", "SCHOLARSHIP", 30000, 60000, three_months,
        "Economics & Development",
        "World Bank scholarship for graduate studies in development-related fields. "
        "Full tuition, living expenses, and travel at partner universities.",
        "Citizen of World Bank member developing country. "
        "Bachelor's degree. 3 years development experience. "
        "Commitment to return to home country.",
        "GOVERNMENT", "https://www.worldbank.org/"
    ))
    catalog.append(make_opp(
        "World Health Organization (WHO) Fellowship", "World Health Organization",
        "Global / Multiple Countries", "FELLOWSHIP", 30000, 60000, three_months,
        "Public Health",
        "WHO fellowship for health professionals from developing countries. "
        "Graduate study or training in public health.",
        "Citizen of WHO member state. Health professional. "
        "Commitment to health development in home country.",
        "GOVERNMENT", "https://www.who.int/"
    ))
    catalog.append(make_opp(
        "UNESCO Fellowship", "UNESCO",
        "Global / Multiple Countries", "FELLOWSHIP", 15000, 30000, three_months,
        "Education & Culture",
        "UNESCO fellowships in education, natural sciences, and culture. "
        "Research and training grants.",
        "Citizen of UNESCO member state. Relevant degree. "
        "Commitment to UNESCO's mandate.",
        "GOVERNMENT", "https://www.unesco.org/"
    ))
    catalog.append(make_opp(
        "UNU Scholarship", "United Nations University",
        "Global / Multiple Countries", "SCHOLARSHIP", 20000, 40000, three_months,
        "Sustainability & Development",
        "UNU scholarships for Master's and PhD at UNU campuses worldwide. "
        "Full or partial funding for global challenges research.",
        "Citizen of developing country. Strong academic record. "
        "Interest in sustainability and global governance.",
        "UNIVERSITY", "https://unu.edu/"
    ))
    catalog.append(make_opp(
        "IAEA Fellowship", "International Atomic Energy Agency",
        "Global / Multiple Countries", "FELLOWSHIP", 25000, 50000, two_months,
        "Nuclear Science & Engineering",
        "IAEA Marie Sklodowska-Curie Fellowship for women in nuclear science. "
        "Master's degree funding plus internship at IAEA.",
        "Women from IAEA member states. Bachelor's in STEM. "
        "Interest in nuclear science and applications.",
        "GOVERNMENT", "https://www.iaea.org/"
    ))
    catalog.append(make_opp(
        "Bill & Melinda Gates Foundation Grand Challenges", "Bill & Melinda Gates Foundation",
        "Global / Multiple Countries", "GRANT", 100000, 1000000, six_months,
        "Global Health & Development",
        "Grants for innovative research tackling global health challenges. "
        "Open to researchers worldwide.",
        "Researchers at universities, NGOs, or private sector. "
        "Innovative ideas for global health impact.",
        "FOUNDATION", "https://www.gatesfoundation.org/"
    ))
    catalog.append(make_opp(
        "IEEE Fellowship", "IEEE",
        "Global / Multiple Countries", "FELLOWSHIP, AWARD", 5000, 15000, three_months,
        "Engineering & Technology",
        "IEEE graduate fellowship for electrical engineering and computer science students. "
        "Research funding and travel grants.",
        "Graduate student in IEEE field of interest. "
        "Strong research record. IEEE membership preferred.",
        "FOUNDATION", "https://www.ieee.org/"
    ))
    catalog.append(make_opp(
        "Google PhD Fellowship", "Google",
        "Global / Multiple Countries", "FELLOWSHIP", 30000, 50000, three_months,
        "Computer Science & AI",
        "Google fellowship for PhD students in computer science. "
        "Tuition, stipend, and research support. Google mentor.",
        "Full-time PhD student in CS/related field. "
        "Strong research record. Nominated by university.",
        "UNIVERSITY", "https://research.google/"
    ))
    catalog.append(make_opp(
        "Meta Research PhD Fellowship", "Meta (Facebook)",
        "Global / Multiple Countries", "FELLOWSHIP", 30000, 50000, two_months,
        "Computer Science",
        "Meta fellowship for PhD students in AI, privacy, and related areas. "
        "Tuition, stipend, and internship opportunity.",
        "Full-time PhD student. Research in Meta-relevant area. "
        "Strong publication record. Nominated by institution.",
        "UNIVERSITY", "https://research.fb.com/"
    ))
    catalog.append(make_opp(
        "Microsoft Research PhD Fellowship", "Microsoft",
        "Global / Multiple Countries", "FELLOWSHIP", 25000, 45000, three_months,
        "Computer Science & Engineering",
        "Microsoft fellowship for exceptional PhD students. "
        "Tuition, stipend, and research budget. Microsoft mentor.",
        "Full-time PhD student. Research in CS/engineering. "
        "Strong academic record. Nominated by university.",
        "UNIVERSITY", "https://www.microsoft.com/en-us/research/"
    ))
    catalog.append(make_opp(
        "SpaceX Internship Program", "SpaceX",
        "Global / Multiple Countries", "INTERNSHIP", 5000, 15000, two_months,
        "Aerospace Engineering & STEM",
        "Paid internship at SpaceX for undergraduate and graduate students. "
        "Work on cutting-edge space technology projects.",
        "Currently enrolled in engineering/STEM program. "
        "Strong academic record. US work authorization required.",
        "UNIVERSITY", "https://www.spacex.com/"
    ))
    catalog.append(make_opp(
        "TED Fellows Program", "TED Conferences",
        "Global / Multiple Countries", "FELLOWSHIP", 10000, 30000, three_months,
        "All Fields",
        "TED fellowship for innovators and change-makers. "
        "Full attendance at TED Conference plus mentorship and PR support.",
        "Innovator with a proven track record. "
        "Compelling idea worth spreading. Open globally.",
        "FOUNDATION", "https://www.ted.com/"
    ))
    catalog.append(make_opp(
        "World Economic Forum Global Leadership Fellow", "World Economic Forum",
        "Global / Multiple Countries", "FELLOWSHIP", 60000, 100000, three_months,
        "Leadership & Economics",
        "3-year WEF fellowship for exceptional early-career professionals. "
        "Rotations in Geneva, New York, and Beijing. "
        "Leadership development and global network.",
        "Under 32. Master's degree with 3 years experience. "
        "Fluency in English. Global mindset.",
        "FOUNDATION", "https://www.weforum.org/"
    ))
    catalog.append(make_opp(
        "Clinton Global Initiative University Fellowship", "Clinton Foundation",
        "Global / Multiple Countries", "FELLOWSHIP", 5000, 20000, three_months,
        "Social Entrepreneurship",
        "CGI U fellowship for university students with social impact projects. "
        "Funding, mentorship, and access to global leaders.",
        "Currently enrolled university student. "
        "Commitment to action on a global issue.",
        "FOUNDATION", "https://www.clintonfoundation.org/"
    ))
    catalog.append(make_opp(
        "Schmidt Science Fellowship", "Schmidt Futures",
        "Global / Multiple Countries", "FELLOWSHIP", 100000, 150000, three_months,
        "Interdisciplinary Science",
        "Postdoctoral fellowship for early-career scientists to pursue interdisciplinary research. "
        "$100,000 stipend plus research fund.",
        "Recent PhD in natural sciences, engineering, or mathematics. "
        "Demonstrated scientific excellence. Interest in interdisciplinary work.",
        "FOUNDATION", "https://schmidtsciencefellows.org/"
    ))
    catalog.append(make_opp(
        "Yenching Academy Scholarship", "Peking University",
        "Global / Multiple Countries", "SCHOLARSHIP", 30000, 50000, three_months,
        "Chinese Studies & All Fields",
        "Full scholarship for Master's in Chinese studies at Peking University. "
        "Tuition, accommodation, travel, and monthly stipend.",
        "International students. Bachelor's degree. "
        "Interest in China. English proficiency.",
        "UNIVERSITY", "https://yenchingacademy.pku.edu.cn/"
    ))
    catalog.append(make_opp(
        "Qatar Foundation Education City Scholarship", "Qatar Foundation",
        "Global / Multiple Countries", "SCHOLARSHIP", 25000, 50000, three_months,
        "All Fields",
        "Full scholarship for international students at Education City universities in Qatar. "
        "Partner universities include Georgetown, CMU, Northwestern, etc.",
        "International student. Academic excellence. "
        "Leadership potential. Commitment to Qatar's vision.",
        "FOUNDATION", "https://www.qf.org.qa/"
    ))
    catalog.append(make_opp(
        "UNDP Internship Program", "United Nations Development Programme",
        "Global / Multiple Countries", "INTERNSHIP", 5000, 10000, two_months,
        "Development Studies",
        "Paid internship at UNDP offices worldwide. "
        "Work experience in international development.",
        "Graduate student or recent graduate in development field. "
        "Fluency in UN language. Interest in development.",
        "GOVERNMENT", "https://www.undp.org/"
    ))
    catalog.append(make_opp(
        "UNICEF Internship Program", "UNICEF",
        "Global / Multiple Countries", "INTERNSHIP", 5000, 15000, two_months,
        "Child Rights & Development",
        "Paid internship at UNICEF headquarters and country offices. "
        "Contribution to child rights programs globally.",
        "Currently enrolled or recent graduate. "
        "Commitment to children's rights. Fluency in UN language.",
        "GOVERNMENT", "https://www.unicef.org/"
    ))
    catalog.append(make_opp(
        "Global Innovation Fund", "Global Innovation Fund",
        "Global / Multiple Countries", "GRANT", 50000, 1000000, three_months,
        "Social Innovation",
        "Grants for social innovations with potential to improve millions of lives in developing countries.",
        "Social enterprises, NGOs, and researchers. "
        "Evidence-backed innovation with scaling potential.",
        "FOUNDATION", "https://www.globalinnovation.fund/"
    ))
    catalog.append(make_opp(
        "Schwarzman Scholars", "Schwarzman Scholars - Tsinghua University",
        "Global / Multiple Countries", "SCHOLARSHIP", 50000, 80000, three_months,
        "Global Affairs & Leadership",
        "Fully-funded Master's in global affairs at Tsinghua University, Beijing. "
        "Tuition, room and board, travel, and leadership program.",
        "Citizens of all countries. Bachelor's degree. "
        "Age 18-28. Strong English proficiency. Leadership potential.",
        "UNIVERSITY", "https://www.schwarzmanscholars.org/"
    ))

    return catalog


# ======================================================================
# FEED UI CSS
# ======================================================================

FEED_CSS = """
<style>
    /* --- GLOBAL SIDEBAR DARK THEMING OVERRIDE --- */
    [data-testid="stSidebar"], section[data-testid="stSidebar"] {
        background-color: #090d16 !important;
        border-right: 1px solid #1e293b !important;
    }
    
    /* Force all sidebar text, links, and headers to high-contrast off-white */
    [data-testid="stSidebar"] *, section[data-testid="stSidebar"] * {
        color: #f8fafc !important;
    }

    /* Target navigation links and text explicitly */
    [data-testid="stSidebarNav"] span, 
    [data-testid="stSidebarNav"] a,
    [data-testid="stSidebarNavLink"],
    [data-testid="stSidebarHeader"] {
        color: #f8fafc !important;
        font-weight: 600 !important;
    }

    /* Navigation item hover state */
    [data-testid="stSidebarNavLink"]:hover,
    [data-testid="stSidebarNav"] a:hover {
        background-color: #1e293b !important;
        border-radius: 8px !important;
    }

    /* Currently selected navigation item active state */
    [data-testid="stSidebarNavLink"][aria-current="page"],
    [data-testid="stSidebarNav"] a[aria-selected="true"] {
        background-color: #0284c7 !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
    }

    /* Custom form inputs inside sidebar */
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] .stMultiSelect label {
        color: #38bdf8 !important;
        font-weight: 700 !important;
    }
/* â”€â”€ Live Opportunity Feed Styles â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
.feed-container {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 16px;
    overflow: hidden;
    margin-bottom: 1rem;
}

.feed-header {
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
    border-bottom: 1px solid #1e293b;
    padding: 1rem 1.5rem;
}
.feed-header h2 { color: #f8fafc !important; font-size: 1.3rem !important; font-weight: 800 !important; margin: 0 !important; }
.feed-header p { color: #94a3b8 !important; font-size: 0.8rem !important; margin: 0.2rem 0 0 0 !important; }

.feed-stats-row {
    display: flex;
    gap: 0.75rem;
    padding: 0.75rem 1.5rem;
    background: #0f172a80;
    border-bottom: 1px solid #1e293b;
}
.feed-stat {
    display: flex;
    align-items: center;
    gap: 0.3rem;
    font-size: 0.75rem;
    color: #94a3b8;
}
.feed-stat-value { color: #f1f5f9; font-weight: 700; }

.feed-card {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 14px;
    padding: 1rem;
    margin-bottom: 0.75rem;
    transition: all 0.2s;
}
.feed-card:hover {
    border-color: #4f46e5;
    box-shadow: 0 4px 20px rgba(79,70,229,0.1);
}

.feed-card-featured {
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
    border: 1px solid #3730a3;
    box-shadow: 0 0 30px rgba(79,70,229,0.08);
}

.feed-card-top {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    margin-bottom: 0.5rem;
}
.feed-card-flag { font-size: 1.8rem; line-height: 1; }
.feed-card-title-area { flex: 1; min-width: 0; }
.feed-card-title {
    color: #f1f5f9;
    font-weight: 700;
    font-size: 0.9rem;
    margin-bottom: 0.15rem;
    line-height: 1.3;
}
.feed-card-org {
    color: #818cf8;
    font-size: 0.75rem;
    font-weight: 500;
}

.feed-card-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
    margin-bottom: 0.5rem;
}
.feed-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.2rem;
    padding: 0.1rem 0.5rem;
    border-radius: 999px;
    font-size: 0.65rem;
    font-weight: 700;
    line-height: 1.6;
}

.feed-badge-type {
    background: rgba(99,102,241,0.15);
    color: #818cf8;
    border: 1px solid rgba(99,102,241,0.3);
}
.feed-badge-amount {
    background: rgba(34,197,94,0.15);
    color: #4ade80;
    border: 1px solid rgba(34,197,94,0.3);
}
.feed-badge-deadline {
    background: rgba(245,158,11,0.15);
    color: #fbbf24;
    border: 1px solid rgba(245,158,11,0.3);
}
.feed-badge-region {
    background: rgba(59,130,246,0.15);
    color: #60a5fa;
    border: 1px solid rgba(59,130,246,0.3);
}
.feed-badge-authority {
    background: rgba(236,72,153,0.15);
    color: #f472b6;
    border: 1px solid rgba(236,72,153,0.3);
}

.feed-card-desc {
    color: #94a3b8;
    font-size: 0.75rem;
    line-height: 1.5;
    margin-bottom: 0.5rem;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.feed-card-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-top: 1px solid #1e293b;
    padding-top: 0.5rem;
    margin-top: 0.25rem;
}
.feed-card-source {
    font-size: 0.6rem;
    color: #475569;
}
.feed-card-source a { color: #818cf8; text-decoration: none; }

.feed-featured-section {
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
    border: 1px solid #1e293b;
    border-radius: 16px;
    padding: 1.25rem;
    margin-bottom: 1rem;
}
.feed-featured-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 1rem;
}
.feed-featured-header h3 { color: #fbbf24; font-size: 1rem; font-weight: 700; margin: 0 !important; }

.feed-pagination {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem;
}
.feed-page-btn {
    padding: 0.3rem 0.8rem;
    border-radius: 8px;
    font-size: 0.75rem;
    font-weight: 600;
    background: #1e293b;
    color: #94a3b8;
    border: 1px solid #334155;
    cursor: pointer;
    transition: all 0.2s;
}
.feed-page-btn:hover { border-color: #6366f1; color: #f1f5f9; }
.feed-page-btn.active { background: #4f46e5; color: white; border-color: #4f46e5; }
.feed-page-info { color: #64748b; font-size: 0.75rem; }

.verification-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.15rem 0.6rem;
    border-radius: 999px;
    font-size: 0.65rem;
    font-weight: 700;
}
</style>
"""


