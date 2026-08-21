import sqlite3
import datetime
import streamlit as st
from modules.paywall import enforce_paywall

NOTION_TEMPLATE_URL = "https://sleet-spectacles-fd3.notion.site/Bio-Research-Enterprise-Research-Planner-35f9142806c6805286a5c6767a7c9cfd?source=copy_link"
NOTION_EMBED_URL = "https://sleet-spectacles-fd3.notion.site/ebd//35f9142806c6805286a5c6767a7c9cfd"

def init_template_db():
    conn = sqlite3.connect("sovereign_apex_engine.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS template_claims (
            email TEXT PRIMARY KEY,
            claimed_at TEXT,
            duplication_count INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def render_notion_template_vault():
    init_template_db()
    
    # Strict Gate: Paid accounts only (Trial accounts strictly blocked)
    enforce_paywall(allowed_plans=["pro", "business", "premium"], feature_name="Bio-Research Notion Enterprise Planner", allow_trial=False)

    user_email = st.session_state.get("user_identity", {}).get("email", "")

    st.title("ðŸ—„ï¸ Bio-Research Enterprise Planner - Notion Vault")
    st.info("ðŸ”’ **Single-Duplication License:** This template is protected. Duplication link is restricted exclusively to active paid subscribers.")

    conn = sqlite3.connect("sovereign_apex_engine.db")
    cursor = conn.cursor()
    cursor.execute("SELECT duplication_count FROM template_claims WHERE email = ?", (user_email,))
    row = cursor.fetchone()

    claim_count = row[0] if row else 0

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### Interactive Workspace Preview")
        st.components.v1.iframe(NOTION_EMBED_URL, height=500, scrolling=True)

    with col2:
        st.markdown("### Template Duplication Access")
        st.write(f"**License Status:** Active Paid License (`{user_email}`)")
        st.write(f"**Duplications Used:** `{claim_count} / 1`")

        if claim_count >= 1:
            st.warning("âš ï¸ You have already claimed your 1-time Notion duplication access.")
            if st.button("ðŸ”— Re-open Licensed Duplicate Link"):
                st.markdown(f"ðŸ‘‰ [Click to open Notion Workspace]({NOTION_TEMPLATE_URL})")
        else:
            if st.button("âš¡ Claim & Duplicate to Notion Space", type="primary"):
                now_str = datetime.datetime.now().isoformat()
                cursor.execute(
                    "INSERT INTO template_claims (email, claimed_at, duplication_count) VALUES (?, ?, 1) "
                    "ON CONFLICT(email) DO UPDATE SET duplication_count = duplication_count + 1",
                    (user_email, now_str)
                )
                conn.commit()
                st.success("âœ… Duplication clearance granted!")
                st.markdown(f"ðŸ‘‰ **[Click here to duplicate into your Notion Workspace]({NOTION_TEMPLATE_URL})**")
                st.rerun()

    conn.close()
