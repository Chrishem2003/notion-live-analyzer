
"""
Collaborative Canvas & Viewport Sync Engine (Yjs / CRDTs)
Production-grade CRDT-based collaborative workspace with:
  - Real-time collaborative project canvas with multi-user presence cursors
  - "Follow My Viewport" Presenter Mode: sync pan/zoom coordinates
  - Ghost Stage Mode: private workspace sandbox for co-hosts
  - LWW-Register based CRDT state management for conflict-free merging
  - Coordinate broadcasting system for viewport synchronization

Architecture:
  - LWW-Register (Last-Writer-Wins) CRDT for conflict-free concurrent edits
  - State Vector clock for causal ordering
  - Viewport coordinate broadcasting with interpolation
  - Ghost Stage as an isolated CRDT branch that can be merged to main
"""
from __future__ import annotations

import hashlib
import json
import math
import time
import uuid
from collections import OrderedDict
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Callable, Set


# ═══════════════════════════════════════════════════════════════════════
# ENUMS & CONSTANTS
# ═══════════════════════════════════════════════════════════════════════

class CursorType(str, Enum):
    DEFAULT = "default"
    TEXT = "text"
    CROSSHAIR = "crosshair"
    POINTER = "pointer"
    GRAB = "grab"
    SELECT = "select"
    DRAW = "draw"
    ERASE = "erase"


class ViewportSyncMode(str, Enum):
    FREE = "free"                  # Each user controls their own viewport
    FOLLOW_HOST = "follow_host"    # Follow the host's viewport
    FOLLOW_COHOST = "follow_cohost"  # Follow a co-host's viewport
    PRESENTATION = "presentation"  # Locked to presenter's view (no user control)


class CanvasElementType(str, Enum):
    TEXT_NOTE = "text_note"
    IMAGE = "image"
    SHAPE = "shape"
    ARROW = "arrow"
    STICKY = "sticky"
    CODE_BLOCK = "code_block"
    DATA_VIEW = "data_view"
    CHART = "chart"
    WIDGET = "widget"


class GhostStageState(str, Enum):
    IDLE = "idle"                # No ghost stage active
    EDITING = "editing"          # Co-host editing in ghost stage
    PENDING_REVIEW = "pending_review"  # Changes ready for review
    MERGING = "merging"          # Being merged to main canvas
    MERGED = "merged"            # Successfully merged


# CRDT Constants
MAX_HISTORY_SIZE = 1000
VIEWPORT_BROADCAST_INTERVAL = 0.05  # 50ms between viewport broadcasts
INTERPOLATION_FACTOR = 0.15  # Smoothing factor for viewport interpolation


# ═══════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════

class CursorPosition:
    """Represents a user's cursor position on the canvas."""

    def __init__(self, user_id: str, display_name: str, x: float = 0.0, y: float = 0.0,
                 cursor_type: CursorType = CursorType.DEFAULT,
                 color: str = "#6366f1", is_selection: bool = False):
        self.user_id = user_id
        self.display_name = display_name
        self.x = x
        self.y = y
        self.cursor_type = cursor_type
        self.color = color
        self.is_selection = is_selection
        self.selection_start_x: Optional[float] = None
        self.selection_start_y: Optional[float] = None
        self.last_updated = time.time()
        self.active_element_id: Optional[str] = None

    def update(self, x: float, y: float, cursor_type: Optional[CursorType] = None):
        """Update cursor position."""
        self.x = x
        self.y = y
        self.last_updated = time.time()
        if cursor_type:
            self.cursor_type = cursor_type

    def start_selection(self, x: float, y: float):
        """Start a selection rectangle."""
        self.is_selection = True
        self.selection_start_x = x
        self.selection_start_y = y

    def end_selection(self):
        """End the selection."""
        self.is_selection = False
        self.selection_start_x = None
        self.selection_start_y = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "user_id": self.user_id,
            "display_name": self.display_name,
            "x": self.x,
            "y": self.y,
            "cursor_type": self.cursor_type.value,
            "color": self.color,
            "is_selection": self.is_selection,
            "selection_start_x": self.selection_start_x,
            "selection_start_y": self.selection_start_y,
            "last_updated": self.last_updated,
            "active_element_id": self.active_element_id,
        }


