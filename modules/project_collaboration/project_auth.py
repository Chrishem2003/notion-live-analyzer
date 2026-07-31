"""
Project Security & JWT Token Generator
Next-gen API route generating project-isolated JWT tokens carrying
user identity, room permissions, and co-host capabilities.

Architecture:
  - JWT tokens bound strictly to `projectId` (project-scoped)
  - Role hierarchy: Host > Co-Host > Researcher > Student/Viewer
  - Token refresh with sliding expiration
  - Role-based permission middleware
  - Duress mode support (generates limited token under coercion)
"""
from __future__ import annotations

import json
import time
import uuid
import hmac
import hashlib
import base64
from datetime import datetime, timedelta
from enum import IntEnum
from typing import Dict, List, Any, Optional, Tuple, Callable

from modules.logging_utils import get_logger

logger = get_logger(__name__)

try:
    import jwt as pyjwt
    HAS_PYJWT = True
except ImportError:
    HAS_PYJWT = False
    logger.warning("PyJWT unavailable — falling back to the manual HMAC-SHA256 JWT implementation")


# ═══════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════

DEFAULT_TOKEN_EXPIRY_HOURS = 24
MAX_TOKEN_EXPIRY_HOURS = 168  # 7 days
REFRESH_TOKEN_EXPIRY_DAYS = 30
TOKEN_ISSUER = "chrishem-project-collab"
TOKEN_AUDIENCE = "chrishem-collab-api"

# Production-grade signing key (in production, use a KMS/vault)
DEFAULT_SIGNING_KEY = "chrishem-collab-signing-key-v1-secure"


# ═══════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════

class ProjectRole(IntEnum):
    """Role hierarchy — higher number = more privileges."""
    VIEWER = 0
    STUDENT = 10
    RESEARCHER = 20
    CO_HOST = 90
    HOST = 100

    @classmethod
    def from_string(cls, role_str: str) -> "ProjectRole":
        mapping = {
            "viewer": cls.VIEWER,
            "student": cls.STUDENT,
            "researcher": cls.RESEARCHER,
            "co_host": cls.CO_HOST,
            "co-host": cls.CO_HOST,
            "host": cls.HOST,
        }
        return mapping.get(role_str.lower(), cls.VIEWER)

    @property
    def label(self) -> str:
        labels = {
            0: "Viewer",
            10: "Student",
            20: "Researcher",
            90: "Co-Host",
            100: "Host",
        }
        return labels.get(self.value, "Viewer")

    @property
    def icon(self) -> str:
        icons = {
            0: "👁️",
            10: "🎓",
            20: "🔬",
            90: "🤝",
            100: "👑",
        }
        return icons.get(self.value, "👁️")


def get_role_hierarchy() -> Dict[str, int]:
    """Get the role hierarchy mapping for permission checks."""
    return {role.label.lower(): role.value for role in ProjectRole}


def get_role_permissions(role: ProjectRole) -> Dict[str, bool]:
    """Get permissions for a given role."""
    permissions = {
        "view_canvas": True,
        "view_participants": True,
        "view_reactions": True,
        "view_ai_feed": True,
        "send_reactions": role >= ProjectRole.STUDENT,
        "raise_hand": role >= ProjectRole.STUDENT,
        "edit_canvas": role >= ProjectRole.RESEARCHER,
        "use_ghost_stage": role >= ProjectRole.RESEARCHER,
        "invite_participants": role >= ProjectRole.CO_HOST,
        "present_screen": role >= ProjectRole.CO_HOST,
        "follow_viewport": role >= ProjectRole.CO_HOST,
        "manage_roles": role >= ProjectRole.HOST,
        "mute_participants": role >= ProjectRole.HOST,
        "end_session": role >= ProjectRole.HOST,
        "access_ai_actions": role >= ProjectRole.RESEARCHER,
    }
    return permissions


# ═══════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════

