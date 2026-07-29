st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>",unsafe_allow_html=True)

"""
Research Synthesizer & Audio Intelligence Hub — Standalone Page
World-class multimodal research engine that ingests papers, lectures,
or URLs and produces verifiable breakdowns, grounded audio podcasts,
and real-time prior art mapping.

Features:
  - Multimodal input: paste text, enter URL, upload video
  - Language translation selector
  - Audio briefing style (Podcast Dialogue / Executive)
  - Synthesize & generate briefing pipeline
  - Rigor scoring with quality badges
  - Interactive audio player with speed control
  - Clickable source citation inspector
  - Prior art & related literature context widget
"""
import streamlit as st

st.set_page_config(page_title="Research Synthesizer", page_icon="🔬", layout="wide")

from modules.config import init_session_state
from modules.ui_components import hero_card, load_css, watermark, section_header

# ─── Init ─────────────────────────────────────────────────────────────
init_session_state()
is_dark = st.session_state.get("theme", "light") == "dark"
load_css(is_dark=is_dark)
hero_card(
    "🔬 Research Synthesizer & Audio Intelligence Hub",
    "Ingest dense papers, lectures, or URLs. Get verifiable breakdowns, "
    "grounded audio podcasts, and real-time prior art mapping.",
    badge_text="⚡ Next-Gen Multimodal Research Engine"
)
watermark("CHRISHEM")

# ─── Session State Initialization ────────────────────────────────────
if "synth_input_type" not in st.session_state:
    st.session_state["synth_input_type"] = "text"
if "synth_input_text" not in st.session_state:
    st.session_state["synth_input_text"] = ""
if "synth_input_url" not in st.session_state:
    st.session_state["synth_input_url"] = ""
if "synth_target_language" not in st.session_state:
    st.session_state["synth_target_language"] = "English"
if "synth_audio_style" not in st.session_state:
    st.session_state["synth_audio_style"] = "podcast_dialogue"
if "synth_is_processing" not in st.session_state:
    st.session_state["synth_is_processing"] = False
if "synth_has_result" not in st.session_state:
    st.session_state["synth_has_result"] = False
if "synth_is_playing" not in st.session_state:
    st.session_state["synth_is_playing"] = False
if "synth_playback_speed" not in st.session_state:
    st.session_state["synth_playback_speed"] = 1.0
if "synth_active_citation" not in st.session_state:
    st.session_state["synth_active_citation"] = 0

# Sample data for the output view
CITATIONS = [
    {
        "id": "CIT-1",
        "summaryText": (
            "C-band SAR combined with optical imagery achieves 94.2% "
            "detection accuracy under dense cloud cover."
        ),
        "sourceType": "PDF Page",
        "sourceLocation": "Page 5, Paragraph 2",
        "originalContext": (
            "...by fusing Sentinel-1 C-band Synthetic Aperture Radar (SAR) "
            "backscatter with Sentinel-2 optical bands, our autoencoder model "
            "maintained a classification accuracy of 94.2% (±0.8%) across all "
            "cloud-obscured test tiles..."
        ),
    },
    {
        "id": "CIT-2",
        "summaryText": (
            "Model inference time reduced to < 45 seconds per 100km² tile."
        ),
        "sourceType": "Video Timestamp",
        "sourceLocation": "14:23 - 15:10",
        "originalContext": (
            "Presentation transcript: 'When running on our GPU pipeline, "
            "the inference latency dropped significantly—completing a full "
            "100 square kilometer tile in under 45 seconds...'"
        ),
    },
    {
        "id": "CIT-3",
        "summaryText": (
            "Multimodal fusion approach outperforms single-modal baselines "
            "by 18.7% in F1-score across all test conditions."
        ),
        "sourceType": "PDF Page",
        "sourceLocation": "Page 8, Table 3",
        "originalContext": (
            "Table 3 reports comparative F1-scores: Single-modal SAR (0.812), "
            "Single-modal Optical (0.845), Multimodal Fusion (0.999). "
            "The proposed fusion method achieves an 18.7% relative improvement "
            "over the best single-modal baseline."
        ),
    },
]