class ViewportState:
    """
    Viewport state for a participant.
    Tracks pan (x, y) and zoom level for synchronized viewing.
    """

    def __init__(self, user_id: str, x: float = 0.0, y: float = 0.0,
                 zoom: float = 1.0, width: float = 1920, height: float = 1080):
        self.user_id = user_id
        self.x = x
        self.y = y
        self.zoom = zoom
        self.width = width
        self.height = height
        self.last_updated = time.time()

        # Interpolation target (for smooth following)
        self._target_x = x
        self._target_y = y
        self._target_zoom = zoom

    def update(self, x: float, y: float, zoom: float):
        """Update viewport state."""
        self._target_x = x
        self._target_y = y
        self._target_zoom = zoom
        self.last_updated = time.time()

    def interpolate(self, factor: float = INTERPOLATION_FACTOR) -> bool:
        """
        Smoothly interpolate toward the target position.
        Returns True if still converging, False if settled.
        """
        dx = self._target_x - self.x
        dy = self._target_y - self.y
        dz = self._target_zoom - self.zoom

        if abs(dx) < 0.5 and abs(dy) < 0.5 and abs(dz) < 0.001:
            self.x = self._target_x
            self.y = self._target_y
            self.zoom = self._target_zoom
            return False

        self.x = dx * factor
        self.y = dy * factor
        self.zoom = dz * factor
        return True

    def get_bounding_box(self) -> Dict[str, float]:
        """Get the visible bounding box in canvas coordinates."""
        half_w = (self.width / 2) / self.zoom
        half_h = (self.height / 2) / self.zoom
        return {
            "left": self.x - half_w,
            "right": self.x  half_w,
            "top": self.y - half_h,
            "bottom": self.y  half_h,
        }

    def is_visible(self, element_x: float, element_y: float,
                   margin: float = 100) -> bool:
        """Check if a point is visible in the current viewport."""
        bbox = self.get_bounding_box()
        return (bbox["left"] - margin <= element_x <= bbox["right"]  margin and
                bbox["top"] - margin <= element_y <= bbox["bottom"]  margin)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "user_id": self.user_id,
            "x": round(self.x, 1),
            "y": round(self.y, 1),
            "zoom": round(self.zoom, 3),
            "width": self.width,
            "height": self.height,
            "last_updated": self.last_updated,
        }


# ═══════════════════════════════════════════════════════════════════════
# CRDT ELEMENT
# ═══════════════════════════════════════════════════════════════════════

