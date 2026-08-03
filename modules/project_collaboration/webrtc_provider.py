
"""
WebRTC Provider  Enhanced Audio/Video Engine with Spatial Audio & Denoising
Production-grade WebRTC session management with:
  - Adaptive HD video streaming with low-latency WebRTC simulation
  - AI Noise Suppression / Background Denoising (Krisp SDK integration pattern)
  - Dual-Track Publishing: Camera  Presentation overlay streams
  - Spatial Audio Positioning: Pan audio tracks based on participant cursor distances
  - Participant grid management with role-based video layout

Architecture:
  - Session-based participant management
  - Spatial audio engine using 2D coordinate panning (L/R channels)
  - Noise suppression via spectral gating simulation
  - Dual-track: video (camera)  presentation (screen share overlay)
"""
from __future__ import annotations

import hashlib
import json
import math
import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Callable


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# ENUMS & CONSTANTS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class TrackType(str, Enum):
    CAMERA = "camera"
    PRESENTATION = "presentation"
    SCREEN_SHARE = "screen_share"
    AUDIO = "audio"


class TrackQuality(str, Enum):
    LOW = "low"          # 480p
    MEDIUM = "medium"    # 720p
    HIGH = "high"        # 1080p
    ULTRA = "ultra"      # 4K (simulated)


