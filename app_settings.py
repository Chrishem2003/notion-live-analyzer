"""
App Settings — persistent key-value store (replaces hardcoded file paths)
=============================================================================
The old code pointed the creator photo at a hardcoded Windows path
(C:\\Users\\Admin\\Pictures\\background.jpg) — guaranteed to not exist on a
deployed Linux server. Real fix: upload once through the UI, store as a
base64 blob in the shared database, same pattern as every other real
dataset in this app.

Honest caveat: this database file (sovereign_apex_engine.db) lives on
local disk. Most managed hosts, including Streamlit Community Cloud,
don't guarantee that local disk survives an app restart/redeploy/sleep
cycle — so this is real persistence *within a running deployment*, not
guaranteed permanent storage. If the photo (or other data in this DB)
disappears after a redeploy, that's the actual cause, and the real fix
is external persistent storage (a hosted Postgres/Supabase, S3-compatible
object storage, etc.) rather than anything fixable from application code
alone. Flagging this plainly rather than implying local SQLite is
bulletproof.
"""

import sqlite3

DB_FILE = "sovereign_apex_engine.db"


def _get_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    return conn


def ensure_settings_table():
    conn = _get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT
        )
    """)
    conn.commit()
    conn.close()


def get_setting(key: str, default=None):
    ensure_settings_table()
    conn = _get_db()
    row = conn.execute("SELECT setting_value FROM app_settings WHERE setting_key = ?", (key,)).fetchone()
    conn.close()
    return row[0] if row else default


def set_setting(key: str, value: str):
    ensure_settings_table()
    conn = _get_db()
    conn.execute(
        "INSERT OR REPLACE INTO app_settings (setting_key, setting_value) VALUES (?, ?)", (key, value)
    )
    conn.commit()
    conn.close()


def get_creator_photo_b64():
    return get_setting("creator_photo_b64", default=None)


def set_creator_photo_b64(data_uri: str):
    set_setting("creator_photo_b64", data_uri)