class CRDTElement:
    """
    A conflict-free replicated data type element using LWW-Register semantics.
    
    Each element has:
      - Unique ID (UUID)
      - Last-writer-wins timestamp for conflict resolution
      - State vector for causal ordering
      - Owner ID for access control
    """

    def __init__(self, element_id: str, element_type: CanvasElementType,
                 owner_id: str, x: float = 0.0, y: float = 0.0,
                 width: float = 200, height: float = 150,
                 content: Optional[Dict[str, Any]] = None):
        self.id = element_id
        self.type = element_type
        self.owner_id = owner_id
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.content = content or {}
        self.created_at = time.time()
        self.last_modified = time.time()
        self.version = 1
        self.is_deleted = False

        # CRDT metadata
        self.state_vector: Dict[str, int] = {owner_id: 1}  # Vector clock
        self.last_writer = owner_id
        self.last_write_time = time.time_ns()

    def update(self, updater_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update the element with LWW semantics.
        Returns True if the update was applied.
        """
        if self.is_deleted:
            return False

        # Increment state vector for updater
        self.state_vector[updater_id] = self.state_vector.get(updater_id, 0)  1

        # Apply updates (LWW  last writer wins per field)
        for key, value in updates.items():
            if hasattr(self, key) and key not in ("id", "owner_id", "created_at", "state_vector"):
                setattr(self, key, value)

        self.last_writer = updater_id
        self.last_write_time = time.time_ns()
        self.last_modified = time.time()
        self.version = 1
        return True

    def delete(self, deleter_id: str):
        """Soft-delete the element (tombstone)."""
        self.is_deleted = True
        self.last_writer = deleter_id
        self.last_write_time = time.time_ns()
        self.last_modified = time.time()

    def resolve_conflict(self, other: "CRDTElement") -> "CRDTElement":
        """
        Resolve conflicts between two versions of the same element.
        Uses LWW (Last-Writer-Wins) with tiebreaker on ID.
        """
        if self.last_write_time > other.last_write_time:
            return self
        elif other.last_write_time > self.last_write_time:
            return other
        else:
            # Same timestamp  use deterministic tiebreaker (higher ID wins)
            return self if self.id > other.id else other

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "owner_id": self.owner_id,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "content": self.content,
            "created_at": self.created_at,
            "last_modified": self.last_modified,
            "version": self.version,
            "is_deleted": self.is_deleted,
            "last_writer": self.last_writer,
        }


# ═══════════════════════════════════════════════════════════════════════
# GHOST STAGE
# ═══════════════════════════════════════════════════════════════════════

class GhostStage:
    """
    Ghost Stage Mode  Private workspace sandbox for co-hosts.
    
    Co-hosts can:
      - Edit content in an isolated branch
      - Stage changes without affecting the live canvas
      - Push changes live to all members when ready
      - Review diffs before merging
    
    Architecture:
      - Fork-based: creates a copy of the current canvas state
      - Changes are tracked as a patch set
      - Merge applies patches to the main canvas
    """

    def __init__(self, cohost_id: str, display_name: str):
        self.id = f"ghost_{uuid.uuid4().hex[:12]}"
        self.cohost_id = cohost_id
        self.display_name = display_name
        self.state = GhostStageState.IDLE
        self.created_at = datetime.now()

        # Forked elements (private sandbox)
        self.elements: Dict[str, CRDTElement] = {}

        # Patch tracking
        self.patches: List[Dict[str, Any]] = []
        self.base_snapshot_id: Optional[str] = None

        # Review
        self.review_notes: str = ""
        self.reviewers: List[str] = []

    def fork_from(self, main_elements: Dict[str, CRDTElement]):
        """Create a fork of the current canvas state."""
        self.state = GhostStageState.EDITING
        # Deep copy elements
        for eid, element in main_elements.items():
            if not element.is_deleted:
                new_elem = CRDTElement(
                    element_id=e.element_id,
                    element_type=e.type,
                    owner_id=self.cohost_id,
                    x=e.x, y=e.y,
                    width=e.width, height=e.height,
                    content=dict(e.content),
                )
                self.elements[eid] = new_elem

        self.base_snapshot_id = hashlib.sha256(
            json.dumps({eid: e.to_dict() for eid, e in self.elements.items()},
                       sort_keys=True).encode()
        ).hexdigest()[:16]

        self._log("forked", f"Ghost stage forked from main canvas")

    def add_element(self, element: CRDTElement):
        """Add an element to the ghost stage."""
        self.elements[element.id] = element
        self.patches.append({
            "type": "add",
            "element_id": element.id,
            "data": element.to_dict(),
            "timestamp": time.time(),
        })
        self._log("element_added", f"Added {element.type.value}: {element.id[:8]}")

    def update_element(self, element_id: str, updates: Dict[str, Any]) -> bool:
        """Update an element in the ghost stage."""
        if element_id not in self.elements:
            return False
        success = self.elements[element_id].update(self.cohost_id, updates)
        if success:
            self.patches.append({
                "type": "update",
                "element_id": element_id,
                "updates": updates,
                "timestamp": time.time(),
            })
        return success

    def delete_element(self, element_id: str) -> bool:
        """Soft-delete an element from the ghost stage."""
        if element_id not in self.elements:
            return False
        self.elements[element_id].delete(self.cohost_id)
        self.patches.append({
            "type": "delete",
            "element_id": element_id,
            "timestamp": time.time(),
        })
        return True

    def compute_diff(self, main_elements: Dict[str, CRDTElement]) -> Dict[str, Any]:
        """Compute the diff between ghost stage and main canvas."""
        additions = []
        modifications = []
        deletions = []

        for eid, ghost_elem in self.elements.items():
            if ghost_elem.is_deleted:
                deletions.append(eid)
            elif eid not in main_elements:
                additions.append(ghost_elem.to_dict())
            else:
                main_elem = main_elements[eid]
                if ghost_elem.last_write_time > main_elem.last_write_time:
                    modifications.append({
                        "element_id": eid,
                        "before": main_elem.to_dict(),
                        "after": ghost_elem.to_dict(),
                    })

        return {
            "additions": len(additions),
            "modifications": len(modifications),
            "deletions": len(deletions),
            "total_changes": len(additions)  len(modifications)  len(deletions),
            "additions_detail": additions[:10],  # Limit to 10 for display
            "modifications_detail": modifications[:10],
            "deletions_detail": deletions[:10],
        }

    def stage_for_review(self, notes: str = ""):
        """Mark the ghost stage as ready for review."""
        self.state = GhostStageState.PENDING_REVIEW
        self.review_notes = notes
        self._log("staged_for_review", f"Ghost stage ready for review: {len(self.patches)} patches")

    def merge_to_main(self, main_elements: Dict[str, CRDTElement]) -> Dict[str, Any]:
        """
        Merge ghost stage changes to the main canvas.
        Returns merge statistics.
        """
        self.state = GhostStageState.MERGING

        added = 0
        updated = 0
        deleted = 0

        for eid, ghost_elem in self.elements.items():
            if ghost_elem.is_deleted:
                if eid in main_elements:
                    main_elements[eid].delete(self.cohost_id)
                    deleted = 1
            elif eid in main_elements:
                # Merge  LWW wins
                winner = ghost_elem.resolve_conflict(main_elements[eid])
                main_elements[eid] = winner
                updated = 1
            else:
                # New element
                main_elements[eid] = ghost_elem
                added = 1

        self.state = GhostStageState.MERGED

        result = {
            "added": added,
            "updated": updated,
            "deleted": deleted,
            "total": added  updated  deleted,
            "merged_at": datetime.now().isoformat(),
        }

        self._log("merged", f"Merged to main: {added} ~{updated} -{deleted}")
        return result

    def discard(self):
        """Discard all ghost stage changes."""
        self.elements.clear()
        self.patches.clear()
        self.state = GhostStageState.IDLE
        self._log("discarded", "Ghost stage changes discarded")

    def _log(self, action: str, details: str = ""):
        """Internal action logging."""
        if "_audit_log" not in self.__dict__:
            self.audit_log = []
        self.audit_log.append({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details,
        })

    def get_state(self) -> Dict[str, Any]:
        """Get full ghost stage state."""
        return {
            "id": self.id,
            "cohost_id": self.cohost_id,
            "display_name": self.display_name,
            "state": self.state.value,
            "created_at": self.created_at.isoformat(),
            "element_count": len(self.elements),
            "patch_count": len(self.patches),
            "review_notes": self.review_notes,
            "base_snapshot_id": self.base_snapshot_id,
        }


# ═══════════════════════════════════════════════════════════════════════
# CANVAS SNAPSHOT
# ═══════════════════════════════════════════════════════════════════════

class CanvasSnapshot:
    """A snapshot of the canvas state for history and rollback."""

    def __init__(self, elements: Dict[str, CRDTElement], viewport: ViewportState,
                 label: str = ""):
        self.id = f"snap_{uuid.uuid4().hex[:12]}"
        self.timestamp = time.time()
        self.label = label
        self.element_count = len(elements)

        # Serialize elements
        self.elements_data = {
            eid: elem.to_dict() for eid, elem in elements.items()
        }
        self.viewport_data = viewport.to_dict()

        # Checksum for integrity
        self.checksum = hashlib.sha256(
            json.dumps(self.elements_data, sort_keys=True).encode()
        ).hexdigest()

    def verify_integrity(self) -> bool:
        """Verify snapshot integrity via checksum."""
        checksum = hashlib.sha256(
            json.dumps(self.elements_data, sort_keys=True).encode()
        ).hexdigest()
        return checksum == self.checksum

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "label": self.label,
            "element_count": self.element_count,
            "checksum": self.checksum[:16],
        }


# ═══════════════════════════════════════════════════════════════════════
# COLLABORATIVE CANVAS  Main Engine
# ═══════════════════════════════════════════════════════════════════════

class CollaborativeCanvas:
    """
    Real-time collaborative project canvas with CRDT-based conflict resolution,
    multi-user presence cursors, viewport synchronization, and ghost staging.

    Features:
      - LWW-Register CRDT for conflict-free concurrent editing
      - Multi-user cursor presence with custom cursor types
      - "Follow My Viewport" presenter mode
      - Ghost Stage sandbox for co-hosts
      - Canvas history with snapshots and rollback
      - Coordinate broadcasting for viewport sync
    """

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.elements: Dict[str, CRDTElement] = {}
        self.cursors: Dict[str, CursorPosition] = {}
        self.viewports: Dict[str, ViewportState] = {}
        self.local_user_id: Optional[str] = None
        self.local_role: str = "viewer"

        # Viewport sync
        self.viewport_sync_mode = ViewportSyncMode.FREE
        self.presenter_id: Optional[str] = None
        self.follow_target_id: Optional[str] = None

        # Ghost Stage
        self.ghost_stages: Dict[str, GhostStage] = {}

        # History
        self.snapshots: List[CanvasSnapshot] = []
        self._current_snapshot_id: Optional[str] = None

        # Event system
        self._event_listeners: Dict[str, List[Callable]] = {
            "cursor_moved": [],
            "element_added": [],
            "element_updated": [],
            "element_deleted": [],
            "viewport_changed": [],
            "sync_mode_changed": [],
            "ghost_stage_updated": [],
            "canvas_snapshot": [],
            "presenter_changed": [],
        }

        # Canvas metadata
        self.canvas_width = 4000
        self.canvas_height = 3000
        self.background_color = "#0f172a"
        self.grid_enabled = True
        self.grid_size = 20
        self.snap_to_grid = False

    # ── Event System ────────────────────────────────────────────────

    def on(self, event: str, callback: Callable):
        """Register an event listener."""
        if event in self._event_listeners:
            self._event_listeners[event].append(callback)

    def _emit(self, event: str, data: Any = None):
        """Emit an event to all registered listeners."""
        for cb in self._event_listeners.get(event, []):
            try:
                cb(data)
            except Exception:
                pass

    # ── User Management ─────────────────────────────────────────────

    def set_local_user(self, user_id: str, role: str = "viewer"):
        """Set the local user for this canvas."""
        self.local_user_id = user_id
        self.local_role = role

    def add_cursor(self, user_id: str, display_name: str,
                   color: Optional[str] = None) -> CursorPosition:
        """Add a cursor for a remote user."""
        if color is None:
            # Generate color from user_id hash
            hue = int(hashlib.md5(user_id.encode()).hexdigest()[:4], 16) % 360
            color = f"hsl({hue}, 70%, 60%)"

        cursor = CursorPosition(
            user_id=user_id,
            display_name=display_name,
            color=color,
        )
        self.cursors[user_id] = cursor
        return cursor

    def update_cursor(self, user_id: str, x: float, y: float,
                      cursor_type: Optional[CursorType] = None):
        """Update a user's cursor position."""
        cursor = self.cursors.get(user_id)
        if cursor:
            cursor.update(x, y, cursor_type)
            self._emit("cursor_moved", {"user_id": user_id, "x": x, "y": y})

    def remove_cursor(self, user_id: str):
        """Remove a user's cursor."""
        if user_id in self.cursors:
            del self.cursors[user_id]

    # ── Viewport Management ─────────────────────────────────────────

    def add_viewport(self, user_id: str, width: float = 1920,
                     height: float = 1080) -> ViewportState:
        """Add a viewport for a user."""
        viewport = ViewportState(user_id=user_id, width=width, height=height)
        self.viewports[user_id] = viewport
        return viewport

    def update_viewport(self, user_id: str, x: float, y: float, zoom: float):
        """Update a user's viewport position."""
        viewport = self.viewports.get(user_id)
        if viewport:
            viewport.update(x, y, zoom)
            self._emit("viewport_changed", {
                "user_id": user_id,
                "x": x, "y": y,
                "zoom": zoom,
            })

    def set_presenter(self, user_id: str):
        """Set the presenter for 'Follow My Viewport' mode."""
        self.presenter_id = user_id
        self.viewport_sync_mode = ViewportSyncMode.FOLLOW_HOST
        self.follow_target_id = user_id
        self._emit("presenter_changed", {"presenter_id": user_id})

    def clear_presenter(self):
        """Clear the presenter and return to free mode."""
        self.presenter_id = None
        self.follow_target_id = None
        self.viewport_sync_mode = ViewportSyncMode.FREE
        self._emit("presenter_changed", {"presenter_id": None})

    def set_sync_mode(self, mode: ViewportSyncMode, target_id: Optional[str] = None):
        """Set the viewport synchronization mode."""
        self.viewport_sync_mode = mode
        if mode == ViewportSyncMode.FOLLOW_HOST:
            self.follow_target_id = target_id or self.presenter_id
        elif mode == ViewportSyncMode.FOLLOW_COHOST:
            self.follow_target_id = target_id
        self._emit("sync_mode_changed", {
            "mode": mode.value,
            "target_id": self.follow_target_id,
        })

    def get_follow_viewport(self) -> Optional[ViewportState]:
        """Get the viewport to follow (if in follow mode)."""
        if self.viewport_sync_mode in (ViewportSyncMode.FOLLOW_HOST,
                                        ViewportSyncMode.FOLLOW_COHOST):
            if self.follow_target_id and self.follow_target_id in self.viewports:
                return self.viewports[self.follow_target_id]
        return None

    # ── Element Management (CRDT) ───────────────────────────────────

    def add_element(self, element_type: CanvasElementType, owner_id: str,
                    x: float, y: float, width: float = 200, height: float = 150,
                    content: Optional[Dict[str, Any]] = None) -> CRDTElement:
        """Add a new element to the canvas with CRDT semantics."""
        if self.snap_to_grid:
            x = round(x / self.grid_size) * self.grid_size
            y = round(y / self.grid_size) * self.grid_size

        element_id = f"elem_{uuid.uuid4().hex[:16]}"
        element = CRDTElement(
            element_id=element_id,
            element_type=element_type,
            owner_id=owner_id,
            x=x, y=y,
            width=width, height=height,
            content=content,
        )
        self.elements[element_id] = element
        self._emit("element_added", element.to_dict())
        return element

    def update_element(self, element_id: str, updater_id: str,
                       updates: Dict[str, Any]) -> bool:
        """Update an element (LWW CRDT)."""
        element = self.elements.get(element_id)
        if not element:
            return False

        if self.snap_to_grid:
            if "x" in updates:
                updates["x"] = round(updates["x"] / self.grid_size) * self.grid_size
            if "y" in updates:
                updates["y"] = round(updates["y"] / self.grid_size) * self.grid_size

        success = element.update(updater_id, updates)
        if success:
            self._emit("element_updated", {
                "element_id": element_id,
                "updater_id": updater_id,
                "updates": updates,
            })
        return success

    def delete_element(self, element_id: str, deleter_id: str) -> bool:
        """Soft-delete an element (tombstone CRDT pattern)."""
        element = self.elements.get(element_id)
        if not element:
            return False
        element.delete(deleter_id)
        self._emit("element_deleted", {"element_id": element_id, "deleter_id": deleter_id})
        return True

    def get_element(self, element_id: str) -> Optional[CRDTElement]:
        """Get a non-deleted element by ID."""
        element = self.elements.get(element_id)
        if element and not element.is_deleted:
            return element
        return None

    def list_elements(self, include_deleted: bool = False,
                      element_type: Optional[CanvasElementType] = None) -> List[CRDTElement]:
        """List all elements, optionally filtered by type."""
        results = []
        for element in self.elements.values():
            if not include_deleted and element.is_deleted:
                continue
            if element_type and element.type != element_type:
                continue
            results.append(element)
        return results

    def get_elements_in_viewport(self, viewport: ViewportState,
                                 margin: float = 200) -> List[CRDTElement]:
        """Get all elements visible in a given viewport."""
        bbox = viewport.get_bounding_box()
        bbox["left"] -= margin
        bbox["right"] = margin
        bbox["top"] -= margin
        bbox["bottom"] = margin

        visible = []
        for element in self.elements.values():
            if element.is_deleted:
                continue
            if (bbox["left"] <= element.x <= bbox["right"] and
                    bbox["top"] <= element.y <= bbox["bottom"]):
                visible.append(element)
        return visible

    # ── Ghost Stage ─────────────────────────────────────────────────

    def start_ghost_stage(self, cohost_id: str, display_name: str) -> GhostStage:
        """Start a new ghost stage session for a co-host."""
        ghost = GhostStage(cohost_id, display_name)
        ghost.fork_from(self.elements)
        self.ghost_stages[ghost.id] = ghost
        self._emit("ghost_stage_updated", ghost.get_state())
        return ghost

    def get_active_ghost_stages(self) -> List[GhostStage]:
        """Get all currently active (non-merged, non-idle) ghost stages."""
        return [
            gs for gs in self.ghost_stages.values()
            if gs.state in (GhostStageState.EDITING, GhostStageState.PENDING_REVIEW)
        ]

    # ── History & Snapshots ─────────────────────────────────────────

    def take_snapshot(self, viewport: ViewportState, label: str = "") -> CanvasSnapshot:
        """Take a snapshot of the current canvas state."""
        snapshot = CanvasSnapshot(self.elements, viewport, label)
        self.snapshots.append(snapshot)

        # Limit history
        if len(self.snapshots) > MAX_HISTORY_SIZE:
            self.snapshots = self.snapshots[-MAX_HISTORY_SIZE:]

        self._current_snapshot_id = snapshot.id
        self._emit("canvas_snapshot", {"snapshot_id": snapshot.id, "label": label})
        return snapshot

    def rollback_to_snapshot(self, snapshot_id: str) -> bool:
        """
        Rollback the canvas to a previous snapshot state.
        Returns True if successful.
        """
        for snapshot in self.snapshots:
            if snapshot.id == snapshot_id:
                if not snapshot.verify_integrity():
                    return False

                # Restore elements from snapshot data
                self.elements.clear()
                for eid, elem_data in snapshot.elements_data.items():
                    element = CRDTElement(
                        element_id=elem_data["id"],
                        element_type=CanvasElementType(elem_data["type"]),
                        owner_id=elem_data["owner_id"],
                        x=elem_data["x"], y=elem_data["y"],
                        width=elem_data["width"], height=elem_data["height"],
                        content=elem_data.get("content", {}),
                    )
                    element.created_at = elem_data.get("created_at", time.time())
                    element.last_modified = elem_data.get("last_modified", time.time())
                    element.version = elem_data.get("version", 1)
                    element.is_deleted = elem_data.get("is_deleted", False)
                    self.elements[eid] = element

                return True
        return False

    # ── Serialization ───────────────────────────────────────────────

    def export_canvas(self) -> Dict[str, Any]:
        """Export the entire canvas state as a serializable dict."""
        return {
            "project_id": self.project_id,
            "exported_at": datetime.now().isoformat(),
            "element_count": len(self.elements),
            "active_element_count": sum(1 for e in self.elements.values() if not e.is_deleted),
            "elements": {
                eid: elem.to_dict() for eid, elem in self.elements.items()
            },
            "canvas_width": self.canvas_width,
            "canvas_height": self.canvas_height,
            "background_color": self.background_color,
            "grid_enabled": self.grid_enabled,
            "grid_size": self.grid_size,
        }

    def get_canvas_state(self) -> Dict[str, Any]:
        """Get a lightweight summary of the canvas state."""
        active_elements = [e for e in self.elements.values() if not e.is_deleted]
        type_counts: Dict[str, int] = {}
        for elem in active_elements:
            t = elem.type.value
            type_counts[t] = type_counts.get(t, 0)  1

        return {
            "project_id": self.project_id,
            "total_elements": len(active_elements),
            "type_breakdown": type_counts,
            "active_cursors": len(self.cursors),
            "sync_mode": self.viewport_sync_mode.value,
            "presenter_id": self.presenter_id,
            "ghost_stages_active": len(self.get_active_ghost_stages()),
            "snapshot_count": len(self.snapshots),
            "canvas_width": self.canvas_width,
            "canvas_height": self.canvas_height,
        }

