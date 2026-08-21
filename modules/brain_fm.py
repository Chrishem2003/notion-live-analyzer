import streamlit as st
from modules.paywall import enforce_paywall

def render_brain_fm_studio():
    # Enforce strict paid paywall (No trials allowed)
    enforce_paywall(allowed_plans=["pro", "business", "premium"], feature_name="Brain FM Focus Soundscapes", allow_trial=False)

    st.title("ðŸ§  Brain FM & Neural Focus Soundscapes")
    st.caption("Acoustic brainwave entrainment to enhance deep focus and cognitive flow.")

    sound_type = st.selectbox(
        "Select Focus Neural State:",
        ["40Hz Beta/Gamma Waves (Hyper-Focus)", "10Hz Alpha Waves (Calm Productivity)", "Deep Brown Noise (Distraction Blocking)", "Ambient Rain & Coffee Shop (Calm Flow)"]
    )

    audio_sources = {
        "40Hz Beta/Gamma Waves (Hyper-Focus)": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
        "10Hz Alpha Waves (Calm Productivity)": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3",
        "Deep Brown Noise (Distraction Blocking)": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3",
        "Ambient Rain & Coffee Shop (Calm Flow)": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3"
    }

    st.markdown(f"#### Currently Playing: **{sound_type}**")
    st.audio(audio_sources[sound_type], format="audio/mp3", loop=True)

    st.markdown("""
        ---
        **ðŸ§  How Brainwave Entrainment Works:**
        * **40Hz Beta/Gamma:** Stimulates neural synchronization for complex problem solving and coding.
        * **10Hz Alpha:** Reduces anxiety and visual clutter while maintaining cognitive alertness.
    """)
