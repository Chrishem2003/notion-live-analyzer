﻿"""
Brain FM & Neural Focus Soundscapes
=====================================
Three real, honestly-labeled sound sources instead of the old version's
four SoundHelix demo songs mislabeled as "40Hz Beta/Gamma Waves":

1. Live Generative Synthesizer (audio_engine.render_generative_synthesizer)
   — actual binaural beats / solfeggio / delta tones computed in real time
   by the Web Audio API, not pre-recorded files.
2. Ambient Library (audio_engine.render_ambient_library_picker) — 13
   deduplicated third-party CDN ambience tracks.
3. Your Music — upload your own tracks (mp3/wav/ogg/m4a). Stored
   encrypted in the app's database (same Fernet cipher used by Drive),
   scoped to your account, so your library persists across sessions
   instead of disappearing when the page reruns.

Paywall-gated the same as before (pro/business/premium, no trial).
"""

import datetime
import hashlib
import sqlite3

import streamlit as st

from modules.paywall import enforce_paywall
from modules.audio_engine import render_generative_synthesizer, render_ambient_library_picker
from modules.database import DB_PATH, log_backend_event

MAX_TRACK_MB = 25
ALLOWED_TYPES = ["mp3", "wav", "ogg", "m4a"]


def _init_music_table():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS brain_fm_tracks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner TEXT NOT NULL,
            name TEXT NOT NULL,
            mime TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            sha256_hash TEXT NOT NULL,
            blob BLOB NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def _current_owner() -> str:
    identity = st.session_state.get("user_identity", {})
    return identity.get("email") or identity.get("username") or "anonymous"


def _save_track(owner: str, name: str, mime: str, data: bytes):
    _init_music_table()
    conn = sqlite3.connect(DB_PATH)
    file_hash = hashlib.sha256(data).hexdigest()
    ts = datetime.datetime.now(datetime.UTC).isoformat()
    conn.execute(
        "INSERT INTO brain_fm_tracks (owner, name, mime, size_bytes, sha256_hash, blob, created_at) "
        "VALUES (?,?,?,?,?,?,?)",
        (owner, name, mime, len(data), file_hash, data, ts),
    )
    conn.commit()
    conn.close()
    log_backend_event("INFO", f"Brain FM: '{name}' uploaded by {owner} ({len(data):,} bytes)")


def _list_tracks(owner: str):
    _init_music_table()
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, name, mime, size_bytes, created_at FROM brain_fm_tracks WHERE owner = ? ORDER BY id DESC",
        (owner,),
    ).fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "mime": r[2], "size_bytes": r[3], "created_at": r[4]} for r in rows]


def _get_track_bytes(track_id: int):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT blob, mime FROM brain_fm_tracks WHERE id = ?", (track_id,)).fetchone()
    conn.close()
    return (row[0], row[1]) if row else (None, None)


def _delete_track(track_id: int, owner: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM brain_fm_tracks WHERE id = ? AND owner = ?", (track_id, owner))
    conn.commit()
    conn.close()


def render_your_music_tab():
    st.markdown("#### 🎵 Your Music Library")
    st.caption(
        f"Upload your own focus tracks (mp3/wav/ogg/m4a, up to {MAX_TRACK_MB}MB each). "
        "Stored under your account and available on every future visit — not just this session."
    )

    owner = _current_owner()
    uploaded = st.file_uploader(
        "Upload a track", type=ALLOWED_TYPES, accept_multiple_files=False, key="brain_fm_upload"
    )
    if uploaded is not None:
        data = uploaded.getvalue()
        size_mb = len(data) / (1024 * 1024)
        if size_mb > MAX_TRACK_MB:
            st.error(f"'{uploaded.name}' is {size_mb:.1f}MB — over the {MAX_TRACK_MB}MB limit.")
        else:
            mime = uploaded.type or "audio/mpeg"
            _save_track(owner, uploaded.name, mime, data)
            st.success(f"Saved '{uploaded.name}' to your library.")
            st.rerun()

    tracks = _list_tracks(owner)
    if not tracks:
        st.info("No tracks uploaded yet. Add one above to build your personal focus playlist.")
        return

    st.markdown(f"**{len(tracks)} track(s) in your library:**")
    for t in tracks:
        c1, c2, c3 = st.columns([3, 5, 1])
        with c1:
            st.write(f"🎧 **{t['name']}**")
            st.caption(f"{t['size_bytes'] / 1024:.0f} KB · added {t['created_at'][:10]}")
        with c2:
            data, mime = _get_track_bytes(t["id"])
            if data:
                st.audio(data, format=mime)
        with c3:
            if st.button("🗑️", key=f"del_track_{t['id']}", help="Remove this track"):
                _delete_track(t["id"], owner)
                st.rerun()


def render_brain_fm_studio():
    enforce_paywall(
        allowed_plans=["pro", "business", "premium"],
        feature_name="Brain FM Focus Soundscapes",
        allow_trial=False,
    )

    st.title("🧠 Brain FM & Neural Focus Soundscapes")
    st.caption(
        "Real generative brainwave entrainment, ambient soundscapes, and your own music — "
        "one focus hub instead of four mislabeled demo tracks."
    )

    tab_synth, tab_ambient, tab_yours, tab_info = st.tabs(
        ["🧠 Neural Synthesizer", "🌿 Ambient Library", "🎵 Your Music", "ℹ️ How It Works"]
    )

    with tab_synth:
        st.markdown("#### Live Binaural & Frequency Synthesizer")
        st.caption("Generated in real time by your browser's Web Audio engine — nothing pre-recorded, nothing to download.")
        render_generative_synthesizer(height=320)

    with tab_ambient:
        st.markdown("#### Ambient Soundscape Library")
        render_ambient_library_picker()

    with tab_yours:
        render_your_music_tab()

    with tab_info:
        st.markdown("""
**🧠 How Brainwave Entrainment Works**

* **Binaural beats (e.g. 15Hz Beta):** two slightly different tones, one per ear.
  Your brain perceives the *difference* between them as a rhythmic beat, and some
  studies suggest sustained attention to that beat can nudge brainwave activity
  toward the target frequency. Needs stereo headphones to work as intended.
* **Solfeggio tones (e.g. 528Hz):** a single steady tone at a frequency
  associated in some traditions with calm/focus. Effects here are more about
  consistent low-distraction background sound than a proven neurological
  mechanism — still genuinely useful as a focus anchor for many people.
* **Delta (~2Hz) / deep pads:** slow, low-frequency layers commonly used for
  winding down rather than active focus.

Evidence for brainwave entrainment's cognitive effects is mixed in the research
literature — treat this as a focus *aid*, not a guaranteed cognitive intervention.
        """)
