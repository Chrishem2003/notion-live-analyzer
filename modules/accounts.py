"""User accounts, subscription tiers and entitlement state.

Two backends implement the same :class:`AccountStore` interface:

* :class:`SQLiteAccountStore` — the default. Zero configuration, but hosted
  Streamlit containers have an ephemeral filesystem, so it is only durable for
  self-hosted or single-container deployments.
* :class:`SupabaseAccountStore` — used automatically when ``SUPABASE_URL`` and
  ``SUPABASE_SERVICE_KEY`` are set. Talks to PostgREST over ``requests``; no
  extra dependency.

Passwords are stored as PBKDF2-HMAC-SHA256 with a per-user salt. Nothing here
imports Streamlit so it stays unit-testable and reusable from a webhook handler.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

APP_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = APP_DIR / "accounts.db"

PBKDF2_ROUNDS = 200_000
TRIAL_DAYS = 15
TEMPLATE_TOKEN_TTL_HOURS = 48


class Tier(str, Enum):
    FREE = "free"
    STANDARD = "standard"
    PREMIUM = "premium"

    @classmethod
    def from_string(cls, value: Optional[str]) -> "Tier":
        try:
            return cls(str(value).strip().lower())
        except (ValueError, AttributeError):
            return cls.FREE

    @property
    def rank(self) -> int:
        return {Tier.FREE: 0, Tier.STANDARD: 1, Tier.PREMIUM: 2}[self]

    def covers(self, required: "Tier") -> bool:
        """True when this tier includes everything ``required`` grants."""
        return self.rank >= required.rank


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _format_ts(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


# ═══════════════════════════════════════════════════════════════════════
# Password hashing
# ═══════════════════════════════════════════════════════════════════════
def hash_password(password: str, salt: Optional[str] = None) -> str:
    """Return ``pbkdf2_sha256$rounds$salt$hash``."""
    if not password:
        raise ValueError("Password must not be empty")
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), PBKDF2_ROUNDS
    ).hex()
    return f"pbkdf2_sha256${PBKDF2_ROUNDS}${salt}${digest}"


def verify_password(password: str, encoded: str) -> bool:
    """Constant-time check of a password against a stored hash."""
    try:
        algorithm, rounds, salt, digest = encoded.split("$")
    except (ValueError, AttributeError):
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    candidate = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), int(rounds)
    ).hex()
    return hmac.compare_digest(candidate, digest)


# ═══════════════════════════════════════════════════════════════════════
# Model
# ═══════════════════════════════════════════════════════════════════════
@dataclass
class User:
    id: str
    email: str
    tier: Tier = Tier.FREE
    created_at: datetime = field(default_factory=utcnow)
    trial_ends_at: Optional[datetime] = None
    subscription_ends_at: Optional[datetime] = None
    country: Optional[str] = None
    institution: Optional[str] = None
    student_verified: bool = False
    notion_template_claimed: bool = False
    stripe_customer_id: Optional[str] = None
    is_admin: bool = False
    is_suspended: bool = False
    password_hash: str = ""

    # ─── Derived state ────────────────────────────────────────────
    def trial_active(self, now: Optional[datetime] = None) -> bool:
        now = now or utcnow()
        return bool(self.trial_ends_at and self.trial_ends_at > now)

    def trial_days_left(self, now: Optional[datetime] = None) -> int:
        now = now or utcnow()
        if not self.trial_active(now):
            return 0
        return max(0, (self.trial_ends_at - now).days + 1)

    def subscription_active(self, now: Optional[datetime] = None) -> bool:
        now = now or utcnow()
        return bool(self.subscription_ends_at and self.subscription_ends_at > now)

    def effective_tier(self, now: Optional[datetime] = None) -> Tier:
        """The tier actually in force, accounting for trials and lapses.

        A suspended account has no entitlements. A paid tier that has lapsed
        falls back to free. An active trial upgrades a free account to standard,
        and never downgrades someone who already pays for more.
        """
        now = now or utcnow()
        if self.is_suspended:
            return Tier.FREE

        tier = self.tier
        if tier is not Tier.FREE and self.subscription_ends_at and not self.subscription_active(now):
            tier = Tier.FREE
        if self.trial_active(now) and tier.rank < Tier.STANDARD.rank:
            tier = Tier.STANDARD
        return tier

    def to_row(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "tier": self.tier.value,
            "created_at": _format_ts(self.created_at),
            "trial_ends_at": _format_ts(self.trial_ends_at),
            "subscription_ends_at": _format_ts(self.subscription_ends_at),
            "country": self.country,
            "institution": self.institution,
            "student_verified": int(self.student_verified),
            "notion_template_claimed": int(self.notion_template_claimed),
            "stripe_customer_id": self.stripe_customer_id,
            "is_admin": int(self.is_admin),
            "is_suspended": int(self.is_suspended),
            "password_hash": self.password_hash,
        }

    @classmethod
    def from_row(cls, row: Any) -> "User":
        data = dict(row)
        return cls(
            id=str(data["id"]),
            email=data["email"],
            tier=Tier.from_string(data.get("tier")),
            created_at=_parse_ts(data.get("created_at")) or utcnow(),
            trial_ends_at=_parse_ts(data.get("trial_ends_at")),
            subscription_ends_at=_parse_ts(data.get("subscription_ends_at")),
            country=data.get("country"),
            institution=data.get("institution"),
            student_verified=bool(data.get("student_verified")),
            notion_template_claimed=bool(data.get("notion_template_claimed")),
            stripe_customer_id=data.get("stripe_customer_id"),
            is_admin=bool(data.get("is_admin")),
            is_suspended=bool(data.get("is_suspended")),
            password_hash=data.get("password_hash") or "",
        )


class AccountError(Exception):
    """Raised for expected account failures (duplicate email, bad login...)."""


# ═══════════════════════════════════════════════════════════════════════
# SQLite backend
# ═══════════════════════════════════════════════════════════════════════
class SQLiteAccountStore:
    """File-backed account store. Durable only where the disk is."""

    backend = "sqlite"

    def __init__(self, db_path: Any = None):
        self.db_path = Path(db_path or os.environ.get("ACCOUNTS_DB_PATH") or DEFAULT_DB_PATH)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self):
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS accounts (
                    id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    tier TEXT NOT NULL DEFAULT 'free',
                    created_at TEXT NOT NULL,
                    trial_ends_at TEXT,
                    subscription_ends_at TEXT,
                    country TEXT,
                    institution TEXT,
                    student_verified INTEGER NOT NULL DEFAULT 0,
                    notion_template_claimed INTEGER NOT NULL DEFAULT 0,
                    stripe_customer_id TEXT,
                    is_admin INTEGER NOT NULL DEFAULT 0,
                    is_suspended INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS usage_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    feature TEXT NOT NULL,
                    period TEXT NOT NULL,
                    used_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_usage_user_period
                    ON usage_events(user_id, feature, period);
                CREATE TABLE IF NOT EXISTS template_claims (
                    token TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    issued_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    redeemed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS discount_codes (
                    code TEXT PRIMARY KEY,
                    percent_off INTEGER NOT NULL,
                    grants_tier TEXT,
                    grants_days INTEGER,
                    max_redemptions INTEGER NOT NULL DEFAULT 1,
                    redemptions INTEGER NOT NULL DEFAULT 0,
                    expires_at TEXT,
                    created_at TEXT NOT NULL
                );
                """
            )
            conn.commit()

    # ─── CRUD ─────────────────────────────────────────────────────
    def create_user(self, email: str, password: str, **kwargs) -> User:
        email = normalize_email(email)
        if self.get_user_by_email(email):
            raise AccountError(f"An account already exists for {email}.")
        user = User(
            id=secrets.token_hex(16),
            email=email,
            password_hash=hash_password(password),
            **kwargs,
        )
        row = user.to_row()
        with self._connect() as conn:
            conn.execute(
                f"INSERT INTO accounts ({','.join(row)}) VALUES ({','.join('?' * len(row))})",
                tuple(row.values()),
            )
            conn.commit()
        return user

    def get_user(self, user_id: str) -> Optional[User]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM accounts WHERE id = ?", (user_id,)).fetchone()
        return User.from_row(row) if row else None

    def get_user_by_email(self, email: str) -> Optional[User]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM accounts WHERE email = ?", (normalize_email(email),)
            ).fetchone()
        return User.from_row(row) if row else None

    def save_user(self, user: User) -> User:
        row = user.to_row()
        assignments = ",".join(f"{key} = ?" for key in row if key != "id")
        values = [value for key, value in row.items() if key != "id"]
        with self._connect() as conn:
            conn.execute(f"UPDATE accounts SET {assignments} WHERE id = ?", (*values, user.id))
            conn.commit()
        return user

    def list_users(self, limit: int = 500) -> List[User]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM accounts ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [User.from_row(row) for row in rows]

    def delete_user(self, user_id: str) -> bool:
        with self._connect() as conn:
            deleted = conn.execute("DELETE FROM accounts WHERE id = ?", (user_id,)).rowcount
            conn.execute("DELETE FROM usage_events WHERE user_id = ?", (user_id,))
            conn.commit()
        return bool(deleted)

    # ─── Usage metering ───────────────────────────────────────────
    def record_usage(self, user_id: str, feature: str, when: Optional[datetime] = None) -> int:
        when = when or utcnow()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO usage_events (user_id, feature, period, used_at) VALUES (?,?,?,?)",
                (user_id, feature, billing_period(when), when.isoformat()),
            )
            conn.commit()
        return self.usage_count(user_id, feature, when)

    def usage_count(self, user_id: str, feature: str, when: Optional[datetime] = None) -> int:
        when = when or utcnow()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM usage_events WHERE user_id=? AND feature=? AND period=?",
                (user_id, feature, billing_period(when)),
            ).fetchone()
        return int(row["c"])

    # ─── Notion template claim ────────────────────────────────────
    def issue_template_token(self, user_id: str, ttl_hours: int = TEMPLATE_TOKEN_TTL_HOURS) -> str:
        now = utcnow()
        token = secrets.token_urlsafe(32)
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO template_claims (token, user_id, issued_at, expires_at) VALUES (?,?,?,?)",
                (token, user_id, now.isoformat(), (now + timedelta(hours=ttl_hours)).isoformat()),
            )
            conn.commit()
        return token

    def redeem_template_token(self, token: str, now: Optional[datetime] = None) -> Optional[str]:
        """Consume a claim token, returning its user id, or None if unusable."""
        now = now or utcnow()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM template_claims WHERE token = ?", (token,)
            ).fetchone()
            if row is None or row["redeemed_at"]:
                return None
            if (_parse_ts(row["expires_at"]) or now) <= now:
                return None
            conn.execute(
                "UPDATE template_claims SET redeemed_at = ? WHERE token = ?",
                (now.isoformat(), token),
            )
            conn.commit()
        return row["user_id"]

    # ─── Discount codes ───────────────────────────────────────────
    def create_discount_code(self, code: Dict[str, Any]) -> Dict[str, Any]:
        with self._connect() as conn:
            conn.execute(
                f"INSERT INTO discount_codes ({','.join(code)}) "
                f"VALUES ({','.join('?' * len(code))})",
                tuple(code.values()),
            )
            conn.commit()
        return code

    def get_discount_code(self, code: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM discount_codes WHERE code = ?", (code.strip().upper(),)
            ).fetchone()
        return dict(row) if row else None

    def list_discount_codes(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM discount_codes ORDER BY created_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def increment_discount_redemptions(self, code: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE discount_codes SET redemptions = redemptions + 1 WHERE code = ?",
                (code.strip().upper(),),
            )
            conn.commit()

    def delete_discount_code(self, code: str) -> bool:
        with self._connect() as conn:
            deleted = conn.execute(
                "DELETE FROM discount_codes WHERE code = ?", (code.strip().upper(),)
            ).rowcount
            conn.commit()
        return bool(deleted)


# ═══════════════════════════════════════════════════════════════════════
# Supabase backend
# ═══════════════════════════════════════════════════════════════════════
class SupabaseAccountStore(SQLiteAccountStore):
    """PostgREST-backed store with the same interface.

    Subclasses the SQLite store only to inherit the metering/claim helpers'
    signatures; every method that touches state is overridden below.
    """

    backend = "supabase"

    def __init__(self, url: str, service_key: str, session=None):
        import requests  # local import keeps the module importable offline

        self.url = url.rstrip("/")
        self.service_key = service_key
        self._session = session or requests.Session()
        self._headers = {
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    # ─── REST plumbing ────────────────────────────────────────────
    def _request(self, method: str, table: str, **kwargs) -> Any:
        response = self._session.request(
            method,
            f"{self.url}/rest/v1/{table}",
            headers=self._headers,
            timeout=15,
            **kwargs,
        )
        if response.status_code >= 400:
            raise AccountError(f"Supabase {method} {table} failed: {response.text[:200]}")
        if not response.content:
            return []
        return response.json()

    def _select_one(self, table: str, **filters) -> Optional[Dict[str, Any]]:
        params = {key: f"eq.{value}" for key, value in filters.items()}
        params["limit"] = 1
        rows = self._request("GET", table, params=params)
        return rows[0] if rows else None

    # ─── CRUD ─────────────────────────────────────────────────────
    def create_user(self, email: str, password: str, **kwargs) -> User:
        email = normalize_email(email)
        if self.get_user_by_email(email):
            raise AccountError(f"An account already exists for {email}.")
        user = User(
            id=secrets.token_hex(16),
            email=email,
            password_hash=hash_password(password),
            **kwargs,
        )
        self._request("POST", "accounts", json=user.to_row())
        return user

    def get_user(self, user_id: str) -> Optional[User]:
        row = self._select_one("accounts", id=user_id)
        return User.from_row(row) if row else None

    def get_user_by_email(self, email: str) -> Optional[User]:
        row = self._select_one("accounts", email=normalize_email(email))
        return User.from_row(row) if row else None

    def save_user(self, user: User) -> User:
        self._request(
            "PATCH", "accounts", params={"id": f"eq.{user.id}"}, json=user.to_row()
        )
        return user

    def list_users(self, limit: int = 500) -> List[User]:
        rows = self._request(
            "GET", "accounts", params={"order": "created_at.desc", "limit": limit}
        )
        return [User.from_row(row) for row in rows]

    def delete_user(self, user_id: str) -> bool:
        rows = self._request("DELETE", "accounts", params={"id": f"eq.{user_id}"})
        return bool(rows)

    # ─── Usage metering ───────────────────────────────────────────
    def record_usage(self, user_id: str, feature: str, when: Optional[datetime] = None) -> int:
        when = when or utcnow()
        self._request(
            "POST",
            "usage_events",
            json={
                "user_id": user_id,
                "feature": feature,
                "period": billing_period(when),
                "used_at": when.isoformat(),
            },
        )
        return self.usage_count(user_id, feature, when)

    def usage_count(self, user_id: str, feature: str, when: Optional[datetime] = None) -> int:
        when = when or utcnow()
        rows = self._request(
            "GET",
            "usage_events",
            params={
                "user_id": f"eq.{user_id}",
                "feature": f"eq.{feature}",
                "period": f"eq.{billing_period(when)}",
                "select": "id",
            },
        )
        return len(rows)

    # ─── Notion template claim ────────────────────────────────────
    def issue_template_token(self, user_id: str, ttl_hours: int = TEMPLATE_TOKEN_TTL_HOURS) -> str:
        now = utcnow()
        token = secrets.token_urlsafe(32)
        self._request(
            "POST",
            "template_claims",
            json={
                "token": token,
                "user_id": user_id,
                "issued_at": now.isoformat(),
                "expires_at": (now + timedelta(hours=ttl_hours)).isoformat(),
                "redeemed_at": None,
            },
        )
        return token

    def redeem_template_token(self, token: str, now: Optional[datetime] = None) -> Optional[str]:
        now = now or utcnow()
        row = self._select_one("template_claims", token=token)
        if row is None or row.get("redeemed_at"):
            return None
        if (_parse_ts(row.get("expires_at")) or now) <= now:
            return None
        self._request(
            "PATCH",
            "template_claims",
            params={"token": f"eq.{token}"},
            json={"redeemed_at": now.isoformat()},
        )
        return row["user_id"]

    # ─── Discount codes ───────────────────────────────────────────
    def create_discount_code(self, code: Dict[str, Any]) -> Dict[str, Any]:
        self._request("POST", "discount_codes", json=code)
        return code

    def get_discount_code(self, code: str) -> Optional[Dict[str, Any]]:
        return self._select_one("discount_codes", code=code.strip().upper())

    def list_discount_codes(self) -> List[Dict[str, Any]]:
        return self._request("GET", "discount_codes", params={"order": "created_at.desc"})

    def increment_discount_redemptions(self, code: str) -> None:
        existing = self.get_discount_code(code)
        if existing is None:
            return
        self._request(
            "PATCH",
            "discount_codes",
            params={"code": f"eq.{code.strip().upper()}"},
            json={"redemptions": int(existing.get("redemptions", 0)) + 1},
        )

    def delete_discount_code(self, code: str) -> bool:
        rows = self._request(
            "DELETE", "discount_codes", params={"code": f"eq.{code.strip().upper()}"}
        )
        return bool(rows)


# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════
def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def billing_period(when: Optional[datetime] = None) -> str:
    """Quota bucket key — quotas in the pricing table are per calendar month."""
    when = when or utcnow()
    return when.strftime("%Y-%m")


def get_store(force_sqlite: bool = False) -> SQLiteAccountStore:
    """Supabase when configured, SQLite otherwise."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if url and key and not force_sqlite:
        return SupabaseAccountStore(url, key)
    return SQLiteAccountStore()


def storage_is_durable() -> bool:
    """False when accounts live on a container filesystem that resets."""
    return bool(os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_KEY"))


# ═══════════════════════════════════════════════════════════════════════
# Account operations
# ═══════════════════════════════════════════════════════════════════════
def register(
    store: SQLiteAccountStore,
    email: str,
    password: str,
    country: Optional[str] = None,
    with_trial: bool = True,
    now: Optional[datetime] = None,
) -> User:
    """Create an account, starting the standard trial by default."""
    now = now or utcnow()
    if len(password or "") < 8:
        raise AccountError("Password must be at least 8 characters.")
    if "@" not in normalize_email(email):
        raise AccountError("Enter a valid email address.")

    admin_emails = {
        normalize_email(value)
        for value in (os.environ.get("ADMIN_EMAILS") or "").split(",")
        if value.strip()
    }
    user = store.create_user(
        email,
        password,
        country=country,
        created_at=now,
        trial_ends_at=now + timedelta(days=TRIAL_DAYS) if with_trial else None,
        is_admin=normalize_email(email) in admin_emails,
    )
    return user


def authenticate(store: SQLiteAccountStore, email: str, password: str) -> User:
    """Return the user for valid credentials, else raise :class:`AccountError`."""
    user = store.get_user_by_email(email)
    # Hash regardless of whether the account exists so timing does not leak it.
    reference = user.password_hash if user else hash_password("placeholder-comparison")
    if not verify_password(password, reference) or user is None:
        raise AccountError("Incorrect email or password.")
    if user.is_suspended:
        raise AccountError("This account is suspended. Contact support.")
    return user


def set_tier(
    store: SQLiteAccountStore,
    user: User,
    tier: Tier,
    days: Optional[int] = None,
    now: Optional[datetime] = None,
) -> User:
    """Grant a tier, optionally for a fixed number of days."""
    now = now or utcnow()
    updated = replace(
        user,
        tier=tier,
        subscription_ends_at=(now + timedelta(days=days)) if days else None,
    )
    return store.save_user(updated)


def extend_trial(
    store: SQLiteAccountStore, user: User, days: int, now: Optional[datetime] = None
) -> User:
    """Add trial days, from today when the previous trial has already lapsed."""
    now = now or utcnow()
    base = user.trial_ends_at if user.trial_active(now) else now
    return store.save_user(replace(user, trial_ends_at=base + timedelta(days=days)))


def suspend(store: SQLiteAccountStore, user: User, suspended: bool = True) -> User:
    return store.save_user(replace(user, is_suspended=suspended))
