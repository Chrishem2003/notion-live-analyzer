import av
import cv2
import numpy as np
import streamlit as st
from streamlit_webrtc import RTCConfiguration, WebRtcMode, webrtc_streamer

# Page Configuration
st.set_page_config(
    page_title="Project Collaboration | High-Definition Media Suite",
    page_icon="🎯",
    layout="wide",
)

st.title("🎯 High-Performance Real-Time Collaboration & Video Feed")
st.markdown(
    "Experience low-latency, high-grade WebRTC video streaming engineered for optimal clarity."
)

# Sidebar Control Suite for Advanced Stream Management
with st.sidebar:
  st.subheader("⚙️ Stream & Quality Controls")

  # Separate toggles for granular control
  enable_video = st.toggle("Enable Camera Feed", value=True)
  enable_audio = st.toggle("Enable Microphone Audio", value=True)

  st.markdown("---")
  st.subheader("🎨 Cinematic Filters (Apple-Grade FX)")
  filter_mode = st.selectbox(
      "Video Enhancement Profile",
      ["Standard HD", "Cinematic Contrast", "Studio Grayscale", "Edge Sharpen"],
  )

  # Mirror option for natural self-view
  mirror_feed = st.toggle("Mirror Video Stream", value=True)


# High-performance frame transformer mimicking studio-grade processing
def video_frame_callback(frame: av.VideoFrame) -> av.VideoFrame:
  img = frame.to_ndarray(format="bgr24")

  # Optional Mirroring
  if mirror_feed:
    img = cv2.flip(img, 1)

  # Apply professional post-processing based on selection
  if filter_mode == "Cinematic Contrast":
    # Enhance contrast and brightness algorithmically
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    limg = cv2.merge((cl, a, b))
    img = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

  elif filter_mode == "Studio Grayscale":
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

  elif filter_mode == "Edge Sharpen":
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    img = cv2.filter2D(img, -1, kernel)

  return av.VideoFrame.from_ndarray(img, format="bgr24")


# Public STUN Server configuration for robust connectivity across networks
RTC_CONFIGURATION = RTCConfiguration(
    {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
)

# Main layout container
col1, col2 = st.vertical_layout([3, 1]) if hasattr(st, "vertical_layout") else (st, st)

with st.container():
  st.info(
      "💡 **Tip:** Use the separate hardware toggles below the video window"
      " to control your camera and microphone independently without resetting"
      " the stream."
  )

  # WebRTC Streamer Component Execution
  webrtc_ctx = webrtc_streamer(
      key="project-collab-video-chat",
      mode=WebRtcMode.SENDRECV,
      rtc_configuration=RTC_CONFIGURATION,
      video_frame_callback=video_frame_callback,
      media_stream_constraints={
          "video": {"width": {"ideal": 1280}, "height": {"ideal": 720}}
          if enable_video
          else False,
          "audio": enable_audio,
      },
      media_toggle_controls=True,  # Enables clean independent hardware toggles
      async_processing=True,
  )

# Analytics / Session Status HUD
if webrtc_ctx.state.playing:
  st.success("🟢 Secure WebRTC Data Pipeline Active & Streaming.")
else:
  st.warning("⚠️ Stream is currently paused. Click 'START' above to initialize.")