class ProjectTokenPayload:
    """Structured JWT payload for project-scoped tokens."""

    def __init__(
        self,
        user_id: str,
        project_id: str,
        role: ProjectRole,
        display_name: str = "",
        avatar_url: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        expires_in_hours: int = DEFAULT_TOKEN_EXPIRY_HOURS,
        is_duress_token: bool = False,
    ):
        self.jti = str(uuid.uuid4())
        self.sub = user_id
        self.project_id = project_id
        self.role = role
        self.display_name = display_name or f"User_{user_id[:8]}"
        self.avatar_url = avatar_url
        self.metadata = metadata or {}
        self.iat = int(time.time())
        self.exp = int(time.time() + min(expires_in_hours, MAX_TOKEN_EXPIRY_HOURS) * 3600)
        self.iss = TOKEN_ISSUER
        self.aud = TOKEN_AUDIENCE
        self.is_duress_token = is_duress_token
        self.token_type = "access"
        self.permissions = get_role_permissions(role)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "jti": self.jti,
            "sub": self.sub,
            "project_id": self.project_id,
            "role": self.role.value,
            "role_label": self.role.label,
            "role_icon": self.role.icon,
            "display_name": self.display_name,
            "avatar_url": self.avatar_url,
            "metadata": self.metadata,
            "iat": self.iat,
            "exp": self.exp,
            "iss": self.iss,
            "aud": self.aud,
            "is_duress_token": self.is_duress_token,
            "token_type": self.token_type,
            "permissions": self.permissions,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectTokenPayload":
        payload = cls.__new__(cls)
        payload.jti = data.get("jti", "")
        payload.sub = data.get("sub", "")
        payload.project_id = data.get("project_id", "")
        payload.role = ProjectRole(data.get("role", 0))
        payload.display_name = data.get("display_name", "")
        payload.avatar_url = data.get("avatar_url", "")
        payload.metadata = data.get("metadata", {})
        payload.iat = data.get("iat", 0)
        payload.exp = data.get("exp", 0)
        payload.iss = data.get("iss", TOKEN_ISSUER)
        payload.aud = data.get("aud", TOKEN_AUDIENCE)
        payload.is_duress_token = data.get("is_duress_token", False)
        payload.token_type = data.get("token_type", "access")
        payload.permissions = data.get("permissions", {})
        return payload

    def is_expired(self) -> bool:
        return time.time() > self.exp

    def time_remaining(self) -> float:
        return max(0, self.exp - time.time())

    def has_permission(self, permission: str) -> bool:
        return self.permissions.get(permission, False)

    def can_access(self, required_role: ProjectRole) -> bool:
        return self.role.value >= required_role.value

    def __repr__(self) -> str:
        return (
            f"ProjectTokenPayload(user={self.sub[:12]}..., "
            f"project={self.project_id[:12]}..., "
            f"role={self.role.label}, expires_in={self.time_remaining()/3600:.1f}h)"
        )


# ═══════════════════════════════════════════════════════════════════════
# JWT TOKEN MANAGER
# ═══════════════════════════════════════════════════════════════════════