class ConnectionState(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


# Default video configurations
VIDEO_QUALITY_PRESETS = {
    TrackQuality.LOW: {"width": 640, "height": 480, "fps": 15, "bitrate": 500_000},
    TrackQuality.MEDIUM: {"width": 1280, "height": 720, "fps": 24, "bitrate": 1_500_000},
    TrackQuality.HIGH: {"width": 1920, "height": 1080, "fps": 30, "bitrate": 4_000_000},
    TrackQuality.ULTRA: {"width": 3840, "height": 2160, "fps": 60, "bitrate": 16_000_000},
}

# Audio processing constants
SAMPLE_RATE = 48000  # Hz
FFT_SIZE = 2048
NOISE_FLOOR_DB = -50
SPEECH_THRESHOLD_DB = -30
MAX_SPATIAL_DISTANCE = 1200  # pixels  beyond this, audio is fully panned
SPATIAL_PAN_RANGE = 0.8  # max pan amount (0-1)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# DATA MODELS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class AudioSpatialPosition:
    """
    Spatial audio position for a participant.
    Calculates stereo panning based on 2D cursor position relative to the local user.
    """

    def __init__(self, x: float = 0.0, y: float = 0.0):
        self.x = x
        self.y = y
        self._last_pan = 0.0
        self._last_volume = 1.0

    @staticmethod
    def calculate_pan(local_x: float, local_y: float,
                      remote_x: float, remote_y: float) -> float:
        """
        Calculate stereo pan value (-1.0 to 1.0) based on relative cursor position.
        -1.0 = full left, 0.0 = center, 1.0 = full right.

        Uses a logarithmic distance-based falloff to create natural spatial audio.
        """
        dx = remote_x - local_x
        dy = remote_y - local_y
        distance = math.sqrt(dx**2  dy**2)

        if distance < 10:
            return 0.0  # Too close  center

        # Calculate horizontal pan (left/right based on X axis)
        pan = max(-1.0, min(1.0, dx / MAX_SPATIAL_DISTANCE))

        # Apply distance-based falloff
        # Closer = more centered, further = more panned
        distance_factor = min(1.0, distance / MAX_SPATIAL_DISTANCE)
        pan *= distance_factor * SPATIAL_PAN_RANGE

        return pan

    @staticmethod
    def calculate_volume(local_x: float, local_y: float,
                         remote_x: float, remote_y: float,
                         min_volume: float = 0.3) -> float:
        """
        Calculate volume attenuation based on cursor distance.
        Closer cursors = louder, further = quieter.
        """
        dx = remote_x - local_x
        dy = remote_y - local_y
        distance = math.sqrt(dx**2  dy**2)

        if distance < 10:
            return 1.0  # Max volume

        # Exponential distance decay
        normalized_dist = min(1.0, distance / MAX_SPATIAL_DISTANCE)
        volume = 1.0 - (normalized_dist * (1.0 - min_volume))

        return max(min_volume, volume)

    def get_spatial_audio_params(self, local_x: float, local_y: float,
                                  remote_x: float, remote_y: float) -> Dict[str, float]:
        """Get complete spatial audio parameters for a participant."""
        pan = self.calculate_pan(local_x, local_y, remote_x, remote_y)
        volume = self.calculate_volume(local_x, local_y, remote_x, remote_y)
        self._last_pan = pan
        self._last_volume = volume

        return {
            "pan": pan,           # -1.0 (L) to 1.0 (R)
            "volume": volume,      # 0.0 to 1.0
            "distance": math.sqrt((remote_x - local_x)**2  (remote_y - local_y)**2),
            "azimuth": math.degrees(math.atan2(remote_y - local_y, remote_x - local_x)),
        }


class SpatialAudioEngine:
    """
    Session-level spatial audio mixer.

    Keeps the listener (local user) position and every remote participant's
    position, and derives per-participant stereo pan / volume from their cursor
    distance using :class:`AudioSpatialPosition`.
    """

    def __init__(self, min_volume: float = 0.3, enabled: bool = True):
        self.listener_x: float = 0.0
        self.listener_y: float = 0.0
        self.min_volume = max(0.0, min(1.0, min_volume))
        self._enabled = enabled
        self._positions: Dict[str, AudioSpatialPosition] = {}

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def toggle(self) -> bool:
        """Toggle spatial audio on/off. Returns the new state."""
        self._enabled = not self._enabled
        return self._enabled

    def set_listener_position(self, x: float, y: float):
        """Move the local listener."""
        self.listener_x = float(x)
        self.listener_y = float(y)

    def set_position(self, participant_id: str, x: float, y: float) -> AudioSpatialPosition:
        """Set (or create) a participant's spatial position."""
        position = self._positions.get(participant_id)
        if position is None:
            position = AudioSpatialPosition(x, y)
            self._positions[participant_id] = position
        else:
            position.x = float(x)
            position.y = float(y)
        return position

    def remove_participant(self, participant_id: str) -> bool:
        """Drop a participant from the mix. Returns True if it was present."""
        return self._positions.pop(participant_id, None) is not None

    def clear(self):
        """Remove all tracked participants."""
        self._positions.clear()

    def get_params(self, participant_id: str) -> Dict[str, float]:
        """
        Spatial audio parameters for one participant.
        Returns centered/full-volume parameters when the engine is disabled,
        and an empty dict for an unknown participant.
        """
        position = self._positions.get(participant_id)
        if position is None:
            return {}
        if not self._enabled:
            return {"pan": 0.0, "volume": 1.0, "distance": 0.0, "azimuth": 0.0}

        params = position.get_spatial_audio_params(
            self.listener_x, self.listener_y, position.x, position.y
        )
        params["volume"] = max(
            self.min_volume,
            AudioSpatialPosition.calculate_volume(
                self.listener_x, self.listener_y, position.x, position.y,
                min_volume=self.min_volume,
            ),
        )
        return params

    def mix(self) -> Dict[str, Dict[str, float]]:
        """Spatial audio parameters for every tracked participant."""
        return {pid: self.get_params(pid) for pid in self._positions}

    def get_state(self) -> Dict[str, Any]:
        """Current engine state."""
        return {
            "is_enabled": self._enabled,
            "listener": {"x": self.listener_x, "y": self.listener_y},
            "participant_count": len(self._positions),
            "min_volume": self.min_volume,
            "max_distance": MAX_SPATIAL_DISTANCE,
            "pan_range": SPATIAL_PAN_RANGE,
        }


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# NOISE SUPPRESSION ENGINE
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class NoiseSuppressionEngine:
    """
    AI Noise Suppression / Background Denoising Engine.
    Implements a spectral gating noise reduction algorithm (simulated Krisp SDK integration).

    In production, this would interface with Krisp SDK or RNNoise/Wenet for
    real-time neural noise suppression. This implementation provides the
    architectural pattern and algorithmic simulation.
    """

    def __init__(self, sample_rate: int = SAMPLE_RATE, fft_size: int = FFT_SIZE):
        self.sample_rate = sample_rate
        self.fft_size = fft_size
        self.noise_profile: Optional[Dict[str, float]] = None
        self.is_learning = False
        self.learning_duration = 2.0  # seconds to learn noise profile
        self.learning_start: Optional[float] = None
        self.suppression_strength: float = 0.85  # 0-1
        self._noise_samples: List[float] = []
        self._is_active = True

        # Spectral gating parameters
        self._noise_floor_db = NOISE_FLOOR_DB
        self._speech_threshold_db = SPEECH_THRESHOLD_DB
        self._gate_release_ms = 50  # milliseconds
        self._gate_attack_ms = 10   # milliseconds

    @property
    def is_active(self) -> bool:
        return self._is_active

    def toggle(self) -> bool:
        """Toggle noise suppression on/off."""
        self._is_active = not self._is_active
        return self._is_active

    def set_suppression_strength(self, strength: float):
        """Set suppression strength 0.0 (none) to 1.0 (aggressive)."""
        self.suppression_strength = max(0.0, min(1.0, strength))

    def start_learning_noise_profile(self):
        """Start learning the background noise profile."""
        self.is_learning = True
        self.learning_start = time.time()
        self._noise_samples = []

    def learn_noise_sample(self, audio_frame: bytes):
        """Feed an audio frame to the noise learning algorithm."""
        if not self.is_learning:
            return

        # Convert bytes to float samples (simulated)
        # In production: np.frombuffer(audio_frame, dtype=np.int16).astype(np.float32) / 32768.0
        self._noise_samples.append(time.time())

        # Check if learning period is complete
        if self.learning_start and (time.time() - self.learning_start) >= self.learning_duration:
            self._finalize_noise_profile()

    def _finalize_noise_profile(self):
        """Finalize the noise profile from collected samples."""
        # Simulated spectral analysis
        # In production: compute magnitude spectrum, estimate noise floor per frequency bin
        self.noise_profile = {
            "noise_floor_db": self._noise_floor_db,
            "speech_threshold_db": self._speech_threshold_db,
            "learned_at": datetime.now().isoformat(),
            "sample_count": len(self._noise_samples),
            "estimated_snr_db": 15.0  (self.suppression_strength * 10.0),
            "algorithm": "spectral_gating_v2",
            "frequency_bands": {
                "low": {"cutoff_hz": 300, "suppression": self.suppression_strength * 0.5},
                "mid": {"cutoff_hz": 3000, "suppression": self.suppression_strength * 0.8},
                "high": {"cutoff_hz": 8000, "suppression": self.suppression_strength * 0.6},
            }
        }
        self.is_learning = False
        self._noise_samples = []

    def process_audio_frame(self, audio_frame: bytes) -> bytes:
        """
        Apply noise suppression to an audio frame.
        Returns processed audio bytes.

        Uses spectral gating algorithm:
        1. Compute STFT
        2. Apply noise suppression mask
        3. Reconstruct audio via ISTFT
        """
        if not self._is_active or not self.noise_profile:
            return audio_frame  # Passthrough

        # Simulated processing delay
        # In production:
        #   spectrum = np.fft.rfft(audio_samples)
        #   magnitude = np.abs(spectrum)
        #   phase = np.angle(spectrum)
        #   noise_mask = (magnitude > noise_threshold).astype(float)
        #   clean_spectrum = spectrum * noise_mask
        #   clean_audio = np.fft.irfft(clean_spectrum)
        time.sleep(0.0001)  # ~0.1ms processing delay

        # Return processed audio (simulated  in production, returns denoised samples)
        return audio_frame

    def get_state(self) -> Dict[str, Any]:
        """Get current engine state."""
        return {
            "is_active": self._is_active,
            "is_learning": self.is_learning,
            "suppression_strength": self.suppression_strength,
            "noise_profile_learned": self.noise_profile is not None,
            "algorithm": "spectral_gating_v2",
            "sample_rate": self.sample_rate,
        }


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# PARTICIPANT MODELS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class ParticipantTrack:
    """A media track published by a participant."""

    def __init__(self, track_id: str, track_type: TrackType,
                 quality: TrackQuality = TrackQuality.MEDIUM):
        self.id = track_id
        self.type = track_type
        self.quality = quality
        self.is_published = False
        self.is_muted = False
        self.started_at: Optional[datetime] = None
        self.stopped_at: Optional[datetime] = None
        self.stats: Dict[str, Any] = {
            "packets_sent": 0,
            "packets_lost": 0,
            "bytes_sent": 0,
            "jitter_ms": 0,
            "rtt_ms": 0,
            "frame_rate": 0,
            "resolution": f"{VIDEO_QUALITY_PRESETS[quality]['width']}x{VIDEO_QUALITY_PRESETS[quality]['height']}",
        }

    def publish(self):
        """Publish this track."""
        self.is_published = True
        self.started_at = datetime.now()
        self.stats["packets_sent"] = 0
        self.stats["packets_lost"] = 0
        self.stats["bytes_sent"] = 0

    def unpublish(self):
        """Unpublish this track."""
        self.is_published = False
        self.stopped_at = datetime.now()

    def mute(self):
        """Mute this track."""
        self.is_muted = True

    def unmute(self):
        """Unmute this track."""
        self.is_muted = False

    def update_stats(self, packets_sent: int = 0, packets_lost: int = 0,
                     bytes_sent: int = 0, jitter_ms: float = 0,
                     rtt_ms: float = 0, frame_rate: float = 0):
        """Update track statistics."""
        self.stats["packets_sent"] = packets_sent
        self.stats["packets_lost"] = packets_lost
        self.stats["bytes_sent"] = bytes_sent
        self.stats["jitter_ms"] = jitter_ms
        self.stats["rtt_ms"] = rtt_ms
        self.stats["frame_rate"] = frame_rate

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "quality": self.quality.value,
            "is_published": self.is_published,
            "is_muted": self.is_muted,
            "stats": self.stats,
        }


