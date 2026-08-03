
"""
Project Collaboration & Meeting System
A world-class, hybrid project collaboration & live meeting platform
combining Zoom, Figma, and Google Classroom capabilities.

Modules:
  - project_auth.py           JWT Token Generator & Role-Based Access Control
  - webrtc_provider.py        WebRTC  Spatial Audio  Denoising Engine
  - collaborative_canvas.py   Yjs/CRDT Canvas & Viewport Sync Engine
  - ai_researcher.py          AI Co-Researcher & Action-Item Detection

Architecture:
  - High-performance audio/video engine with adaptive HD streaming
  - Real-time project synchronization via CRDTs
  - AI-assisted research with speech-to-text and action-item detection
  - Role-based controls: Host, Co-Host, Researcher, Student/Viewer
  - Dual-track publishing: camera  presentation overlay streams
  - Spatial audio positioning based on participant cursor distances
"""

__version__ = "1.0.0"
__author__ = "CHRISHEM"

from .project_auth import (
    ProjectAuthManager,
    ProjectRole,
    ProjectTokenPayload,
    generate_project_token,
    verify_project_token,
    require_role,
    get_role_hierarchy,
    get_role_permissions,
)

from .webrtc_provider import (
    WebRTCProvider,
    SpatialAudioEngine,
    NoiseSuppressionEngine,
    Participant,
    ParticipantTrack,
    AudioSpatialPosition,
    TrackType,
    TrackQuality,
    ConnectionState,
)

from .collaborative_canvas import (
    CollaborativeCanvas,
    ViewportState,
    ViewportSyncMode,
    CursorPosition,
    CursorType,
    CRDTElement,
    CanvasElementType,
    GhostStage,
    GhostStageState,
    CanvasSnapshot,
)

from .ai_researcher import (
    AIResearcher,
    TranscriptProcessor,
    TranscriptSegment,
    TranscriptSource,
    ActionItemDetector,
    ActionItem,
    ActionItemPriority,
    ActionItemStatus,
    MeetingNote,
    NoteCategory,
    ResearchContext,
)

__all__ = [
    # Auth
    "ProjectAuthManager",
    "ProjectRole",
    "ProjectTokenPayload",
    "generate_project_token",
    "verify_project_token",
    "require_role",
    "get_role_hierarchy",
    "get_role_permissions",
    # WebRTC
    "WebRTCProvider",
    "SpatialAudioEngine",
    "NoiseSuppressionEngine",
    "Participant",
    "ParticipantTrack",
    "AudioSpatialPosition",
    "TrackType",
    "TrackQuality",
    "ConnectionState",
    # Canvas
    "CollaborativeCanvas",
    "ViewportState",
    "ViewportSyncMode",
    "CursorPosition",
    "CursorType",
    "CRDTElement",
    "CanvasElementType",
    "GhostStage",
    "GhostStageState",
    "CanvasSnapshot",
    # AI
    "AIResearcher",
    "TranscriptProcessor",
    "TranscriptSegment",
    "TranscriptSource",
    "ActionItemDetector",
    "ActionItem",
    "ActionItemPriority",
    "ActionItemStatus",
    "MeetingNote",
    "NoteCategory",
    "ResearchContext",
]