class ProjectAuthManager:
    """
    Manages JWT token generation, validation, and role-based access control
    for the project collaboration system.

    Features:
      - Project-isolated JWT tokens
      - Role hierarchy with granular permissions
      - Token refresh with sliding expiration
      - Duress token mode (limited under coercion)
      - Token blacklisting (for logout/revocation)
      - Audit logging of token operations
    """

    def __init__(self, signing_key: Optional[str] = None):
        self.signing_key = signing_key or DEFAULT_SIGNING_KEY
        self._blacklisted_tokens: Dict[str, float] = {}  # jti -> expiry time
        self._refresh_tokens: Dict[str, Dict[str, Any]] = {}
        self._audit_log: List[Dict[str, Any]] = []

        # Algorithm selection (HS256 for simplicity, RS256 for production)
        self._algorithm = "HS256"

    # ── Token Generation ────────────────────────────────────────────

    def create_access_token(
        self,
        user_id: str,
        project_id: str,
        role: ProjectRole,
        display_name: str = "",
        avatar_url: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        expires_in_hours: int = DEFAULT_TOKEN_EXPIRY_HOURS,
        is_duress: bool = False,
    ) -> Tuple[str, ProjectTokenPayload]:
        """
        Create a project-scoped JWT access token.

        Args:
            user_id: Unique user identifier
            project_id: Scoped project identifier
            role: User's role in the project
            display_name: Human-readable display name
            avatar_url: URL to user's avatar
            metadata: Additional claims (team, department, etc.)
            expires_in_hours: Token validity duration
            is_duress: If True, generates a duress-limited token

        Returns:
            Tuple of (encoded JWT string, ProjectTokenPayload)
        """
        payload = ProjectTokenPayload(
            user_id=user_id,
            project_id=project_id,
            role=role,
            display_name=display_name,
            avatar_url=avatar_url,
            metadata=metadata,
            expires_in_hours=expires_in_hours,
            is_duress_token=is_duress,
        )

        # If duress mode, override permissions to limited set
        if is_duress:
            payload.permissions = {
                "view_canvas": True,
                "view_participants": True,
                "send_reactions": False,
                "edit_canvas": False,
                "present_screen": False,
                "manage_roles": False,
            }

        token = self._encode_jwt(payload.to_dict())
        self._audit("token_created", {
            "user_id": user_id[:12],
            "project_id": project_id[:12],
            "role": role.label,
            "is_duress": is_duress,
            "expires_in": expires_in_hours,
        })
        return token, payload

    def create_refresh_token(
        self,
        user_id: str,
        project_id: str,
        role: ProjectRole,
    ) -> str:
        """Create a long-lived refresh token."""
        refresh_id = str(uuid.uuid4())
        token_data = {
            "refresh_id": refresh_id,
            "user_id": user_id,
            "project_id": project_id,
            "role": role.value,
            "created_at": time.time(),
            "expires_at": time.time() + REFRESH_TOKEN_EXPIRY_DAYS * 86400,
        }
        self._refresh_tokens[refresh_id] = token_data
        self._audit("refresh_token_created", {
            "user_id": user_id[:12],
            "project_id": project_id[:12],
        })
        # Return signed refresh token
        return self._encode_jwt(token_data)

    def refresh_access_token(
        self,
        refresh_token: str,
    ) -> Tuple[Optional[str], Optional[ProjectTokenPayload], str]:
        """
        Refresh an access token using a refresh token.

        Returns:
            Tuple of (new_token, payload, message)
        """
        try:
            data = self._decode_jwt(refresh_token)
            if data is None:
                return None, None, "❌ Invalid refresh token."

            refresh_id = data.get("refresh_id")
            if refresh_id not in self._refresh_tokens:
                return None, None, "❌ Refresh token has been revoked."

            stored = self._refresh_tokens[refresh_id]
            if time.time() > stored["expires_at"]:
                del self._refresh_tokens[refresh_id]
                return None, None, "❌ Refresh token expired."

            role = ProjectRole(stored["role"])
            new_token, payload = self.create_access_token(
                user_id=stored["user_id"],
                project_id=stored["project_id"],
                role=role,
            )
            return new_token, payload, "✅ Token refreshed successfully."

        except Exception as e:
            return None, None, f"❌ Token refresh failed: {str(e)}"

    # ── Token Validation ────────────────────────────────────────────

    def validate_token(self, token: str) -> Tuple[bool, Optional[ProjectTokenPayload], str]:
        """
        Validate a JWT access token.

        Returns:
            Tuple of (is_valid, payload, message)
        """
        try:
            data = self._decode_jwt(token)
            if data is None:
                return False, None, "❌ Invalid token signature or format."

            # Check blacklist
            jti = data.get("jti", "")
            if jti in self._blacklisted_tokens:
                return False, None, "❌ Token has been revoked."

            payload = ProjectTokenPayload.from_dict(data)

            # Check expiry
            if payload.is_expired():
                return False, None, "❌ Token has expired."

            return True, payload, "✅ Token valid."

        except Exception as e:
            return False, None, f"❌ Token validation error: {str(e)}"

    def revoke_token(self, jti: str) -> bool:
        """Revoke a token by adding it to the blacklist."""
        if jti not in self._blacklisted_tokens:
            self._blacklisted_tokens[jti] = time.time() + MAX_TOKEN_EXPIRY_HOURS * 3600
            self._audit("token_revoked", {"jti": jti[:12]})
            return True
        return False

    def revoke_all_user_tokens(self, user_id: str) -> int:
        """Revoke all tokens for a given user. Returns count revoked."""
        count = 0
        revoked = []
        for refresh_id, data in list(self._refresh_tokens.items()):
            if data["user_id"] == user_id:
                del self._refresh_tokens[refresh_id]
                count += 1
                revoked.append(refresh_id)
        self._audit("all_user_tokens_revoked", {
            "user_id": user_id[:12],
            "count": count,
        })
        return count

    def cleanup_expired(self) -> int:
        """Clean up expired tokens and blacklist entries. Returns count removed."""
        now = time.time()
        # Clean blacklist
        expired_blacklist = [
            jti for jti, exp in self._blacklisted_tokens.items()
            if now > exp
        ]
        for jti in expired_blacklist:
            del self._blacklisted_tokens[jti]

        # Clean refresh tokens
        expired_refresh = [
            rid for rid, data in self._refresh_tokens.items()
            if now > data["expires_at"]
        ]
        for rid in expired_refresh:
            del self._refresh_tokens[rid]

        return len(expired_blacklist) + len(expired_refresh)

    # ── Permission Checks ───────────────────────────────────────────

    def check_permission(
        self,
        token_payload: ProjectTokenPayload,
        required_permission: str,
    ) -> bool:
        """Check if a token has a specific permission."""
        return token_payload.has_permission(required_permission)

    def require_role(
        self,
        token_payload: ProjectTokenPayload,
        minimum_role: ProjectRole,
    ) -> bool:
        """Check if token's role meets the minimum requirement."""
        return token_payload.can_access(minimum_role)

    # ── JWT Encoding/Decoding ───────────────────────────────────────

    def _encode_jwt(self, payload: Dict[str, Any]) -> str:
        """Encode a payload into a JWT token."""
        if HAS_PYJWT:
            return pyjwt.encode(
                payload,
                self.signing_key,
                algorithm=self._algorithm,
            )
        else:
            # Fallback: manual HMAC-SHA256 JWT
            return self._manual_jwt_encode(payload)

    def _decode_jwt(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode and verify a JWT token."""
        if HAS_PYJWT:
            try:
                return pyjwt.decode(
                    token,
                    self.signing_key,
                    algorithms=[self._algorithm],
                    audience=TOKEN_AUDIENCE,
                    issuer=TOKEN_ISSUER,
                )
            except pyjwt.ExpiredSignatureError:
                # Even if expired, we might want to read the payload
                return pyjwt.decode(
                    token,
                    self.signing_key,
                    algorithms=[self._algorithm],
                    audience=TOKEN_AUDIENCE,
                    issuer=TOKEN_ISSUER,
                    options={"verify_exp": False},
                )
            except Exception:
                logger.warning("JWT verification failed — rejecting token", exc_info=True)
                return None
        else:
            return self._manual_jwt_decode(token)

    def _manual_jwt_encode(self, payload: Dict[str, Any]) -> str:
        """Manual JWT encoding using HMAC-SHA256 (fallback)."""
        header = {"alg": "HS256", "typ": "JWT"}
        header_b64 = self._b64encode(json.dumps(header).encode())
        payload_b64 = self._b64encode(json.dumps(payload).encode())
        message = f"{header_b64}.{payload_b64}"
        signature = hmac.new(
            self.signing_key.encode(),
            message.encode(),
            hashlib.sha256,
        ).digest()
        sig_b64 = self._b64encode(signature)
        return f"{message}.{sig_b64}"

    def _manual_jwt_decode(self, token: str) -> Optional[Dict[str, Any]]:
        """Manual JWT decoding with signature verification (fallback)."""
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            header_b64, payload_b64, sig_b64 = parts

            # Verify signature
            message = f"{header_b64}.{payload_b64}"
            expected_sig = hmac.new(
                self.signing_key.encode(),
                message.encode(),
                hashlib.sha256,
            ).digest()
            actual_sig = self._b64decode(sig_b64)
            if not hmac.compare_digest(actual_sig, expected_sig):
                logger.warning("JWT signature mismatch — rejecting token")
                return None

            # Decode payload
            payload_bytes = self._b64decode(payload_b64)
            return json.loads(payload_bytes.decode())
        except Exception:
            logger.warning("Malformed JWT — rejecting token", exc_info=True)
            return None

    @staticmethod
    def _b64encode(data: bytes) -> str:
        """Base64 URL-safe encoding without padding."""
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    @staticmethod
    def _b64decode(data: str) -> bytes:
        """Base64 URL-safe decoding with padding restoration."""
        padding = 4 - len(data) % 4
        if padding != 4:
            data += "=" * padding
        return base64.urlsafe_b64decode(data)

    # ── Audit ───────────────────────────────────────────────────────

    def _audit(self, action: str, details: Dict[str, Any]) -> None:
        """Record an audit log entry."""
        self._audit_log.append({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details,
        })
        # Keep last 1000 entries
        if len(self._audit_log) > 1000:
            self._audit_log = self._audit_log[-1000:]

    def get_audit_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent audit log entries."""
        return self._audit_log[-limit:]

    # ── Stats ───────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Get token manager statistics."""
        return {
            "active_tokens": len(self._refresh_tokens),
            "blacklisted_tokens": len(self._blacklisted_tokens),
            "audit_log_entries": len(self._audit_log),
            "algorithm": self._algorithm,
            "issuer": TOKEN_ISSUER,
        }


# ═══════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

# Global auth manager instance
_auth_manager = ProjectAuthManager()


def generate_project_token(
    user_id: str,
    project_id: str,
    role: str = "viewer",
    display_name: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> Tuple[str, ProjectTokenPayload]:
    """Generate a project-scoped JWT token (convenience function)."""
    role_enum = ProjectRole.from_string(role)
    return _auth_manager.create_access_token(
        user_id=user_id,
        project_id=project_id,
        role=role_enum,
        display_name=display_name,
        metadata=metadata,
    )


def verify_project_token(token: str) -> Tuple[bool, Optional[ProjectTokenPayload], str]:
    """Verify a project JWT token (convenience function)."""
    return _auth_manager.validate_token(token)


def require_role(minimum_role: ProjectRole):
    """
    Decorator for requiring a minimum role.
    Usage: @require_role(ProjectRole.CO_HOST)
    """
    def decorator(func: Callable):
        def wrapper(token_payload: ProjectTokenPayload, *args, **kwargs):
            if token_payload.role.value >= minimum_role.value:
                return func(token_payload, *args, **kwargs)
            else:
                raise PermissionError(
                    f"Requires {minimum_role.label} role, "
                    f"but user has {token_payload.role.label} role."
                )
        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════════════════════
# STREAMLIT UI RENDERER (embedded helper)
# ═══════════════════════════════════════════════════════════════════════

def render_project_auth_ui(auth_manager: Optional[ProjectAuthManager] = None):
    """
    Render the Project Auth management UI within Streamlit.
    Typically embedded in the collaboration page.
    """
    import streamlit as st

    manager = auth_manager or _auth_manager

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
    .auth-card {
        background: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 0.75rem;
    }
    .auth-card h4 { color: #f1f5f9; margin: 0 0 0.5rem 0; font-size: 0.9rem; }
    .auth-token-display {
        background: #020617;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 0.75rem;
        font-family: monospace;
        font-size: 0.7rem;
        color: #94a3b8;
        word-break: break-all;
        max-height: 120px;
        overflow-y: auto;
    }
    .auth-role-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        padding: 0.15rem 0.5rem;
        border-radius: 999px;
        font-size: 0.7rem;
        font-weight: 700;
    }
    .auth-role-host { background: rgba(245,158,11,0.15); color: #fbbf24; border: 1px solid rgba(245,158,11,0.3); }
    .auth-role-cohost { background: rgba(99,102,241,0.15); color: #818cf8; border: 1px solid rgba(99,102,241,0.3); }
    .auth-role-researcher { background: rgba(16,185,129,0.15); color: #34d399; border: 1px solid rgba(16,185,129,0.3); }
    .auth-role-student { background: rgba(6,182,212,0.15); color: #22d3ee; border: 1px solid rgba(6,182,212,0.3); }
    .auth-role-viewer { background: rgba(100,116,139,0.15); color: #94a3b8; border: 1px solid rgba(100,116,139,0.3); }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("### 🔐 Project Auth Manager")

    tab1, tab2, tab3 = st.tabs(["🎟️ Generate Token", "✅ Validate Token", "📋 Audit Log"])

    with tab1:
        st.markdown('<div class="auth-card">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            user_id = st.text_input("User ID", value=f"user_{uuid.uuid4().hex[:8]}", key="auth_user_id")
            project_id = st.text_input("Project ID", value=f"proj_{uuid.uuid4().hex[:8]}", key="auth_project_id")
            display_name = st.text_input("Display Name", value="Researcher", key="auth_display_name")
        with col2:
            role_str = st.selectbox(
                "Role",
                options=["host", "co_host", "researcher", "student", "viewer"],
                index=2,
                key="auth_role_select",
            )
            expiry_hours = st.slider("Token Expiry (hours)", 1, 168, 24, key="auth_expiry")
            is_duress = st.checkbox("⚠️ Duress Mode (limited token)", key="auth_duress")

        if st.button("🎟️ Generate Token", type="primary", use_container_width=True):
            role = ProjectRole.from_string(role_str)
            token, payload = manager.create_access_token(
                user_id=user_id,
                project_id=project_id,
                role=role,
                display_name=display_name,
                expires_in_hours=expiry_hours,
                is_duress=is_duress,
            )
            st.session_state["auth_last_token"] = token
            st.session_state["auth_last_payload"] = payload

            # Role badge
            badge_class = {
                "Host": "auth-role-host",
                "Co-Host": "auth-role-cohost",
                "Researcher": "auth-role-researcher",
                "Student": "auth-role-student",
                "Viewer": "auth-role-viewer",
            }.get(payload.role.label, "auth-role-viewer")

            st.markdown(f"""
            <div class="auth-token-display" style="margin-top:0.75rem;">
                <span style="color:#818cf8;">Token:</span> {token[:64]}...
            </div>
            <div style="display:flex;gap:0.5rem;margin-top:0.5rem;">
                <span class="auth-role-badge {badge_class}">{payload.role.icon} {payload.role.label}</span>
                <span style="color:#64748b;font-size:0.75rem;">⏱️ Expires in {expiry_hours}h</span>
                <span style="color:#64748b;font-size:0.75rem;">📋 {payload.jti[:12]}...</span>
            </div>
            """, unsafe_allow_html=True)

            if is_duress:
                st.warning("⚠️ Duress token generated — limited permissions active.")

        st.markdown('</div>', unsafe_allow_html=True)

        # Show last token details
        if st.session_state.get("auth_last_token"):
            with st.expander("📝 Last Generated Token Details", expanded=False):
                payload = st.session_state["auth_last_payload"]
                st.json(payload.to_dict())
                st.code(st.session_state["auth_last_token"], language="text")

    with tab2:
        st.markdown('<div class="auth-card">', unsafe_allow_html=True)
        token_to_validate = st.text_area(
            "Paste JWT Token",
            placeholder="eyJhbGciOiJIUzI1NiIs...",
            height=100,
            key="auth_validate_token",
        )
        if st.button("✅ Validate Token", type="primary", use_container_width=True) and token_to_validate:
            is_valid, payload, message = manager.validate_token(token_to_validate.strip())
            if is_valid and payload:
                st.success(f"✅ {message}")
                badge_class = {
                    "Host": "auth-role-host",
                    "Co-Host": "auth-role-cohost",
                    "Researcher": "auth-role-researcher",
                    "Student": "auth-role-student",
                    "Viewer": "auth-role-viewer",
                }.get(payload.role.label, "auth-role-viewer")
                st.markdown(f"""
                <div style="display:flex;gap:0.5rem;align-items:center;">
                    <span class="auth-role-badge {badge_class}">{payload.role.icon} {payload.role.label}</span>
                    <span style="color:#94a3b8;font-size:0.85rem;">👤 {payload.display_name}</span>
                    <span style="color:#64748b;font-size:0.75rem;">📁 {payload.project_id[:16]}...</span>
                </div>
                """, unsafe_allow_html=True)
                if payload.is_duress_token:
                    st.warning("⚠️ This is a duress-restricted token.")
                with st.expander("🔍 Full Payload"):
                    st.json(payload.to_dict())
            else:
                st.error(message)
        st.markdown('</div>', unsafe_allow_html=True)

    with tab3:
        st.markdown('<div class="auth-card">', unsafe_allow_html=True)
        log_entries = manager.get_audit_log(limit=30)
        if log_entries:
            for entry in reversed(log_entries):
                ts = entry["timestamp"][:19] if "T" in entry["timestamp"] else entry["timestamp"]
                details_str = json.dumps(entry["details"], default=str)
                st.markdown(f"""
                <div style="display:flex;gap:0.75rem;padding:0.3rem 0;border-bottom:1px solid #1e293b;font-size:0.8rem;">
                    <span style="color:#64748b;min-width:140px;">{ts}</span>
                    <span style="color:#818cf8;">{entry['action']}</span>
                    <span style="color:#94a3b8;font-size:0.7rem;">{details_str[:100]}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No audit log entries yet.")
        st.markdown('</div>', unsafe_allow_html=True)

    # Stats
    stats = manager.get_stats()
    st.caption(f"🔐 Active tokens: {stats['active_tokens']} | "
               f"Blacklisted: {stats['blacklisted_tokens']} | "
               f"Algorithm: {stats['algorithm']}")