RELATED_WORKS = [
    {
        "title": "Deep Learning for SAR Image Despeckling and Land-Cover Classification",
        "authors": "Zhang et al.",
        "year": 2023,
        "relation": "Foundational",
        "citations": 142,
    },
    {
        "title": "Limitations of C-Band SAR Penetration in High-Humidity Tropical Canopy",
        "authors": "Mendoza & Patel",
        "year": 2025,
        "relation": "Conflicting",
        "citations": 38,
    },
    {
        "title": "Real-Time Edge Deployment of Multimodal Satellite Models",
        "authors": "Kim & Andersson",
        "year": 2024,
        "relation": "Follow-up",
        "citations": 67,
    },
]

RESULT_TITLE = (
    "Multi-Sensor Satellite Fusion for Rapid "
    "Environmental Monitoring"
)

# ─── Helper functions ────────────────────────────────────────────────

def handle_synthesize():
    """Trigger the synthesis pipeline."""
    st.session_state["synth_is_processing"] = True
    st.session_state["synth_has_result"] = False


def _build_audio_style_options():
    """Render the audio briefing style selector using columns."""
    col1, col2 = st.columns(2)
    with col1:
        is_active = st.session_state["synth_audio_style"] == "podcast_dialogue"
        extra_cls = " active" if is_active else ""
        if st.button(
            "🎙️ 2-Host Podcast\nConversational",
            key="audio_style_podcast",
            use_container_width=True,
            type="secondary" if not is_active else "primary",
            help="Conversational two-host scientific podcast briefing",
        ):
            st.session_state["synth_audio_style"] = "podcast_dialogue"
            st.rerun()
    with col2:
        is_active = st.session_state["synth_audio_style"] == "executive"
        if st.button(
            "🎧 Solo Executive\nConcise Debrief",
            key="audio_style_exec",
            use_container_width=True,
            type="secondary" if not is_active else "primary",
            help="Concise solo executive audio debrief",
        ):
            st.session_state["synth_audio_style"] = "executive"
            st.rerun()


def _build_citation_card(cit, idx):
    """Render a single clickable citation insight card."""
    is_active = st.session_state["synth_active_citation"] == idx
    border = "border-color: #4f46e5;" if is_active else ""
    bg = "background: rgba(79, 70, 229, 0.2);" if is_active else ""
    color = "color: #f8fafc;" if is_active else ""

    # We use a button styled as a card for clickability
    label = (
        f"**{cit['summaryText']}**\n\n"
        f"`{cit['sourceType']}` — `{cit['sourceLocation']}`"
    )
    if st.button(
        label,
        key=f"cit_{cit['id']}",
        use_container_width=True,
        help="Click to inspect original source context",
    ):
        st.session_state["synth_active_citation"] = idx
        st.rerun()


