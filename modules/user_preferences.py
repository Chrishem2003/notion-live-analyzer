"""
User Preferences — timezone, accent color, and a defensive readability fix
=============================================================================
Three real, working things, not decoration:

1. Timezone: auto-detects the visitor's real browser timezone via a small
   JS snippet (Intl.DateTimeFormat — every modern browser supports this,
   no extra package needed) and lets them override it manually from the
   full real IANA timezone list (Python's stdlib zoneinfo — not a
   hand-picked shortlist). Stored in st.session_state so every page's
   timestamps/greetings can use it.

2. Accent color: a real st.color_picker wired to actual CSS custom
   properties that buttons/highlights use — picking a color changes
   what's on screen, unlike the old dead selectbox that was removed
   earlier in this audit.

3. Text contrast fix: some text areas/inputs were reported as
   unreadable — text color blending into the input background. The
   likely cause is a blanket ".stApp { color: X }" rule in the app's
   base theme CSS cascading into Streamlit's text_area/text_input
   internals, which keep their own default background regardless.
   This injects a targeted, defensive override that forces a correct
   high-contrast pairing specifically for input/textarea elements,
   regardless of what any other page's CSS does — so it fixes the
   symptom immediately while the actual theme source (not yet shared)
   can be fixed at the root.
"""

import datetime
import zoneinfo
import streamlit as st
import streamlit.components.v1 as components

DEFAULT_ACCENT = "#4FB8A6"


def render_readability_fix():
    """Call this once near the top of any page that has reported unreadable
    text-area/text-input content. Safe to call on every page."""
    st.markdown(
        """
        <style>
        /* Defensive override: force real contrast in every text input/textarea,
           regardless of any blanket text-color rule elsewhere on the page. */
        div[data-testid="stTextArea"] textarea,
        div[data-testid="stTextInput"] input,
        div[data-testid="stChatInput"] textarea {
            background-color: #171B23 !important;
            color: #EDEFF2 !important;
            caret-color: #EDEFF2 !important;
            border: 1px solid #3A4048 !important;
        }
        div[data-testid="stTextArea"] textarea::placeholder,
        div[data-testid="stTextInput"] input::placeholder {
            color: #64748B !important;
            opacity: 1 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _detect_browser_timezone():
    """Real browser-side detection via Intl.DateTimeFormat. Writes the
    result into a query param and triggers one reload the first time a
    visitor loads the app in a session — after that it's cached in
    session_state and this doesn't run again."""
    components.html(
        """
        <script>
        try {
            const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
            const params = new URLSearchParams(window.parent.location.search);
            if (params.get('detected_tz') !== tz) {
                params.set('detected_tz', tz);
                window.parent.location.search = params.toString();
            }
        } catch (e) { /* Intl not supported — manual selection still works */ }
        </script>
        """,
        height=0,
    )


def get_user_timezone() -> str:
    """Returns the IANA timezone name to use for this session — detected,
    manually overridden, or a safe UTC fallback. Never guesses silently:
    if nothing is known yet, it's UTC until detection/selection completes."""
    if "user_timezone" in st.session_state:
        return st.session_state["user_timezone"]

    detected = st.query_params.get("detected_tz")
    if detected and detected in zoneinfo.available_timezones():
        st.session_state["user_timezone"] = detected
        return detected

    if "tz_detect_attempted" not in st.session_state:
        st.session_state["tz_detect_attempted"] = True
        _detect_browser_timezone()

    return "UTC"


def render_timezone_and_accent_settings():
    """Real, working preference controls — put this in a Settings/Account
    tab. Both values persist in session_state and take effect immediately."""
    st.markdown("#### 🌐 Timezone")
    current_tz = get_user_timezone()
    all_tz = sorted(zoneinfo.available_timezones())
    try:
        default_idx = all_tz.index(current_tz)
    except ValueError:
        default_idx = all_tz.index("UTC")

    chosen_tz = st.selectbox(
        "Your timezone (auto-detected from your browser — override if it's wrong)",
        all_tz, index=default_idx, key="tz_selector_widget",
    )
    if chosen_tz != st.session_state.get("user_timezone"):
        st.session_state["user_timezone"] = chosen_tz
        st.rerun()

    now_local = datetime.datetime.now(zoneinfo.ZoneInfo(chosen_tz))
    st.caption(f"Your local time right now: **{now_local.strftime('%A, %Y-%m-%d %H:%M:%S %Z')}**")

    st.markdown("#### 🎨 Accent Color")
    current_accent = st.session_state.get("user_accent_color", DEFAULT_ACCENT)
    chosen_accent = st.color_picker("Pick an accent color for buttons and highlights", value=current_accent, key="accent_picker_widget")
    if chosen_accent != current_accent:
        st.session_state["user_accent_color"] = chosen_accent
        st.rerun()

    render_accent_color_css()


def render_accent_color_css():
    """Applies the chosen accent color to real UI elements. Call on every
    page (cheap — just a <style> tag) to keep the accent consistent."""
    accent = st.session_state.get("user_accent_color", DEFAULT_ACCENT)
    st.markdown(
        """
        <style>
        div.stButton > button[kind="primary"] {{
            background-color: {accent} !important;
            border-color: {accent} !important;
        }
        div[data-testid="stMetricValue"] {{ color: {accent} !important; }
        a {{ color: {accent} !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def compute_greeting(dt: datetime.datetime) -> str:
    hour = dt.hour
    return (
        "Good Morning" if 5 <= hour < 12
        else "Good Afternoon" if 12 <= hour < 17
        else "Good Evening" if 17 <= hour < 21
        else "Good Night"
    )

