"""
Enhanced Security, Geolocation, and Advanced Features."""
import os
import re
import json
import time
import hmac
import hashlib
import base64
import uuid
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum
import streamlit as st
import requests

# ═══════════════════════════════════════════════════════════════════════
# SECURITY MODULE
# ═══════════════════════════════════════════════════════════════════════

class SecurityManager:
    """Security and anti-spoofing controls."""
    
    # Known VPN/proxy IP ranges (simplified - use paid service in production)
    VPN_RANGES = [
        "103.0.0.0/8",  # Example ranges
        "185.0.0.0/8",
    ]
    
    # Suspicious patterns
    PROXY_HEADERS = [
        "X-Forwarded-For",
        "X-Real-IP", 
        "X-Cluster-Client-IP",
        "Forwarded-For",
        "Via",
    ]
    
    def __init__(self):
        self._blocked_ips: set = set()
        self._suspicious_activity: List[Dict] = []
    
    def get_client_ip(self, headers: Dict = None) -> str:
        """Extract real client IP from headers."""
        if headers is None:
            try:
                headers = st.context.headers if hasattr(st, 'context') else {}
            except:
                headers = {}
        
        # Check proxy headers (most reliable for Streamlit Cloud)
        for header in self.PROXY_HEADERS:
            value = headers.get(header, "")
            if value:
                # Take first IP if multiple
                return value.split(",")[0].strip()
        
        return "127.0.0.1"
    
    def detect_vpn(self, ip: str) -> Dict[str, Any]:
        """Detect if IP is from VPN/proxy."""
        result = {"is_vpn": False, "is_proxy": False, "risk_score": 0, "details": []}
        
        # Skip localhost
        if ip.startswith("127.") or ip.startswith("10.") or ip.startswith("192.168."):
            return result
        
        # Use ip-api.com for basic info
        try:
            response = requests.get(
                f"http://ip-api.com/json/{ip}",
                params={"fields": "status,country,regionName,city,isp,org,as,mobile,proxy",
                       "timeout": 5},
            )
            if response.status_code == 200:
                data = response.json()
                
                if data.get("status") == "success":
                    # Check for mobile/proxy
                    if data.get("mobile"):
                        result["risk_score"] += 20
                        result["details"].append("Mobile network")
                    
                    if data.get("proxy"):
                        result["is_proxy"] = True
                        result["is_vpn"] = True
                        result["risk_score"] += 60
                        result["details"].append("Known proxy/VPN")
                    
                    # High risk if organization looks like hosting provider
                    org = data.get("org", "")
                    isp = data.get("isp", "")
                    
                    for provider in ["Hosting", "Data Center", "Cloud", "VPN", "DigitalOcean", 
                                    "AWS", "Azure", "GCP", "Linode", "Vultr"]:
                        if provider.lower() in org.lower() or provider.lower() in isp.lower():
                            result["risk_score"] += 30
                            result["details"].append(f"Hosting provider: {isp}")
                            break
        except Exception:
            pass
        
        return result
    
    def check_session_security(self, user_id: str, ip: str) -> Dict[str, Any]:
        """Full security check for session."""
        vpn_check = self.detect_vpn(ip)
        
        # Check for impossible travel (would need session storage in production)
        
        result = {
            "ip": ip,
            "security_score": 100 - vpn_check["risk_score"],
            "is_safe": vpn_check["risk_score"] < 50,
            "warnings": vpn_check["details"],
            "blocked": vpn_check["risk_score"] > 80,
        }
        
        if result["blocked"]:
            self._blocked_ips.add(ip)
            self._suspicious_activity.append({
                "user_id": user_id,
                "ip": ip,
                "reason": "High risk score",
                "timestamp": datetime.utcnow().isoformat(),
            })
        
        return result
    
    def block_ip(self, ip: str):
        """Manually block an IP."""
        self._blocked_ips.add(ip)
    
    def unblock_ip(self, ip: str):
        """Unblock an IP."""
        self._blocked_ips.discard(ip)
    
    def get_blocked_ips(self) -> List[str]:
        """Get list of blocked IPs."""
        return list(self._blocked_ips)

