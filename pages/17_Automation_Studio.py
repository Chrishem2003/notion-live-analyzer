"""
Automation Studio
------------------
Embeds the Lovable-built Automation Studio app and layers on a few
hub-native features: a live health check, saved notes/bookmarks,
quick-launch templates, and theme-aware sizing.
"""

import json
import time
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests
import streamlit as st
import streamlit.components.v1 as components

EMBED_URL = "https://chrishem-autostudio.lovable.app/embed"
NOTES_FILE = Path(__file__).resolve().parent.parent / "data" / "automation_notes.json"

st.set_page_config(page_title="Automation Studio", page_icon="⚙️", layout="wide")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_notes() -> list[dict]:
    if NOTES_FILE.exists():
        try:
            return json.loads(NOTES_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def save_notes(notes: list[dict]) -> None:
    NOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
    NOTES_FILE.write_text(json.dumps(notes, indent=2), encoding="utf-8")


def with_params(url: str, extra: dict) -> str:
    """Return url with extra query params merged in (keeps existing ones)."""
    parts = urlparse(url)
    query = dict(parse_qsl(parts.query))
    query.update({k: str(v) for k, v in extra.items()})
    return urlunparse(parts._replace(query=urlencode(query)))


# A fresh nonce on every reload forces the browser to treat the iframe URL as
# new, so it re-fetches the studio instead of showing a cached copy.
if "embed_nonce" not in st.session_state:
    st.session_state.embed_nonce = int(time.time())


@st.cache_data(ttl=30, show_spinner=False)
def check_health(url: str, nonce: int) -> tuple[bool, float]:
    start = time.time()
    try:
        resp = requests.get(
            with_params(url, {"_v": nonce}),
            timeout=6,
            headers={"Cache-Control": "no-cache", "Pragma": "no-cache"},
        )
        elapsed = round((time.time() - start) * 1000)
        return resp.status_code < 400, elapsed
    except Exception:
        return False, round((time.time() - start) * 1000)


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("⚙️ Automation Studio")
st.caption("Build, test, and launch automations without leaving the hub.")

online, latency_ms = check_health(EMBED_URL, st.session_state.embed_nonce)
status_col, reload_col, link_col, height_col = st.columns([1.2, 1, 1, 2])

with status_col:
    if online:
        st.success(f"Online · {latency_ms} ms")
    else:
        st.error("Unreachable — open in a new tab to check directly")

with reload_col:
    if st.button("↻ Reload studio", use_container_width=True):
        st.session_state.embed_nonce = int(time.time())
        check_health.clear()
        st.rerun()

with link_col:
    st.link_button(
        "Open in new tab ↗",
        with_params(EMBED_URL, {"_v": st.session_state.embed_nonce}),
        use_container_width=True,
    )

with height_col:
    embed_height = st.slider("Embed height (px)", 500, 1400, 850, step=50)

auto_refresh = st.toggle(
    "Auto-reload every 5 minutes",
    value=False,
    help="Re-fetches the studio on a timer so a newly published version shows up without a manual reload.",
)
if auto_refresh:
    # Fragments need streamlit>=1.37. The first run only "primes" the timer so
    # we don't trigger an immediate rerun loop; later ticks reload the embed.
    @st.fragment(run_every=300)
    def _tick():
        if st.session_state.get("tick_primed"):
            st.session_state.embed_nonce = int(time.time())
            check_health.clear()
            st.rerun()
        st.session_state.tick_primed = True
    _tick()
else:
    st.session_state.tick_primed = False

st.divider()

# ---------------------------------------------------------------------------
# Layout: main embed + sidebar tools
# ---------------------------------------------------------------------------
main_col, side_col = st.columns([3, 1])

with main_col:
    components.iframe(
        with_params(EMBED_URL, {"_v": st.session_state.embed_nonce}),
        height=embed_height,
        scrolling=True,
    )
    st.caption(
        "Not seeing your latest changes? This embed shows the **published** version of the studio. "
        "In Lovable, click **Publish → Update** after editing, then press **↻ Reload studio** here."
    )

with side_col:
    st.subheader("📌 Quick templates")
    templates = {
        "Notion live analyzer": "template=notion-analyzer",
        "Notion live digest": "template=notion-digest",
        "Support triage desk": "template=support-triage",
        "Deploy watchdog": "template=deploy-watch",
    }
    for label, query in templates.items():
        key, value = query.split("=", 1)
        st.link_button(
            label,
            with_params(EMBED_URL, {key: value, "_v": st.session_state.embed_nonce}),
            use_container_width=True,
        )

    st.divider()
    st.subheader("📝 Notes & bookmarks")

    notes = load_notes()

    with st.form("add_note_form", clear_on_submit=True):
        note_title = st.text_input("Title")
        note_text = st.text_area("What does this automation do?", height=80)
        submitted = st.form_submit_button("Save note")
        if submitted and note_title.strip():
            notes.append(
                {
                    "title": note_title.strip(),
                    "text": note_text.strip(),
                    "saved_at": time.strftime("%Y-%m-%d %H:%M"),
                }
            )
            save_notes(notes)
            st.rerun()

    if notes:
        for i, n in enumerate(reversed(notes)):
            real_idx = len(notes) - 1 - i
            with st.expander(f"{n['title']} · {n['saved_at']}"):
                st.write(n.get("text") or "_(no description)_")
                if st.button("Delete", key=f"del_{real_idx}"):
                    notes.pop(real_idx)
                    save_notes(notes)
                    st.rerun()
    else:
        st.caption("No saved notes yet — automations you jot down here will show up on every visit.")

st.divider()
st.caption(
    "Tip: templates append a `?template=` query param to the embed URL, "
    "matching the real template IDs in chrishem-autostudio's catalog."
)