class Participant:
    """Represents a participant in a WebRTC session."""

    def __init__(self, user_id: str, display_name: str, role: str = "viewer",
                 avatar_url: str = ""):
        self.id = user_id
        self.name = display_name
        self.role = role  # host, co_host, researcher, viewer
        self.avatar_url = avatar_url

        # Media tracks
        self.tracks: Dict[str, ParticipantTrack] = {}

        # Connection state
        self.connection_state = ConnectionState.DISCONNECTED
        self.joined_at: Optional[datetime] = None
        self.last_active_at: Optional[datetime] = None

        # Spatial audio
        self.spatial_position = AudioSpatialPosition()
        self.cursor_x: float = 0.0
        self.cursor_y: float = 0.0

        # Presence
        self.is_speaking = False
        self.is_video_on = False
        self.is_audio_on = False
        self.is_presenting = False
        self.is_hand_raised = False
        self.reaction: Optional[str] = None

        # Session stats
        self.audio_level: float = 0.0
        self.latency_ms: float = 0.0

    def add_track(self, track_type: TrackType, quality: TrackQuality = TrackQuality.MEDIUM) -> ParticipantTrack:
        """Add a new media track."""
        track_id = f"track_{self.id}_{track_type.value}_{uuid.uuid4().hex[:8]}"
        track = ParticipantTrack(track_id, track_type, quality)
        self.tracks[track_id] = track
        return track

    def get_track_by_type(self, track_type: TrackType) -> Optional[ParticipantTrack]:
        """Get the first track of a given type."""
        for track in self.tracks.values():
            if track.type == track_type:
                return track
        return None

    def update_cursor_position(self, x: float, y: float):
        """Update participant's cursor position for spatial audio."""
        self.cursor_x = x
        self.cursor_y = y

    def get_spatial_audio(self, local_x: float, local_y: float) -> Dict[str, float]:
        """Get spatial audio parameters relative to a local position."""
        return self.spatial_position.get_spatial_audio_params(
            local_x, local_y, self.cursor_x, self.cursor_y
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "avatar_url": self.avatar_url,
            "connection_state": self.connection_state.value,
            "joined_at": self.joined_at.isoformat() if self.joined_at else None,
            "is_speaking": self.is_speaking,
            "is_video_on": self.is_video_on,
            "is_audio_on": self.is_audio_on,
            "is_presenting": self.is_presenting,
            "is_hand_raised": self.is_hand_raised,
            "reaction": self.reaction,
            "cursor_position": {"x": self.cursor_x, "y": self.cursor_y},
            "tracks": {tid: t.to_dict() for tid, t in self.tracks.items()},
            "audio_level": self.audio_level,
            "latency_ms": self.latency_ms,
        }


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# WEBRTC PROVIDER  Main Session Manager
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class WebRTCProvider:
    """
    Enhanced WebRTC Provider managing media tracks, noise suppression,
    spatial audio calculation, and dual-stream publishing.

    Features:
      - Adaptive HD video streaming with quality presets
      - AI Noise Suppression integration (Krisp SDK pattern)
      - Dual-track publishing: camera  presentation overlay
      - Spatial audio positioning engine
      - Participant grid management with role-based layouts
      - Connection state lifecycle management
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.participants: Dict[str, Participant] = {}
        self.local_participant_id: Optional[str] = None

        # Noise suppression engine
        self.noise_suppression = NoiseSuppressionEngine()

        # Session state
        self.connection_state = ConnectionState.DISCONNECTED
        self.session_started_at: Optional[datetime] = None
        self.quality_preset = TrackQuality.HIGH

        # Dual-track publishing
        self._camera_track: Optional[ParticipantTrack] = None
        self._presentation_track: Optional[ParticipantTrack] = None
        self._presentation_active = False

        # Listeners / callbacks
        self._event_listeners: Dict[str, List[Callable]] = {
            "participant_joined": [],
            "participant_left": [],
            "track_published": [],
            "track_unpublished": [],
            "connection_state_changed": [],
            "spatial_audio_updated": [],
            "noise_suppression_changed": [],
            "presentation_started": [],
            "presentation_stopped": [],
        }

    # â”€â”€ Event System â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def on(self, event: str, callback: Callable):
        """Register an event listener."""
        if event in self._event_listeners:
            self._event_listeners[event].append(callback)

    def off(self, event: str, callback: Callable):
        """Remove an event listener."""
        if event in self._event_listeners and callback in self._event_listeners[event]:
            self._event_listeners[event].remove(callback)

    def _emit(self, event: str, data: Any = None):
        """Emit an event to all registered listeners."""
        for cb in self._event_listeners.get(event, []):
            try:
                cb(data)
            except Exception:
                pass

    # â”€â”€ Session Lifecycle â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def connect(self, user_id: str, display_name: str, role: str = "viewer") -> bool:
        """
        Connect to a WebRTC session.
        This establishes the local participant and initiates connection.
        """
        if self.connection_state == ConnectionState.CONNECTED:
            return True

        self.connection_state = ConnectionState.CONNECTING

        # Create local participant
        participant = Participant(
            user_id=user_id,
            display_name=display_name,
            role=role,
        )
        participant.connection_state = ConnectionState.CONNECTED
        participant.joined_at = datetime.now()
        participant.last_active_at = datetime.now()

        self.participants[user_id] = participant
        self.local_participant_id = user_id

        # Auto-publish camera and audio tracks
        camera_track = participant.add_track(TrackType.CAMERA, self.quality_preset)
        camera_track.publish()
        self._camera_track = camera_track

        audio_track = participant.add_track(TrackType.AUDIO)
        audio_track.publish()

        participant.is_video_on = True
        participant.is_audio_on = True

        self.connection_state = ConnectionState.CONNECTED
        self.session_started_at = datetime.now()

        self._emit("connection_state_changed", {"state": "connected"})
        self._emit("participant_joined", participant.to_dict())

        return True

    def disconnect(self):
        """Disconnect from the WebRTC session."""
        if self.connection_state == ConnectionState.DISCONNECTED:
            return

        # Clean up all participants
        for pid in list(self.participants.keys()):
            self._emit("participant_left", {"id": pid})
        self.participants.clear()

        self._camera_track = None
        self._presentation_track = None
        self._presentation_active = False
        self.local_participant_id = None
        self.connection_state = ConnectionState.DISCONNECTED
        self.session_started_at = None

        self._emit("connection_state_changed", {"state": "disconnected"})

    def reconnect(self):
        """Simulate reconnection."""
        if self.connection_state in (ConnectionState.DISCONNECTED, ConnectionState.CONNECTED):
            return
        self.connection_state = ConnectionState.RECONNECTING
        time.sleep(0.5)  # Simulate reconnection delay
        if self.local_participant_id and self.local_participant_id in self.participants:
            self.connection_state = ConnectionState.CONNECTED
            self._emit("connection_state_changed", {"state": "connected"})

    # â”€â”€ Participant Management â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def add_participant(self, user_id: str, display_name: str,
                        role: str = "viewer", avatar_url: str = "") -> Participant:
        """Add a remote participant to the session."""
        # If already exists, just return
        if user_id in self.participants:
            return self.participants[user_id]

        participant = Participant(user_id, display_name, role, avatar_url)
        participant.connection_state = ConnectionState.CONNECTED
        participant.joined_at = datetime.now()
        participant.last_active_at = datetime.now()

        self.participants[user_id] = participant
        self._emit("participant_joined", participant.to_dict())
        return participant

    def remove_participant(self, user_id: str):
        """Remove a participant from the session."""
        if user_id in self.participants:
            self._emit("participant_left", {"id": user_id})
            del self.participants[user_id]

    def get_participant(self, user_id: str) -> Optional[Participant]:
        """Get a participant by user ID."""
        return self.participants.get(user_id)

    def get_local_participant(self) -> Optional[Participant]:
        """Get the local participant."""
        if self.local_participant_id:
            return self.participants.get(self.local_participant_id)
        return None

    def get_participant_count(self) -> int:
        """Get total number of participants."""
        return len(self.participants)

    def get_active_speakers(self, threshold: float = 0.1) -> List[Participant]:
        """Get participants currently speaking above a threshold."""
        return [
            p for p in self.participants.values()
            if p.is_speaking and p.audio_level > threshold
        ]

    # â”€â”€ Track Management â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def start_presentation(self, user_id: str) -> bool:
        """
        Start a presentation overlay stream (dual-track publishing).
        The participant retains their camera track while also publishing
        a presentation overlay.
        """
        participant = self.participants.get(user_id)
        if not participant:
            return False

        # Create presentation track (dual-track)
        pres_track = participant.add_track(TrackType.PRESENTATION, TrackQuality.HIGH)
        pres_track.publish()
        self._presentation_track = pres_track
        self._presentation_active = True
        participant.is_presenting = True

        self._emit("presentation_started", {
            "user_id": user_id,
            "track_id": pres_track.id,
            "quality": pres_track.quality.value,
        })
        return True

    def stop_presentation(self, user_id: str) -> bool:
        """Stop the presentation overlay stream."""
        participant = self.participants.get(user_id)
        if not participant:
            return False

        pres_track = participant.get_track_by_type(TrackType.PRESENTATION)
        if pres_track:
            pres_track.unpublish()
            # Remove from tracks dict
            self.participants[user_id].tracks = {
                tid: t for tid, t in participant.tracks.items()
                if tid != pres_track.id
            }

        self._presentation_active = False
        self._presentation_track = None
        participant.is_presenting = False

        self._emit("presentation_stopped", {"user_id": user_id})
        return True

    def toggle_mute(self, user_id: str, track_type: TrackType = TrackType.AUDIO) -> bool:
        """Toggle mute for a participant's track."""
        participant = self.participants.get(user_id)
        if not participant:
            return False

        track = participant.get_track_by_type(track_type)
        if not track:
            return False

        if track.is_muted:
            track.unmute()
            if track_type == TrackType.AUDIO:
                participant.is_audio_on = True
        else:
            track.mute()
            if track_type == TrackType.AUDIO:
                participant.is_audio_on = False
            elif track_type == TrackType.CAMERA:
                participant.is_video_on = False

        return True

    # â”€â”€ Spatial Audio â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def update_spatial_audio(self) -> Dict[str, Dict[str, float]]:
        """
        Update spatial audio for all remote participants relative to the local user.
        Returns a dict of participant_id -> spatial audio parameters.
        """
        local = self.get_local_participant()
        if not local:
            return {}

        spatial_data = {}
        for pid, participant in self.participants.items():
            if pid == self.local_participant_id:
                continue

            params = participant.get_spatial_audio(local.cursor_x, local.cursor_y)
            spatial_data[pid] = params

        self._emit("spatial_audio_updated", spatial_data)
        return spatial_data

    def update_cursor_position(self, user_id: str, x: float, y: float):
        """Update a participant's cursor position (triggers spatial audio recalculation)."""
        participant = self.participants.get(user_id)
        if participant:
            participant.update_cursor_position(x, y)
            participant.last_active_at = datetime.now()

    # â”€â”€ Noise Suppression â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def toggle_noise_suppression(self) -> bool:
        """Toggle noise suppression on/off."""
        state = self.noise_suppression.toggle()
        self._emit("noise_suppression_changed", {"active": state})
        return state

    def set_noise_suppression_strength(self, strength: float):
        """Set noise suppression strength."""
        self.noise_suppression.set_suppression_strength(strength)
        self._emit("noise_suppression_changed", {"strength": strength})

    def learn_noise_profile(self):
        """Start learning the noise profile for suppression."""
        self.noise_suppression.start_learning_noise_profile()

    # â”€â”€ Quality Management â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def set_quality(self, quality: TrackQuality):
        """Set the video quality preset for all camera tracks."""
        self.quality_preset = quality
        preset = VIDEO_QUALITY_PRESETS[quality]

        # Update all camera tracks
        for participant in self.participants.values():
            camera = participant.get_track_by_type(TrackType.CAMERA)
            if camera:
                camera.quality = quality
                camera.stats["resolution"] = f"{preset['width']}x{preset['height']}"

    def get_network_stats(self) -> Dict[str, Any]:
        """Get aggregate network statistics for the session."""
        total_packets = 0
        total_lost = 0
        total_bytes = 0
        avg_jitter = 0.0
        avg_rtt = 0.0
        participant_count = max(1, len(self.participants))

        for participant in self.participants.values():
            for track in participant.tracks.values():
                total_packets = track.stats["packets_sent"]
                total_lost = track.stats["packets_lost"]
                total_bytes = track.stats["bytes_sent"]
                avg_jitter = track.stats["jitter_ms"]
                avg_rtt = track.stats["rtt_ms"]

        loss_rate = (total_lost / total_packets * 100) if total_packets > 0 else 0

        return {
            "total_packets": total_packets,
            "packet_loss_rate": round(loss_rate, 2),
            "total_bytes_sent": total_bytes,
            "avg_jitter_ms": round(avg_jitter / participant_count, 1),
            "avg_rtt_ms": round(avg_rtt / participant_count, 1),
            "active_participants": len(self.participants),
            "quality_preset": self.quality_preset.value,
            "noise_suppression_active": self.noise_suppression.is_active,
        }

    # â”€â”€ Reactions & Hand Raise â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def set_reaction(self, user_id: str, reaction: str):
        """Set a professional reaction for a participant."""
        participant = self.participants.get(user_id)
        if participant:
            participant.reaction = reaction

    def clear_reaction(self, user_id: str):
        """Clear the reaction for a participant."""
        participant = self.participants.get(user_id)
        if participant:
            participant.reaction = None

    def raise_hand(self, user_id: str, raised: bool = True):
        """Set hand-raise state for a participant."""
        participant = self.participants.get(user_id)
        if participant:
            participant.is_hand_raised = raised

    # â”€â”€ Session State â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def get_session_state(self) -> Dict[str, Any]:
        """Get the full session state as a serializable dict."""
        return {
            "session_id": self.session_id,
            "connection_state": self.connection_state.value,
            "session_started_at": self.session_started_at.isoformat() if self.session_started_at else None,
            "local_participant_id": self.local_participant_id,
            "participant_count": len(self.participants),
            "active_speakers": len(self.get_active_speakers()),
            "presentation_active": self._presentation_active,
            "quality_preset": self.quality_preset.value,
            "participants": {
                pid: p.to_dict() for pid, p in self.participants.items()
            },
            "network_stats": self.get_network_stats(),
            "noise_suppression": self.noise_suppression.get_state(),
        }


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# STREAMLIT UI RENDERER
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def render_webrtc_panel():
    """
    Render the WebRTC Provider panel in Streamlit.
    Manages media tracks, noise suppression, spatial audio, and dual-stream publishing.
    """
    import streamlit as st

    # â”€â”€ CSS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    st.markdown("""
    <style>
    /* --- GLOBAL SIDEBAR DARK THEMING OVERRIDE --- */
    [data-testid="stSidebar"], section[data-testid="stSidebar"] {
        background-color: #090d16 !important;
        border-right: 1px solid #1e293b !important;
    }
    
    /* Force all sidebar text, links, and headers to high-contrast off-white */
    [data-testid="stSidebar"] *, section[data-testid="stSidebar"] * {
        color: #f8fafc !important;
    }

    /* Target navigation links and text explicitly */
    [data-testid="stSidebarNav"] span, 
    [data-testid="stSidebarNav"] a,
    [data-testid="stSidebarNavLink"],
    [data-testid="stSidebarHeader"] {
        color: #f8fafc !important;
        font-weight: 600 !important;
    }

    /* Navigation item hover state */
    [data-testid="stSidebarNavLink"]:hover,
    [data-testid="stSidebarNav"] a:hover {
        background-color: #1e293b !important;
        border-radius: 8px !important;
    }

    /* Currently selected navigation item active state */
    [data-testid="stSidebarNavLink"][aria-current="page"],
    [data-testid="stSidebarNav"] a[aria-selected="true"] {
        background-color: #0284c7 !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
    }

    /* Custom form inputs inside sidebar */
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] .stMultiSelect label {
        color: #38bdf8 !important;
        font-weight: 700 !important;
    }
    .webrtc-container {
        background: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 16px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .webrtc-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 0.75rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #1e293b;
    }
    .webrtc-header-title {
        color: #f1f5f9;
        font-weight: 700;
        font-size: 0.95rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .webrtc-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        padding: 0.15rem 0.5rem;
        border-radius: 999px;
        font-size: 0.65rem;
        font-weight: 700;
    }
    .webrtc-badge-connected { background: rgba(16,185,129,0.15); color: #34d399; border: 1px solid rgba(16,185,129,0.3); }
    .webrtc-badge-disconnected { background: rgba(239,68,68,0.15); color: #f87171; border: 1px solid rgba(239,68,68,0.3); }
    .webrtc-badge-connecting { background: rgba(245,158,11,0.15); color: #fbbf24; border: 1px solid rgba(245,158,11,0.3); }
    .webrtc-participant-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 0.75rem;
        transition: border-color 0.2s;
    }
    .webrtc-participant-card:hover {
        border-color: #6366f1;
    }
    .webrtc-participant-name { color: #f1f5f9; font-weight: 600; font-size: 0.85rem; }
    .webrtc-participant-meta { color: #64748b; font-size: 0.7rem; margin-top: 0.15rem; }
    .webrtc-audio-visualizer {
        display: flex;
        align-items: flex-end;
        gap: 2px;
        height: 32px;
    }
    .webrtc-audio-bar {
        width: 4px;
        border-radius: 2px;
        background: linear-gradient(180deg, #6366f1, #818cf8);
        transition: height 0.15s;
    }
    .webrtc-controls-row {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
        align-items: center;
    }
    </style>
    """, unsafe_allow_html=True)

    # â”€â”€ Session Initialization â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if "webrtc_provider" not in st.session_state:
        st.session_state["webrtc_provider"] = None

    provider: Optional[WebRTCProvider] = st.session_state.get("webrtc_provider")

    st.markdown("### ðŸŽ¥ Media & Audio Engine")

    if not provider or provider.connection_state == ConnectionState.DISCONNECTED:
        # â”€â”€ Connection Form â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        with st.form("webrtc_connect_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                session_id = st.text_input("Session ID", value="session_001", key="webrtc_session_id")
            with col2:
                display_name = st.text_input("Display Name", value=f"User_{uuid.uuid4().hex[:6]}", key="webrtc_display_name")
            with col3:
                user_id = st.text_input("User ID", value=f"user_{uuid.uuid4().hex[:8]}", key="webrtc_user_id")

            role = st.selectbox("Role", options=["host", "co_host", "researcher", "viewer"],
                                 index=3, key="webrtc_role")

            if st.form_submit_button("ðŸŽ¥ Connect to Session", type="primary", use_container_width=True):
                provider = WebRTCProvider(session_id)
                provider.connect(user_id=user_id, display_name=display_name, role=role)
                st.session_state["webrtc_provider"] = provider
                st.rerun()
    else:
        # â”€â”€ Connected State â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        state = provider.connection_state
        badge_class = {
            ConnectionState.CONNECTED: "webrtc-badge-connected",
            ConnectionState.CONNECTING: "webrtc-badge-connecting",
            ConnectionState.RECONNECTING: "webrtc-badge-connecting",
            ConnectionState.DISCONNECTED: "webrtc-badge-disconnected",
            ConnectionState.FAILED: "webrtc-badge-disconnected",
        }.get(state, "webrtc-badge-disconnected")

        st.markdown(f"""
        <div class="webrtc-container">
            <div class="webrtc-header">
                <div class="webrtc-header-title">
                    ðŸŽ¥ Session: {provider.session_id}
                    <span class="webrtc-badge {badge_class}">â— {state.value}</span>
                </div>
                <div style="display:flex;gap:0.5rem;align-items:center;">
                    <span class="webrtc-badge webrtc-badge-connected">ðŸ‘¥ {provider.get_participant_count()}</span>
                    <span class="webrtc-badge webrtc-badge-connected">ðŸ“¡ {provider.quality_preset.value}</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # â”€â”€ Media Controls â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            q = st.selectbox("Quality", options=[q.value for q in TrackQuality],
                              index=1, key="webrtc_quality")
            provider.set_quality(TrackQuality(q))

        with col2:
            ns_active = provider.noise_suppression.is_active
            if st.toggle("ðŸ”‡ Noise Suppression", value=ns_active, key="webrtc_ns"):
                if not ns_active:
                    provider.toggle_noise_suppression()
                    provider.learn_noise_profile()
            else:
                if ns_active:
                    provider.toggle_noise_suppression()

        with col3:
            ns_strength = st.slider("Suppression", 0.0, 1.0,
                                     value=provider.noise_suppression.suppression_strength, key="webrtc_ns_strength")
            provider.set_noise_suppression_strength(ns_strength)

        with col4:
            if st.button("âŒ Disconnect", use_container_width=True):
                provider.disconnect()
                st.session_state["webrtc_provider"] = None
                st.rerun()

        # â”€â”€ Local Participant Info â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        local = provider.get_local_participant()
        if local:
            st.markdown(f"""
            <div class="webrtc-container">
                <div style="display:flex;align-items:center;gap:0.75rem;">
                    <div style="width:48px;height:48px;border-radius:12px;background:linear-gradient(135deg,#6366f1,#818cf8);
                                display:flex;align-items:center;justify-content:center;font-size:1.2rem;font-weight:700;color:white;">
                        {local.name[0].upper()}
                    </div>
                    <div style="flex:1;">
                        <div style="color:#f1f5f9;font-weight:600;">{local.name}</div>
                        <div style="color:#64748b;font-size:0.75rem;">@{local.id[:12]} Â· {local.role}</div>
                    </div>
                    <div style="display:flex;gap:0.5rem;">
                        <span class="webrtc-badge webrtc-badge-connected">ðŸ“¹ {'On' if local.is_video_on else 'Off'}</span>
                        <span class="webrtc-badge webrtc-badge-connected">ðŸŽ¤ {'On' if local.is_audio_on else 'Muted'}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # â”€â”€ Spatial Audio Visualizer â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        st.markdown("### ðŸŒŠ Spatial Audio Map")
        spatial_data = provider.update_spatial_audio()

        if spatial_data:
            cols = st.columns(min(4, len(spatial_data)))
            for idx, (pid, params) in enumerate(spatial_data.items()):
                p = provider.get_participant(pid)
                name = p.name if p else pid[:8]
                pan = params["pan"]
                vol = params["volume"]
                dist = params["distance"]
                az = params["azimuth"]

                # Visual pan indicator
                pan_pct = ((pan  1.0) / 2.0) * 100  # -1..1 -> 0..100
                vol_pct = vol * 100

                with cols[idx % 4]:
                    st.markdown(f"""
                    <div class="webrtc-participant-card">
                        <div class="webrtc-participant-name">{name}</div>
                        <div style="margin:0.5rem 0;">
                            <div style="display:flex;justify-content:space-between;font-size:0.65rem;color:#64748b;">
                                <span>L</span><span>Center</span><span>R</span>
                            </div>
                            <div style="background:#0f172a;border-radius:4px;height:6px;position:relative;margin-top:2px;">
                                <div style="position:absolute;left:{pan_pct}%;top:-3px;width:12px;height:12px;
                                            border-radius:50%;background:#818cf8;transform:translateX(-50%);"></div>
                            </div>
                        </div>
                        <div style="display:flex;justify-content:space-between;font-size:0.7rem;">
                            <span style="color:#34d399;">ðŸ”Š {vol_pct:.0f}%</span>
                            <span style="color:#94a3b8;">ðŸ“ {dist:.0f}px</span>
                            <span style="color:#64748b;">{az:.0f}Â°</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        # â”€â”€ Presentation Controls â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        st.markdown("### ðŸ“º Dual-Track Publishing")
        col1, col2 = st.columns(2)
        with col1:
            if not provider._presentation_active:
                if st.button(" Start Presentation Overlay", use_container_width=True):
                    provider.start_presentation(local.id)
                    st.rerun()
            else:
                if st.button("ðŸ›‘ Stop Presentation", use_container_width=True):
                    provider.stop_presentation(local.id)
                    st.rerun()

        with col2:
            if st.button("ðŸ¤š Raise Hand", use_container_width=True):
                local.is_hand_raised = not local.is_hand_raised

        # â”€â”€ Network Stats â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        with st.expander(" Network Statistics", expanded=False):
            stats = provider.get_network_stats()
            net_cols = st.columns(4)
            with net_cols[0]:
                st.metric("Participants", stats["active_participants"])
            with net_cols[1]:
                st.metric("Packet Loss", f"{stats['packet_loss_rate']}%")
            with net_cols[2]:
                st.metric("Avg RTT", f"{stats['avg_rtt_ms']}ms")
            with net_cols[3]:
                st.metric("Jitter", f"{stats['avg_jitter_ms']}ms")

            st.json(stats)

        # â”€â”€ Remote Participants â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        with st.expander(f"ðŸ‘¥ Participants ({provider.get_participant_count()})", expanded=True):
            for pid, p in provider.participants.items():
                if pid == provider.local_participant_id:
                    continue
                st.markdown(f"""
                <div class="webrtc-participant-card" style="margin-bottom:0.5rem;">
                    <div style="display:flex;align-items:center;gap:0.75rem;">
                        <div style="width:40px;height:40px;border-radius:10px;
                                    background:linear-gradient(135deg,#1e293b,#334155);
                                    display:flex;align-items:center;justify-content:center;font-weight:700;color:#94a3b8;">
                            {p.name[0].upper()}
                        </div>
                        <div style="flex:1;">
                            <div style="color:#f1f5f9;font-weight:600;font-size:0.85rem;">{p.name}</div>
                            <div style="color:#64748b;font-size:0.7rem;">{p.role} Â· {'ðŸŽ¤' if p.is_audio_on else 'ðŸ”‡'} {'ðŸ“¹' if p.is_video_on else 'ðŸ“¹âŒ'}</div>
                        </div>
                        <div>
                            {'ðŸ¤š' if p.is_hand_raised else ''}
                            {'' if p.is_presenting else ''}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# HELPER: Create a demo session with sample participants
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def create_demo_session() -> WebRTCProvider:
    """Create a WebRTC session with sample participants for demonstration."""
    provider = WebRTCProvider("demo_project_workspace")

    # Connect local host
    provider.connect("host_001", "Dr. Sarah Chen", "host")

    # Add remote participants
    provider.add_participant("cohost_001", "Prof. James Miller", "co_host")
    provider.add_participant("researcher_001", "Dr. Emily Watson", "researcher")
    provider.add_participant("viewer_001", "Alex Kim", "viewer")
    provider.add_participant("viewer_002", "Maria Garcia", "viewer")
    provider.add_participant("viewer_003", "David Park", "viewer")

    # Set some spatial positions for demo
    provider.update_cursor_position("cohost_001", 300, 200)
    provider.update_cursor_position("researcher_001", -200, 150)
    provider.update_cursor_position("viewer_001", 500, -100)
    provider.update_cursor_position("viewer_002", -400, -50)
    provider.update_cursor_position("viewer_003", 100, 300)

    # Start noise suppression
    provider.noise_suppression.start_learning_noise_profile()

    return provider


