"""Single-use duplication of the premium Notion workspace template.

The template URL is a secret: anyone holding it can duplicate the workspace
forever. So the app never renders it directly. A Premium user exchanges their
entitlement for a short-lived, single-use token bound to their account, and the
account is flagged as claimed the moment the token is issued — a second click
cannot mint a second token even if the first is never opened.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Optional

from modules.accounts import AccountError, SQLiteAccountStore, User, utcnow
from modules.billing import NOTION_TEMPLATE, check_access


@dataclass(frozen=True)
class TemplateClaim:
    token: str
    url: str
    expires_hours: int


def template_url() -> Optional[str]:
    """The configured Notion duplication URL, if any."""
    return os.environ.get("NOTION_TEMPLATE_URL") or None


def template_configured() -> bool:
    return bool(template_url())


def claim(
    store: SQLiteAccountStore,
    user: User,
    now: Optional[datetime] = None,
    ttl_hours: int = 48,
) -> TemplateClaim:
    """Issue the one duplication link this account is entitled to."""
    now = now or utcnow()

    entitlement = check_access(user, NOTION_TEMPLATE, store, now)
    if not entitlement.allowed:
        raise AccountError(entitlement.reason)
    if user.notion_template_claimed:
        raise AccountError(
            "This account has already claimed its Notion template. "
            "Contact support if you lost the workspace."
        )
    url = template_url()
    if not url:
        raise AccountError(
            "The Notion template isn't configured yet. Set NOTION_TEMPLATE_URL."
        )

    token = store.issue_template_token(user.id, ttl_hours=ttl_hours)
    store.save_user(replace(user, notion_template_claimed=True))
    separator = "&" if "?" in url else "?"
    return TemplateClaim(
        token=token,
        url=f"{url}{separator}claim={token}",
        expires_hours=ttl_hours,
    )


def redeem(store: SQLiteAccountStore, token: str, now: Optional[datetime] = None) -> Optional[User]:
    """Consume a claim token (called when the user opens the link)."""
    user_id = store.redeem_template_token(token, now)
    return store.get_user(user_id) if user_id else None


def reset_claim(store: SQLiteAccountStore, user: User) -> User:
    """Admin escape hatch: let a user claim the template again."""
    return store.save_user(replace(user, notion_template_claimed=False))