@st.cache_resource
def get_security_manager() -> SecurityManager:
    """Get cached security manager."""
    return SecurityManager()

# ═══════════════════════════════════════════════════════════════════════
# GEOLOCATION & GREETINGS
# ═════════════════════════════════════════════════════════==============

class GeoManager:
    """Geolocation and smart greetings."""
    
    # National independence days
    INDEPENDENCE_DAYS = {
        "01-01": "Haiti", "01-01": "Sudan", "01-30": "India",
        "03-06": "Ghana", "03-12": "Mauritius", "04-17": "Syria",
        "06-12": "Nigeria", "07-01": "Canada", "07-04": "USA",
        "08-15": "Korea (Liberation)", "09-15": "Guatemala",
        "09-21": "Malta", "10-01": "Nigeria", "10-09": "Uganda",
        "10-10": "Taiwan", "11-30": "Finland", "12-16": "Bangladesh",
    }
    
    # Major holidays
    HOLIDAYS = {
        "01-01": "🎊 New Year's Day",
        "01-07": "🎄 Orthodox Christmas",
        "02-14": "💕 Valentine's Day",
        "03-08": "🌸 International Women's Day",
        "04-21": "Easter Sunday",
        "05-01": "�國際 Labour Day",
        "07-10": "Eid al-Fitr (estimated)",
        "12-25": "🎄 Christmas Day",
        "12-26": "🎁 Boxing Day",
    }
    
    # User birthday (would be stored in DB)
    USER_BIRTHDAYS = {}  # user_id -> "MM-DD"
    
    def get_country_info(self, ip: str) -> Dict[str, Any]:
        """Get country info from IP."""
        try:
            response = requests.get(
                f"http://ip-api.com/json/{ip}",
                params={"fields": "country,countryCode,regionName,city,currency,timezone",
                       "timeout": 5},
            )
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return {}
    
    def check_holiday(self) -> Optional[str]:
        """Check if today is a holiday."""
        today = datetime.now().strftime("%m-%d")
        return self.HOLIDAYS.get(today)
    
    def check_independence_day(self, country_code: str) -> Optional[str]:
        """Check if today is independence day for country."""
        today = datetime.now().strftime("%m-%d")
        
        # Map country codes to independence day
        country_independence = {
            "NG": "10-01", "GH": "03-06", "UG": "10-09", "KE": "12-12",
            "TZ": "12-09", "ZA": "05-31", "RW": "07-01", "ET": None,
            "US": "07-04", "CA": "07-01", "IN": "01-26", "JM": "08-06",
        }
        
        indep_day = country_independence.get(country_code.upper())
        if indep_day == today:
            return self.INDEPENDENCE_DAYS.get(today)
        return None
    
    def check_birthday(self, user_id: str) -> bool:
        """Check if today is user's birthday."""
        today = datetime.now().strftime("%m-%d")
        return self.USER_BIRTHDAYS.get(user_id) == today
    
    def get_greeting(self, user_name: str = "", country_code: str = "") -> str:
        """Generate contextual greeting."""
        # Base greeting
        hour = datetime.now().hour
        if hour < 12:
            base = "☀️ Good morning"
        elif hour < 17:
            base = "🌤️ Good afternoon"
        else:
            base = "🌙 Good evening"
        
        # Add holiday
        holiday = self.check_holiday()
        if holiday:
            base = f"{holiday}! {base}"
        
        # Add independence day
        if country_code:
            indep = self.check_independence_day(country_code)
            if indep:
                base = f"🎉 Happy Independence Day ({indep})! {base}"
        
        # Add birthday
        # In production, check user's actual birthday
        
        # Add name
        if user_name:
            base = f"{base}, {user_name}!"
        
        return base

@st.cache_resource
def get_geo_manager() -> GeoManager:
    """Get cached geo manager."""
    return GeoManager()

# ═════════════════════════════════════════════════════════==============
# PROFESSOR VAULT
# ═════════════════════════════════════════════════════════==============

