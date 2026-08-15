"""
modules/hub_visibility.py

I don't have modules/navigation.py or modules/page_bootstrap.py (never
uploaded), so I can't safely edit whatever function currently builds your
sidebar/hub cards without risking breaking it blind. This module is the
part of "hide admin from non-admins" that DOESN'T depend on those files —
drop it in and it works immediately. The cosmetic nav-hiding on top of it
is a 2-line addition once you send me navigation.py.

WHAT THIS ALREADY GUARANTEES, with zero edits to navigation.py:
  - 10_Admin_Security_Center.py calls require_admin() at the very top of
    main() (already wired in this drop). Even if the Admin hub link is
    still VISIBLE in the sidebar for a non-admin (cosmetic leak only),
    clicking it or hitting its URL directly hits a hard stop, not the
    admin panel. That's the actual security boundary.

WHAT'S STILL COSMETIC UNTIL YOU SHARE navigation.py:
  - Non-admins will still SEE the "Admin & Security Center" entry in the
    sidebar list (they just can't get past it). If you want it invisible
    too, send me modules/navigation.py and I'll wire this function in
    directly instead of guessing at its internals.
"""

import streamlit as st
from __init__ import CONSOLIDATED_HUBS


def is_admin() -> bool:
    return st.session_state.get("user_identity", {}).get("role") == "admin"


def visible_hubs_for_current_user():
    """Use this anywhere your app currently iterates CONSOLIDATED_HUBS to
    render the sidebar/quick-access cards."""
    if is_admin():
        return CONSOLIDATED_HUBS
    return [h for h in CONSOLIDATED_HUBS if h["id"] != "admin"]
