"""
Session security — proxy signals, geo plausibility and a review log
===================================================================
Streamlit sits behind a proxy, so the only evidence available about a caller
is the forwarded header set. This module reads it, scores it, and records the
outcome for the admin console.

Deliberately conservative: header inspection cannot prove a VPN, and a
commercial IP-reputation feed is a paid dependency this deployment does not
have. So a suspicious session is *flagged for review*, never silently banned —
a false positive here locks a student out of their own submission. Only the
strongest signal (an impossible travel speed between two sightings of the same
account) reaches :data:`RiskLevel.BLOCK`, and even that is advisory to callers.
"""
from __future__ import annotations

import ipaddress
import math
import os
import sqlite3
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

APP_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = APP_DIR / "accounts.db"

# Headers a proxy/anonymiser typically adds on top of the standard forwarding set.
PROXY_HEADERS = (
    "via",
    "forwarded",
    "x-proxy-id",
    "proxy-connection",
    "x-anonymous",
    "x-vpn",
)
STANDARD_FORWARD_HEADERS = ("x-forwarded-for", "x-real-ip", "cf-connecting-ip")

# Fastest sensible commercial travel, plus slack for imprecise city centroids.
MAX_TRAVEL_KMH = 1000.0
GRACE_KM = 100.0
EARTH_RADIUS_KM = 6371.0


class RiskLevel(str, Enum):
    OK = "ok"
    REVIEW = "review"
    BLOCK = "block"


@dataclass(frozen=True)
class ClientSignals:
    ip: Optional[str] = None
    forwarded_chain: Tuple[str, ...] = ()
    country: Optional[str] = None
    proxy_headers: Tuple[str, ...] = ()
    user_agent: str = ""


@dataclass
class RiskAssessment:
    level: RiskLevel
    score: int
    reasons: List[str] = field(default_factory=list)
    signals: ClientSignals = field(default_factory=ClientSignals)

    @property
    def allowed(self) -> bool:
        return self.level is not RiskLevel.BLOCK

    @property
    def summary(self) -> str:
        if not self.reasons:
            return "No anomalies in the forwarded headers."
        return "; ".join(self.reasons)


def normalise_headers(headers: Optional[Dict[str, str]]) -> Dict[str, str]:
    return {str(k).lower(): str(v) for k, v in (headers or {}).items()}


def _is_public(candidate: str) -> bool:
    try:
        address = ipaddress.ip_address(candidate)
    except ValueError:
        return False
    return address.is_global and not address.is_private


def client_ip(headers: Optional[Dict[str, str]]) -> Optional[str]:
    """First public address in the forwarding chain.

    ``X-Forwarded-For`` is client-controlled: anyone can prepend a fake hop.
    Taking the first *public* entry matches what the platform proxies append
    and ignores obviously spoofed private addresses.
    """
    lowered = normalise_headers(headers)
    for header in STANDARD_FORWARD_HEADERS:
        raw = lowered.get(header, "")
        for part in raw.split(","):
            candidate = part.strip()
            if candidate and _is_public(candidate):
                return candidate
    return None


def forwarded_chain(headers: Optional[Dict[str, str]]) -> Tuple[str, ...]:
    lowered = normalise_headers(headers)
    chain = lowered.get("x-forwarded-for", "")
    return tuple(part.strip() for part in chain.split(",") if part.strip())


def declared_country(headers: Optional[Dict[str, str]]) -> Optional[str]:
    """Country from a CDN header, upper-cased, or ``None``."""
    lowered = normalise_headers(headers)
    for header in ("cf-ipcountry", "x-vercel-ip-country", "x-appengine-country"):
        value = lowered.get(header, "").strip().upper()
        if value and value not in ("XX", "T1", "ZZ"):
            return value
    return None


def read_signals(headers: Optional[Dict[str, str]]) -> ClientSignals:
    lowered = normalise_headers(headers)
    return ClientSignals(
        ip=client_ip(headers),
        forwarded_chain=forwarded_chain(headers),
        country=declared_country(headers),
        proxy_headers=tuple(h for h in PROXY_HEADERS if lowered.get(h)),
        user_agent=lowered.get("user-agent", ""),
    )


def haversine_km(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    """Great-circle distance between two ``(lat, lon)`` pairs."""
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(h))


def travel_is_impossible(
    previous: Tuple[float, float],
    current: Tuple[float, float],
    seconds: float,
    max_kmh: float = MAX_TRAVEL_KMH,
) -> Tuple[bool, float]:
    """``(impossible, implied km/h)`` between two sightings."""
    distance = haversine_km(previous, current)
    if distance <= GRACE_KM or seconds <= 0:
        return False, 0.0
    speed = distance / (seconds / 3600.0)
    return speed > max_kmh, round(speed, 1)