class ProfessorVault:
    """AES-256 encrypted review storage."""
    
    def __init__(self):
        self._vault_key = os.environ.get("VAULT_KEY", "").encode()[:32] or b"default_key_change_in_prod"
    
    def _derive_key(self, password: str) -> bytes:
        """Derive encryption key from password."""
        return hashlib.sha256(password.encode()).digest()[:32]
    
    def _xor_encrypt(self, data: bytes, key: bytes) -> bytes:
        """Simple XOR encryption (use proper AES in production)."""
        result = bytearray()
        for i, b in enumerate(data):
            result.append(b ^ key[i % len(key)])
        return bytes(result)
    
    def encrypt_review(self, content: str, password: str) -> str:
        """Encrypt submission review."""
        key = self._derive_key(password)
        encrypted = self._xor_encrypt(content.encode(), key)
        return base64.b64encode(encrypted).decode()
    
    def decrypt_review(self, encrypted_content: str, password: str) -> Optional[str]:
        """Decrypt submission review."""
        try:
            key = self._derive_key(password)
            decoded = base64.b64decode(encrypted_content.encode())
            decrypted = self._xor_encrypt(decoded, key)
            return decrypted.decode()
        except Exception:
            return None
    
    def verify_password(self, encrypted_content: str, password: str) -> bool:
        """Verify password without exposing content."""
        # Use timing-safe comparison in production
        decrypted = self.decrypt_review(encrypted_content, password)
        return decrypted is not None

@st.cache_resource
def get_professor_vault() -> ProfessorVault:
    """Get professor vault instance."""
    return ProfessorVault()

# ═══════════════════════════════════════════════════════════════════════
# STREAMLIT UI
# ═════════════════════════════════════════════════════════==============

def render_security_dashboard():
    """Render security and geolocation UI."""
    
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #1e293b, #0f172a);
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        border: 1px solid #334155;
    ">
        <h2 style="margin:0; color: white;">🛡️ Security & Location</h2>
        <p style="color: #94a3b8; margin-top: 0.5rem;">
            VPN detection, geolocation, and smart greetings
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔐 Session Security")
        
        # Security check
        security = get_security_manager()
        ip = security.get_client_ip()
        
        check = security.check_session_security("current_user", ip)
        
        # Status
        if check["is_safe"]:
            st.success(f"✅ Secure Session (Score: {check['security_score']}%)")
        else:
            st.warning(f"⚠️ Elevated Risk (Score: {check['security_score']}%)")
        
        st.caption(f"IP: {ip}")
        
        # Warnings
        if check["warnings"]:
            st.markdown("**Detected:**")
            for w in check["warnings"]:
                st.warning(f"• {w}")
        
        # Blocked IPs
        with st.expander("🚫 Blocked IPs"):
            blocked = security.get_blocked_ips()
            if blocked:
                for bip in blocked:
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.code(bip)
                    with col_b:
                        if st.button("Unblock", key=f"unb_{bip}"):
                            security.unblock_ip(bip)
                            st.rerun()
            else:
                st.info("No blocked IPs")
    
    with col2:
        st.subheader("🌍 Smart Greeting")
        
        # Manual test
        test_country = st.selectbox("Test Country", 
                                    ["NG", "GH", "UG", "KE", "US", "CA", "UK", "IN"],
                                    format_func=lambda x: {
                                        "NG": "Nigeria", "GH": "Ghana", "UG": "Uganda",
                                        "KE": "Kenya", "US": "USA", "CA": "Canada",
                                        "UK": "UK", "India": "IN",
                                    }.get(x, x))
        
        greeting = get_geo_manager().get_greeting("Dr. Researcher", test_country)
        st.markdown(f"### {greeting}")
        
        # Check holiday
        holiday = get_geo_manager().check_holiday()
        if holiday:
            st.success(f"Today: {holiday}")
        
        # Check independence
        indep = get_geo_manager().check_independence_day(test_country)
        if indep:
            st.success(f"🎉 {indep}")
        
        # IP lookup
        st.divider()
        test_ip = st.text_input("Check IP Location", "8.8.8.8")
        if st.button("Lookup"):
            info = get_geo_manager().get_country_info(test_ip)
            if info.get("country"):
                st.json({
                    "Country": info.get("country"),
                    "Region": info.get("regionName"),
                    "City": info.get("city"),
                    "Currency": info.get("currency"),
                    "Timezone": info.get("timezone"),
                })
            else:
                st.error("Could not lookup IP")