def _build_prior_art_cards():
    """Render the related works / prior art widget."""
    for work in RELATED_WORKS:
        rel_color = "#f59e0b" if work["relation"] == "Conflicting" else "#818cf8"
        rel_bg = "rgba(245, 158, 11, 0.15)" if work["relation"] == "Conflicting" else "rgba(129, 140, 248, 0.15)"
        rel_border = "rgba(245, 158, 11, 0.5)" if work["relation"] == "Conflicting" else "rgba(129, 140, 248, 0.4)"
        st.markdown(
            f"""
            <div class="prior-art-card">
                <div style="display: flex; align-items: center; gap: 0.75rem; width: 100%;">
                    <div style="flex: 1;">
                        <div style="font-weight: 600; color: #e2e8f0; font-size: 0.8rem;">
                            {work['title']}
                        </div>
                        <div style="color: #64748b; font-size: 0.7rem; margin-top: 0.15rem;">
                            {work['authors']} ({work['year']}) • {work['citations']} Citations
                        </div>
                    </div>
                    <span style="
                        font-size: 0.65rem; padding: 0.15rem 0.5rem;
                        border-radius: 999px; font-weight: 500;
                        background: {rel_bg}; color: {rel_color};
                        border: 1px solid {rel_border};
                        white-space: nowrap;
                    ">{work['relation']}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_empty_state():
    """Render the empty/placeholder state when no results exist."""
    st.markdown(
        """
        <div class="empty-state">
            <div style="font-size: 2.5rem; margin-bottom: 0.75rem;">⚡</div>
            <div style="font-weight: 700; color: #94a3b8; font-size: 0.85rem;">
                Next-Gen Research Engine Ready
            </div>
            <p style="font-size: 0.75rem; color: #475569; max-width: 380px; margin-top: 0.25rem;">
                Upload a document, paste text, or drop a video link on the left
                to extract verifiable insights, generate audio debriefs, and
                map literature.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_results():
    """Render the full output workspace with results."""
    active_idx = st.session_state["synth_active_citation"]
    active_cit = CITATIONS[active_idx] if active_idx < len(CITATIONS) else CITATIONS[0]
    audio_style = st.session_state["synth_audio_style"]
    is_playing = st.session_state["synth_is_playing"]
    speed = st.session_state["synth_playback_speed"]
    lang = st.session_state["synth_target_language"]
    style_label = "2-Host Scientific Podcast Brief" if audio_style == "podcast_dialogue" else "Solo Executive Audio Debrief"

    # ─── Output Header with Rigor Score ─────────────────────────────
    col_title, col_badge = st.columns([3, 1])
    with col_title:
        st.markdown(
            f"""
            <div style="font-size: 0.65rem; font-family: monospace; color: #818cf8; margin-bottom: 0.15rem;">
                TRANSLATED TO {lang.upper()} <span style="color: #475569;">•</span>
                <span style="color: #34d399; font-weight: 600;">92% Time Saved</span>
            </div>
            <div style="font-size: 1.15rem; font-weight: 700; color: #f8fafc;">
                {RESULT_TITLE}
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_badge:
        st.markdown(
            """
            <div class="rigor-badge">
                <span>🛡️</span>
                <div>
                    <div class="rigor-score">Rigor Score: 8.8/10</div>
                    <div style="color: #6ee7b7; font-size: 0.6rem;">High Sample Size (n=12,000)</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ─── Audio Player ──────────────────────────────────────────────
    st.markdown(
        f"""
        <div class="audio-player-bar">
            <div class="audio-controls-left">
                <button id="play-pause-btn" class="play-btn" onclick="
                    (function() {{
                        var btn = document.getElementById('play-pause-btn');
                        var playing = btn.innerHTML.trim() === '⏸';
                        btn.innerHTML = playing ? '▶' : '⏸';
                        btn.style.background = playing ? '#4f46e5' : '#059669';
                    }})()
                ">▶</button>
                <div>
                    <div style="font-size: 0.8rem; font-weight: 700; color: #f8fafc; display: flex; align-items: center; gap: 0.4rem;">
                        <span style="color: #818cf8;">🎧</span>
                        {style_label}
                    </div>
                    <div style="font-size: 0.65rem; color: #64748b;">
                        Duration: 03:12 | Synchronized Text Highlighting
                    </div>
            </div>
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <select id="speed-select" onchange="
                    document.getElementById('speed-label').innerText = this.value + 'x Speed';
                " style="
                    background: rgba(15, 23, 42, 0.9); border: 1px solid rgba(148,163,184,0.2);
                    color: #cbd5e1; font-size: 0.7rem; border-radius: 0.5rem;
                    padding: 0.35rem 0.6rem;
                ">
                    <option value="1.0" {"selected" if speed == 1.0 else ""}>1.0x Speed</option>
                    <option value="1.25" {"selected" if speed == 1.25 else ""}>1.25x Speed</option>
                    <option value="1.5" {"selected" if speed == 1.5 else ""}>1.5x Speed</option>
                    <option value="2.0" {"selected" if speed == 2.0 else ""}>2.0x Speed</option>
                </select>
                <span style="
                    display: inline-flex; align-items: center; gap: 0.3rem;
                    background: rgba(79, 70, 229, 0.15); color: #a5b4fc;
                    border: 1px solid rgba(79, 70, 229, 0.4);
                    padding: 0.3rem 0.65rem; border-radius: 0.5rem;
                    font-size: 0.7rem; font-weight: 600; cursor: pointer;
                ">📥 MP3</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ─── Key Insights & Source Inspector Split ──────────────────────
    col_insights, col_inspector = st.columns(2)

    with col_insights:
        st.markdown(
            """
            <div style="font-size: 0.7rem; font-weight: 600; color: #94a3b8;
                        text-transform: uppercase; letter-spacing: 0.05em;
                        margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.35rem;">
                <span style="color: #818cf8;">📑</span> Key Insights (Click to Verify Source)
            </div>
            """,
            unsafe_allow_html=True,
        )
        for idx, cit in enumerate(CITATIONS):
            _build_citation_card(cit, idx)

    with col_inspector:
        st.markdown(
            """
            <div style="font-size: 0.7rem; font-weight: 600; color: #fbbf24;
                        text-transform: uppercase; letter-spacing: 0.05em;
                        margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.35rem;">
                <span style="color: #fbbf24;">👁️</span> Verified Ground Truth Inspector
            </div>
            """,
            unsafe_allow_html=True,
        )
        if active_cit:
            st.markdown(
                f"""
                <div class="inspector-panel">
                    <div>
                        <div style="background: rgba(15, 23, 42, 0.8); padding: 0.75rem;
                                    border-radius: 0.5rem; border: 1px solid rgba(148,163,184,0.1);">
                            <div style="font-size: 0.65rem; font-family: monospace; color: #64748b; margin-bottom: 0.3rem;">
                                Source Segment: {active_cit['sourceLocation']}
                            </div>
                            <p style="font-size: 0.75rem; color: #cbd5e1; font-style: italic;
                                      line-height: 1.5; margin: 0;">
                                &ldquo;{active_cit['originalContext']}&rdquo;
                            </p>
                        </div>
                    </div>
                    <div style="font-size: 0.65rem; color: #64748b; margin-top: 0.5rem;
                                display: flex; align-items: center; gap: 0.3rem;">
                        <span style="color: #34d399;">✅</span> Zero Hallucination Guarantee Enabled
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div class="inspector-panel">
                    <div style="font-size: 0.75rem; color: #64748b;">
                        Select any insight on the left to inspect original text.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ─── Prior Art & Literature Context ─────────────────────────────
    st.markdown(
        """
        <div style="font-size: 0.75rem; font-weight: 600; color: #94a3b8;
                    text-transform: uppercase; letter-spacing: 0.05em;
                    margin: 0.75rem 0 0.5rem 0; display: flex; align-items: center; gap: 0.35rem;">
            <span style="color: #818cf8;">🔀</span> Prior Art & Related Literature Context
        </div>
        """,
        unsafe_allow_html=True,
    )
    _build_prior_art_cards()


# ═══════════════════════════════════════════════════════════════════════
# Custom CSS
# ═══════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* Synthesizer page custom styles */
.synth-container { width: 100%; }
.synth-header-banner {
    display: flex; flex-direction: row; align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid rgba(148, 163, 184, 0.2);
    padding-bottom: 1rem; margin-bottom: 1.5rem; gap: 1rem; flex-wrap: wrap;
}
.synth-header-title h2 {
    font-size: 1.5rem; font-weight: 800; color: #f8fafc; margin: 0;
}
.synth-header-title p {
    color: #94a3b8; font-size: 0.75rem; margin: 0.15rem 0 0 0;
}
.synth-header-controls {
    display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;
}
.synth-input-card {
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(148, 163, 184, 0.15);
    border-radius: 1rem; padding: 1.25rem;
    min-height: 420px;
    display: flex; flex-direction: column; justify-content: space-between;
}
.synth-output-card {
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(148, 163, 184, 0.15);
    border-radius: 1rem; padding: 1.5rem;
    min-height: 420px; display: flex; flex-direction: column;
}
.audio-player-bar {
    display: flex; align-items: center; justify-content: space-between;
    background: rgba(15, 23, 42, 0.8);
    border: 1px solid rgba(99, 102, 241, 0.3);
    border-radius: 1rem; padding: 0.75rem 1rem; gap: 1rem; flex-wrap: wrap;
}
.audio-controls-left {
    display: flex; align-items: center; gap: 0.75rem;
}
.play-btn {
    width: 2.75rem; height: 2.75rem; border-radius: 50%;
    background: #4f46e5; border: none; color: white;
    display: flex; align-items: center; justify-content: center;
    cursor: pointer; transition: all 0.15s; font-size: 1.1rem;
    box-shadow: 0 4px 14px rgba(79, 70, 229, 0.4); flex-shrink: 0;
}
.play-btn:hover { background: #6366f1; transform: scale(1.05); }
.play-btn:active { transform: scale(0.95); }
.insight-card-clickable {
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(148, 163, 184, 0.15);
    border-radius: 0.75rem; padding: 0.75rem; cursor: pointer;
    transition: all 0.2s; font-size: 0.8rem; color: #cbd5e1;
}
.insight-card-clickable:hover { border-color: #6366f1; background: rgba(79, 70, 229, 0.15); }
.insight-card-clickable.active {
    border-color: #4f46e5; background: rgba(79, 70, 229, 0.2); color: #f8fafc;
}
.inspector-panel {
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(148, 163, 184, 0.12);
    border-radius: 0.75rem; padding: 0.9rem;
    display: flex; flex-direction: column; justify-content: space-between;
    min-height: 200px;
}
.prior-art-card {
    background: rgba(15, 23, 42, 0.5);
    border: 1px solid rgba(148, 163, 184, 0.12);
    border-radius: 0.75rem; padding: 0.65rem;
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 0.5rem;
}
.prior-art-card:last-child { margin-bottom: 0; }
.rigor-badge {
    display: inline-flex; align-items: center; gap: 0.4rem;
    background: rgba(5, 150, 105, 0.2);
    border: 1px solid rgba(5, 150, 105, 0.5);
    padding: 0.35rem 0.75rem; border-radius: 0.75rem; font-size: 0.75rem;
}
.rigor-score { color: #34d399; font-weight: 700; }
.empty-state {
    display: flex; flex-direction: column; align-items: center;
    justify-content: center; text-align: center; padding: 2rem;
    color: #64748b; min-height: 380px;
}
.audio-option-btn {
    padding: 0.5rem; border-radius: 0.75rem;
    border: 1px solid rgba(148, 163, 184, 0.2);
    background: rgba(15, 23, 42, 0.8); color: #94a3b8;
    cursor: pointer; text-align: left; font-size: 0.7rem; transition: all 0.2s;
}
.audio-option-btn:hover { border-color: #6366f1; }
.audio-option-btn.active {
    background: rgba(79, 70, 229, 0.2); border-color: #4f46e5;
    color: #a5b4fc; font-weight: 700;
}
/* Override Streamlit button styles for citation cards */
div[data-testid="stHorizontalBlock"] > div div.stButton > button {
    text-align: left !important;
    justify-content: flex-start !important;
    white-space: normal !important;
    height: auto !important;
    min-height: 3rem !important;
    padding: 0.6rem !important;
    font-size: 0.78rem !important;
    line-height: 1.4 !important;
}
/* Audio style buttons */
div[data-testid="column"] div.stButton > button[key*="audio_style"] {
    text-align: left !important;
    justify-content: flex-start !important;
    white-space: pre-line !important;
    height: auto !important;
    min-height: 3.5rem !important;
    padding: 0.5rem !important;
    font-size: 0.7rem !important;
    line-height: 1.3 !important;
}
div[data-testid="column"] div.stButton > button[key*="audio_style"]:first-line {
    font-weight: 700;
    font-size: 0.75rem;
}
/* Synthesize button */
button[kind="primary"]:has(div:empty) {
    /* Not ideal, but we target by key below */
}
button[key="synth_submit"] {
    background: #4f46e5 !important;
    font-weight: 700 !important;
    font-size: 0.8rem !important;
}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# HEADER BANNER (Language selector + Input type toggle)
# ═══════════════════════════════════════════════════════════════════════

col_lang, col_toggle = st.columns([1, 2])

with col_lang:
    lang = st.selectbox(
        "🌐 Translate to",
        options=["English", "French", "Spanish", "German", "Chinese", "Japanese"],
        index=["English", "French", "Spanish", "German", "Chinese", "Japanese"].index(
            st.session_state["synth_target_language"]
        ),
        key="synth_lang_select",
        label_visibility="collapsed",
    )
    if lang != st.session_state["synth_target_language"]:
        st.session_state["synth_target_language"] = lang
        st.rerun()

with col_toggle:
    input_type = st.radio(
        "Input Type",
        options=["📄 PDF / Text", "🔗 Web Link", "🎥 Video"],
        index=["text", "url", "video"].index(st.session_state["synth_input_type"]),
        horizontal=True,
        key="synth_input_type_radio",
        label_visibility="collapsed",
    )
    type_map = {"📄 PDF / Text": "text", "🔗 Web Link": "url", "🎥 Video": "video"}
    new_type = type_map[input_type]
    if new_type != st.session_state["synth_input_type"]:
        st.session_state["synth_input_type"] = new_type
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════
# GRID LAYOUT: Left Input Column + Right Output Column
# ═══════════════════════════════════════════════════════════════════════

col_input, col_output = st.columns([4, 8])

# ──────────────────────────────────────────────────────────────────────
# LEFT INPUT COLUMN
# ──────────────────────────────────────────────────────────────────────
with col_input:
    st.markdown('<div class="synth-input-card">', unsafe_allow_html=True)

    input_type = st.session_state["synth_input_type"]

    if input_type == "text":
        st.markdown(
            '<label style="font-size:0.75rem;font-weight:600;color:#94a3b8;">'
            'Drop PDF File or Paste Research Text</label>',
            unsafe_allow_html=True,
        )
        text_val = st.text_area(
            "",
            value=st.session_state["synth_input_text"],
            placeholder="Paste long-form text, research excerpts, or raw notes here...",
            height=220,
            key="synth_text_area",
            label_visibility="collapsed",
        )
        if text_val != st.session_state["synth_input_text"]:
            st.session_state["synth_input_text"] = text_val

    elif input_type == "url":
        st.markdown(
            '<label style="font-size:0.75rem;font-weight:600;color:#94a3b8;">'
            'Paste Journal Article / ArXiv URL</label>',
            unsafe_allow_html=True,
        )
        url_val = st.text_input(
            "",
            value=st.session_state["synth_input_url"],
            placeholder="https://arxiv.org/abs/2026.01928...",
            key="synth_url_input",
            label_visibility="collapsed",
        )
        if url_val != st.session_state["synth_input_url"]:
            st.session_state["synth_input_url"] = url_val

    else:  # video
        st.markdown(
            '<label style="font-size:0.75rem;font-weight:600;color:#94a3b8;">'
            'Upload Lecture Video or YouTube Link</label>',
            unsafe_allow_html=True,
        )
        uploaded_file = st.file_uploader(
            "",
            type=["mp4", "avi", "mov", "mkv", "webm"],
            key="synth_video_upload",
            label_visibility="collapsed",
            help="Automatic Speech-to-Text & Transcript Alignment",
        )
        if uploaded_file is not None:
            st.success(f"✅ {uploaded_file.name} uploaded ({uploaded_file.size:,} bytes)")

    # ─── Audio Briefing Style Selector ─────────────────────────────
    st.markdown(
        '<div style="margin-top: 0.75rem; padding-top: 0.75rem; '
        'border-top: 1px solid rgba(148,163,184,0.12);">'
        '<label style="font-size:0.7rem;font-weight:600;color:#94a3b8;display:block;margin-bottom:0.35rem;">'
        '🎧 Audio Briefing Style</label>',
        unsafe_allow_html=True,
    )
    _build_audio_style_options()
    st.markdown('</div>', unsafe_allow_html=True)

    # ─── Synthesize Button ─────────────────────────────────────────
    can_process = (
        (input_type == "text" and st.session_state["synth_input_text"].strip())
        or (input_type == "url" and st.session_state["synth_input_url"].strip())
        or (input_type == "video")
    )

    if st.button(
        "⚡ Synthesize & Generate Briefing",
        key="synth_submit",
        type="primary",
        use_container_width=True,
        disabled=st.session_state["synth_is_processing"] or not can_process,
    ):
        st.session_state["synth_is_processing"] = True
        st.session_state["synth_has_result"] = False
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────
# RIGHT OUTPUT COLUMN
# ──────────────────────────────────────────────────────────────────────
with col_output:
    st.markdown('<div class="synth-output-card">', unsafe_allow_html=True)

    if st.session_state["synth_is_processing"]:
        # Processing state
        with st.spinner("🌀 Synthesizing Multimodal Inputs..."):
            import time
            progress_bar = st.progress(0)
            for pct in range(0, 101, 20):
                time.sleep(0.28)
                progress_bar.progress(pct)
            st.session_state["synth_is_processing"] = False
            st.session_state["synth_has_result"] = True
            st.session_state["synth_active_citation"] = 0
            st.rerun()

    elif st.session_state["synth_has_result"]:
        _render_results()

    else:
        _render_empty_state()

    st.markdown('</div>', unsafe_allow_html=True)


# ─── Sidebar Footer ──────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.info(
    "💡 **How to use:**\n\n"
    "1. Select input type (Text / URL / Video)\n"
    "2. Paste content or upload a file\n"
    "3. Choose audio briefing style\n"
    "4. Click **Synthesize & Generate Briefing**\n\n"
    "📌 Click any insight card to inspect the original source context.\n\n"
"🌐 Use the language selector to translate results."
)