def assess(
    headers: Optional[Dict[str, str]] = None,
    *,
    declared: Optional[str] = None,
    history: Sequence["SessionSighting"] = (),
    now: Optional[float] = None,
) -> RiskAssessment:
    """Score a session from its headers and this account's recent sightings."""
    signals = read_signals(headers)
    now = now if now is not None else time.time()
    reasons: List[str] = []
    score = 0

    if signals.proxy_headers:
        score += 25
        reasons.append(
            "Proxy headers present: " + ", ".join(signals.proxy_headers)
        )
    if len(signals.forwarded_chain) > 3:
        score += 15
        reasons.append(f"Unusually long forwarding chain ({len(signals.forwarded_chain)} hops)")
    if not signals.ip:
        score += 10
        reasons.append("No public client address in the forwarded headers")
    if declared and signals.country and declared.upper() != signals.country:
        score += 30
        reasons.append(
            f"Declared country {declared.upper()} does not match network country {signals.country}"
        )
    if not signals.user_agent:
        score += 10
        reasons.append("No user agent")

    level = RiskLevel.OK
    for sighting in history:
        if sighting.coordinates is None or not signals.country:
            continue
        current = COUNTRY_CENTROIDS.get(signals.country)
        if current is None:
            continue
        impossible, speed = travel_is_impossible(
            sighting.coordinates, current, max(0.0, now - sighting.at)
        )
        if impossible:
            score += 60
            level = RiskLevel.BLOCK
            reasons.append(
                f"Impossible travel: {speed:.0f} km/h since the last sign-in from "
                f"{sighting.country}"
            )
            break

    if level is not RiskLevel.BLOCK and score >= 40:
        level = RiskLevel.REVIEW
    return RiskAssessment(level=level, score=score, reasons=reasons, signals=signals)


# Country centroids used for the travel check. Coarse on purpose: the check
# only has to separate "same region" from "other side of the planet".
COUNTRY_CENTROIDS: Dict[str, Tuple[float, float]] = {
    "UG": (1.37, 32.29), "KE": (-0.02, 37.91), "TZ": (-6.37, 34.89),
    "RW": (-1.94, 29.87), "NG": (9.08, 8.68), "GH": (7.95, -1.02),
    "ZA": (-30.56, 22.94), "EG": (26.82, 30.80), "ET": (9.15, 40.49),
    "US": (37.09, -95.71), "GB": (55.38, -3.44), "CA": (56.13, -106.35),
    "IN": (20.59, 78.96), "CN": (35.86, 104.20), "DE": (51.17, 10.45),
    "FR": (46.23, 2.21), "BR": (-14.24, -51.93), "AU": (-25.27, 133.78),
    "JP": (36.20, 138.25), "AE": (23.42, 53.85),
}


@dataclass(frozen=True)
class SessionSighting:
    account: str
    country: Optional[str]
    ip: Optional[str]
    at: float

    @property
    def coordinates(self) -> Optional[Tuple[float, float]]:
        return COUNTRY_CENTROIDS.get((self.country or "").upper())


# ═══════════════════════════════════════════════════════════════════════
# Persistence — shared with the accounts database
# ═══════════════════════════════════════════════════════════════════════
def db_path() -> Path:
    return Path(os.environ.get("ACCOUNTS_DB_PATH") or DEFAULT_DB_PATH)


class SecurityLog:
    """Append-only record of assessments, read by the admin console."""

    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path else db_path()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS security_events (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       account TEXT NOT NULL DEFAULT '',
                       level TEXT NOT NULL,
                       score INTEGER NOT NULL,
                       country TEXT,
                       ip TEXT,
                       reasons TEXT,
                       at REAL NOT NULL
                   )"""
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_security_events_at ON security_events(at)"
            )
            conn.commit()

    def record(
        self,
        assessment: RiskAssessment,
        account: str = "",
        now: Optional[float] = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO security_events (account, level, score, country, ip, reasons, at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    account,
                    assessment.level.value,
                    assessment.score,
                    assessment.signals.country,
                    assessment.signals.ip,
                    " | ".join(assessment.reasons),
                    now if now is not None else time.time(),
                ),
            )
            conn.commit()

    def recent(self, limit: int = 50, level: Optional[RiskLevel] = None) -> List[Dict]:
        query = "SELECT * FROM security_events"
        params: List[object] = []
        if level is not None:
            query += " WHERE level = ?"
            params.append(level.value)
        query += " ORDER BY at DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            return [dict(row) for row in conn.execute(query, params).fetchall()]

    def sightings(self, account: str, limit: int = 5) -> List[SessionSighting]:
        """Most recent sightings of an account, newest first."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT account, country, ip, at FROM security_events"
                " WHERE account = ? AND country IS NOT NULL ORDER BY at DESC LIMIT ?",
                (account, limit),
            ).fetchall()
        return [
            SessionSighting(r["account"], r["country"], r["ip"], r["at"]) for r in rows
        ]

    def counts(self) -> Dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT level, COUNT(*) AS n FROM security_events GROUP BY level"
            ).fetchall()
        return {row["level"]: row["n"] for row in rows}