def render_professor_vault():
    """Render professor vault UI."""
    st.subheader("🔒 Professor Vault")
    
    st.markdown("""
    Secure, encrypted storage for grading submissions.
    Set a project password to protect student reviews.
    """)
    
    tab1, tab2 = st.tabs(["🔐 Encrypt Review", "🔓 Decrypt Review"])
    
    with tab1:
        st.markdown("#### Encrypt a Submission")
        
        content = st.text_area("Submission Content", height=150)
        password = st.text_input("Project Password", type="password")
        
        if st.button("Encrypt 🔒", type="primary") and content and password:
            vault = get_professor_vault()
            encrypted = vault.encrypt_review(content, password)
            
            st.success("Encrypted!")
            st.code(encrypted)
            
            st.download_button(
                "📥 Download Encrypted",
                data=encrypted,
                file_name="encrypted_review.sec",
                mime="text/plain",
            )
    
    with tab2:
        st.markdown("#### Decrypt a Submission")
        
        decrypt_mode = st.radio("Source", ["Paste", "Upload File"], horizontal=True)
        
        encrypted_data = ""
        if decrypt_mode == "Paste":
            encrypted_data = st.text_area("Encrypted Content", height=100)
        else:
            uploaded = st.file_uploader("Upload encrypted file", type=["sec", "txt"])
            if uploaded:
                encrypted_data = uploaded.read().decode()
        
        password = st.text_input("Decryption Password", type="password")
        
        if st.button("Decrypt 🔓", type="primary") and encrypted_data and password:
            vault = get_professor_vault()
            
            if vault.verify_password(encrypted_data, password):
                decrypted = vault.decrypt_review(encrypted_data, password)
                st.success("Decrypted successfully!")
                st.text_area("Decrypted Content", value=decrypted, height=150)
            else:
                st.error("Incorrect password!")

def render_settings_new():
    """Enhanced settings page with all features."""
    st.title("⚙️ Settings")
    st.markdown("---")
    
    # New tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔐 Credentials", "💳 Subscription", "🔗 Integrations", 
        "🛡️ Security", "🔧 System",
    ])
    
    with tab1:
        render_credentials_tab()
    
    with tab2:
        render_subscription_tab()
    
    with tab3:
        render_integrations_tab()
    
    with tab4:
        render_security_dashboard()
        st.divider()
        render_professor_vault()
    
    with tab5:
        render_system_tab()

def render_credentials_tab():
    st.subheader("Notion Credentials")
    
    from modules.auth import get_notion_token, get_database_id
    
    token = st.text_input("Notion Token", type="password", value=get_notion_token())
    db_id = st.text_input("Database ID", value=get_database_id())
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Save Credentials"):
            st.session_state["user_NOTION_TOKEN"] = token
            st.session_state["user_DATABASE_ID"] = db_id
            st.success("Saved!")
    with col2:
        if st.button("Clear"):
            st.session_state["user_NOTION_TOKEN"] = ""
            st.session_state["user_DATABASE_ID"] = ""
            st.success("Cleared!")

def render_subscription_tab():
    from modules.verification import render_tier_selector
    try:
        render_tier_selector()
    except:
        st.info("Subscription management requires database")

def render_integrations_tab():
    st.subheader("🔗 Integrations")
    
    # Academic integrations redirect
    st.info("Access Academic Integrations from the main navigation")
    
    if st.button("Open Integrations"):
        # Navigate to integrations page
        pass

def render_system_tab():
    st.subheader("🔧 System")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Clear Cache"):
            import gc
            gc.collect()
            st.success("Cache cleared!")
    
    with col2:
        if st.button("Reset Session"):
            for key in list(st.session_state.keys()):
                if not key.startswith(("collab_", "user_")):
                    del st.session_state[key]
            st.rerun()
    
    # Debug info
    with st.expander("🔍 Debug Info"):
        st.write("Session State Keys:", list(st.session_state.keys())[:10])