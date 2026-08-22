import base64
import datetime
import hashlib
import hmac
import io
import os
import secrets
import sqlite3
import urllib.parse
import zipfile
import pandas as pd
import requests
import streamlit as st
import extra_streamlit_components as stx

# --- PAGE CONFIGURATION (Must be the first Streamlit command) ---
st.set_page_config(
    page_title="Chrishem Science Hub - Sovereign Enterprise Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Shared Subscription & Billing Modules
from modules import subscription
from modules import billing_stripe

PBKDF2_ITERATIONS = 260_000


def get_cookie_manager():
    return stx.CookieManager()


cookie_manager = get_cookie_manager()


# --- DATABASE INITIALIZATION ---
def init_sovereign_db():
    conn = sqlite3.connect("sovereign_apex_engine.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS auth_users (
            email TEXT PRIMARY KEY,
            name TEXT,
            password_hash TEXT,
            role TEXT,
            avatar_blob BLOB
        )
    """)
    for migration in (
        "ALTER TABLE auth_users ADD COLUMN avatar_blob BLOB",
        "ALTER TABLE auth_users ADD COLUMN salt TEXT",
        "ALTER TABLE auth_users ADD COLUMN auth_provider TEXT DEFAULT 'password'",
        "ALTER TABLE auth_users ADD COLUMN provider_id TEXT",
    ):
        try:
            cursor.execute(migration)
        except sqlite3.OperationalError:
            pass  # Column already exists.

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            email TEXT PRIMARY KEY,
            plan TEXT,
            trial_started TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS live_chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            timestamp TEXT,
            prompt TEXT,
            response TEXT
        )
    """)
    conn.commit()
    return conn


db_conn = init_sovereign_db()


# --- PASSWORD HASHING (PBKDF2-HMAC-SHA256) ---
def _hash_password(password: str, salt_hex: str = None):
    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return dk.hex(), salt.hex()


def _verify_password(password: str, stored_hash_hex: str, salt_hex: str) -> bool:
    computed_hash, _ = _hash_password(password, salt_hex)
    return hmac.compare_digest(computed_hash, stored_hash_hex)


# --- BOOTSTRAP & DESIGNATED ADMIN SYNC ---
def ensure_bootstrap_admin():
    cursor = db_conn.cursor()
    bootstrap_email = os.environ.get("SOVEREIGN_ADMIN_EMAIL")
    
    if cursor.execute("SELECT COUNT(*) FROM auth_users").fetchone()[0] > 0:
        if bootstrap_email:
            email_norm = bootstrap_email.lower().strip()
            cursor.execute("UPDATE auth_users SET name = 'CHRISHEM' WHERE email = ? AND role = 'admin'", (email_norm,))
            db_conn.commit()
        return

    bootstrap_password = os.environ.get("SOVEREIGN_ADMIN_PASSWORD")
    if bootstrap_email and bootstrap_password:
        pwd_hash, salt = _hash_password(bootstrap_password)
        email_norm = bootstrap_email.lower().strip()
        cursor.execute(
            "INSERT INTO auth_users (email, name, password_hash, salt, role) VALUES (?,?,?,?,?)",
            (email_norm, "CHRISHEM", pwd_hash, salt, "admin"),
        )
        db_conn.commit()
        subscription.admin_override_plan("system:bootstrap", email_norm, "pro", "comp")


ensure_bootstrap_admin()


def sync_designated_admin():
    designated_email = os.environ.get("SOVEREIGN_ADMIN_EMAIL")
    if not designated_email:
        try:
            designated_email = st.secrets.get("SOVEREIGN_ADMIN_EMAIL")
        except Exception:
            designated_email = None
    if not designated_email:
        return

    designated_email = designated_email.lower().strip()
    cursor = db_conn.cursor()
    cursor.execute("SELECT role FROM auth_users WHERE email = ?", (designated_email,))
    row = cursor.fetchone()
    if row and row[0] != "admin":
        cursor.execute("UPDATE auth_users SET role = 'admin', name = 'CHRISHEM' WHERE email = ?", (designated_email,))
        db_conn.commit()


sync_designated_admin()


# --- AUTHENTICATION STORE ---
class AuthStore:
    def verify_login(self, email, password):
        cursor = db_conn.cursor()
        cursor.execute(
            "SELECT email, name, role, password_hash, salt FROM auth_users WHERE email = ?",
            (email.lower().strip(),),
        )
        row = cursor.fetchone()
        if not row:
            return None
        db_email, name, role, stored_hash, salt = row

        if not stored_hash:
            return {"email": db_email, "name": name, "role": role, "oauth_only": True}

        if salt:
            if _verify_password(password, stored_hash, salt):
                return {"email": db_email, "name": name, "role": role}
            return None

        legacy_hash = hashlib.sha256(password.encode()).hexdigest()
        if legacy_hash == stored_hash:
            new_hash, new_salt = _hash_password(password)
            cursor.execute("UPDATE auth_users SET password_hash = ?, salt = ? WHERE email = ?", (new_hash, new_salt, db_email))
            db_conn.commit()
            return {"email": db_email, "name": name, "role": role}
        return None

    def get_user_by_email(self, email):
        cursor = db_conn.cursor()
        cursor.execute("SELECT email, name, role FROM auth_users WHERE email = ?", (email,))
        row = cursor.fetchone()
        if row:
            return {"email": row[0], "name": row[1], "role": row[2]}
        return None

    def create_user(self, email, name, password, role="user"):
        cursor = db_conn.cursor()
        email_norm = email.lower().strip()
        cursor.execute("SELECT email FROM auth_users WHERE email = ?", (email_norm,))
        if cursor.fetchone():
            return {"ok": False, "error": "Email already registered."}

        pwd_hash, salt = _hash_password(password)
        cursor.execute(
            "INSERT INTO auth_users (email, name, password_hash, salt, role) VALUES (?, ?, ?, ?, ?)",
            (email_norm, name, pwd_hash, salt, role),
        )
        db_conn.commit()
        subscription.ensure_trial_started(email_norm)
        return {"ok": True}

    def get_or_create_oauth_user(self, email, name, provider, provider_id):
        cursor = db_conn.cursor()
        email_norm = email.lower().strip()
        cursor.execute("SELECT email, name, role FROM auth_users WHERE email = ?", (email_norm,))
        row = cursor.fetchone()
        if row:
            db_email, db_name, role = row
            cursor.execute(
                "UPDATE auth_users SET auth_provider = ?, provider_id = ? WHERE email = ?",
                (provider, provider_id, db_email),
            )
            db_conn.commit()
            return {"email": db_email, "name": db_name or name, "role": role}

        cursor.execute(
            "INSERT INTO auth_users (email, name, password_hash, salt, role, auth_provider, provider_id) "
            "VALUES (?, ?, NULL, NULL, ?, ?, ?)",
            (email_norm, name, "user", provider, provider_id),
        )
        db_conn.commit()
        subscription.ensure_trial_started(email_norm)
        return {"email": email_norm, "name": name, "role": "user"}


auth_store = AuthStore()


# --- OAUTH INTEGRATION ---
OAUTH_PROVIDERS = {
    "google": {
        "label": "Google",
        "icon": "🔴",
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo",
        "scope": "openid email profile",
        "client_id_env": "GOOGLE_CLIENT_ID",
        "client_secret_env": "GOOGLE_CLIENT_SECRET",
    },
    "github": {
        "label": "GitHub",
        "icon": "⚫",
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "scope": "read:user user:email",
        "client_id_env": "GITHUB_CLIENT_ID",
        "client_secret_env": "GITHUB_CLIENT_SECRET",
    },
}


def _oauth_config_value(name):
    val = os.environ.get(name)
    if val:
        return val
    try:
        return st.secrets.get(name)
    except Exception:
        return None


def get_configured_providers():
    configured = {}
    for key, cfg in OAUTH_PROVIDERS.items():
        cid = _oauth_config_value(cfg["client_id_env"])
        secret = _oauth_config_value(cfg["client_secret_env"])
        if cid and secret:
            configured[key] = {**cfg, "client_id": cid, "client_secret": secret}
    return configured


def get_redirect_uri():
    return _oauth_config_value("OAUTH_REDIRECT_URI") or ""


def build_authorize_url(provider_key, cfg):
    token = secrets.token_urlsafe(24)
    pending = st.session_state.setdefault("oauth_pending", {})
    pending[token] = provider_key

    params = {
        "client_id": cfg["client_id"],
        "redirect_uri": get_redirect_uri(),
        "scope": cfg["scope"],
        "state": token,
        "response_type": "code",
    }
    if provider_key == "google":
        params["access_type"] = "online"
        params["prompt"] = "select_account"
    return f"{cfg['authorize_url']}?{urllib.parse.urlencode(params)}"


def exchange_code_for_token(cfg, code):
    resp = requests.post(
        cfg["token_url"],
        data={
            "client_id": cfg["client_id"],
            "client_secret": cfg["client_secret"],
            "code": code,
            "redirect_uri": get_redirect_uri(),
            "grant_type": "authorization_code",
        },
        headers={"Accept": "application/json"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("access_token")


def fetch_oauth_profile(provider_key, cfg, access_token):
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    resp = requests.get(cfg["userinfo_url"], headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if provider_key == "google":
        return {
            "email": data.get("email"),
            "name": data.get("name") or data.get("email", "").split("@")[0],
            "provider_id": data.get("sub"),
        }

    if provider_key == "github":
        email = data.get("email")
        if not email:
            email_resp = requests.get("https://api.github.com/user/emails", headers=headers, timeout=10)
            if email_resp.ok:
                for entry in email_resp.json():
                    if entry.get("primary") and entry.get("verified"):
                        email = entry.get("email")
                        break
        return {
            "email": email,
            "name": data.get("name") or data.get("login"),
            "provider_id": str(data.get("id")),
        }

    return {"email": None, "name": None, "provider_id": None}


def handle_oauth_callback():
    query = st.query_params
    code = query.get("code")
    returned_state = query.get("state")
    if not code or not returned_state:
        return False

    pending = st.session_state.get("oauth_pending", {})
    provider_key = pending.get(returned_state)
    if not provider_key or provider_key not in OAUTH_PROVIDERS:
        st.query_params.clear()
        st.error("OAuth sign-in failed a security check (unrecognized state). Please try again.")
        return False

    configured = get_configured_providers()
    cfg = configured.get(provider_key)
    if not cfg:
        st.query_params.clear()
        st.error(f"{provider_key.title()} sign-in is not configured on this deployment.")
        return False

    try:
        access_token = exchange_code_for_token(cfg, code)
        if not access_token:
            raise ValueError("No access token returned.")
        profile = fetch_oauth_profile(provider_key, cfg, access_token)
        if not profile.get("email"):
            raise ValueError("The provider didn't return a usable email address.")
    except Exception as e:
        st.query_params.clear()
        st.error(f"{provider_key.title()} sign-in failed: {e}")
        return False

    user = auth_store.get_or_create_oauth_user(
        profile["email"], profile["name"] or profile["email"], provider_key, profile["provider_id"]
    )
    st.session_state.portal_unlocked = True
    st.session_state.user_identity = {
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
        "is_admin": user["role"] == "admin",
    }
    cookie_manager.set("chrishem_user_email", user["email"], expires_at=datetime.datetime.now() + datetime.timedelta(days=90))
    subscription.ensure_trial_started(user["email"])
    st.session_state.pop("oauth_pending", None)
    st.query_params.clear()
    st.rerun()


def render_oauth_buttons():
    configured = get_configured_providers()
    if not configured:
        return
    if not get_redirect_uri():
        st.caption("Social sign-in credentials set, but `OAUTH_REDIRECT_URI` is missing.")
        return

    for key, cfg in configured.items():
        url = build_authorize_url(key, cfg)
        st.link_button(f"{cfg['icon']} Continue with {cfg['label']}", url, use_container_width=True)
    st.markdown("<div style='text-align:center; color:#6B7280; font-size:0.8rem; margin: 10px 0;'>— or use email & password —</div>", unsafe_allow_html=True)


def handle_checkout_return():
    qp = st.query_params
    if qp.get("checkout") == "success" and qp.get("session_id"):
        result = billing_stripe.verify_checkout_session(qp["session_id"])
        st.query_params.clear()
        if result:
            st.session_state["_billing_toast"] = f"✅ Upgraded to **{result['plan'].title()}** — welcome aboard."
        else:
            st.session_state["_billing_toast"] = "⚠️ Could not confirm payment yet. Try resyncing billing status."
    elif qp.get("checkout") == "cancelled":
        st.query_params.clear()
        st.session_state["_billing_toast"] = "ℹ️ Checkout cancelled — no charge was made."


def is_admin():
    identity = st.session_state.get("user_identity", {})
    return identity.get("role") == "admin"


def get_user_avatar_base64(email):
    cursor = db_conn.cursor()
    cursor.execute("SELECT avatar_blob FROM auth_users WHERE email = ?", (email,))
    row = cursor.fetchone()
    if row and row[0]:
        return base64.b64encode(row[0]).decode("utf-8")
    img_path = "chrishem.png"
    if os.path.exists(img_path):
        with open(img_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode("utf-8")
    return None


# --- STARTER CONFIG BUNDLES ---
def create_starter_bundle(platform_name):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr(
            "README.md",
            f"# Chrishem Science Hub — Starter Notes ({platform_name})\n\n"
            "This is a minimal configuration reference bundle. To run the platform, deploy `streamlit run app.py`.",
        )
        zip_file.writestr("config.toml", "[server]\nheadless = true\nenableCORS = false")
    return zip_buffer.getvalue()


starter_win = create_starter_bundle("Windows")
starter_linux = create_starter_bundle("Linux")
starter_mac = create_starter_bundle("macOS")
starter_pwa = create_starter_bundle("Mobile / PWA")

# --- CUSTOM CSS & THEME OVERRIDES ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
        color: #EDEFF2 !important;
    }

    .stApp {
        background: radial-gradient(circle at 15% 20%, #0d1326 0%, #04060a 85%);
        background-attachment: fixed;
    }

    .portal-hero-card {
        background: rgba(17, 24, 39, 0.82);
        backdrop-filter: blur(24px);
        -webkit-backdrop-filter: blur(24px);
        border: 1px solid rgba(56, 189, 248, 0.35);
        border-radius: 28px;
        padding: 35px 30px;
        box-shadow: 0 30px 60px rgba(0, 0, 0, 0.9), 0 0 50px rgba(56, 189, 248, 0.15);
        max-width: 860px;
        margin: 0 auto;
    }

    .portal-title {
        font-size: 2.3rem;
        font-weight: 800;
        background: linear-gradient(135deg, #4FB8A6 0%, #8B93A8 50%, #F472B6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        letter-spacing: -0.02em;
        margin-bottom: 6px;
    }

    .portal-subtitle {
        font-size: 0.95rem;
        color: #6B7280 !important;
        font-weight: 600;
        text-align: center;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 18px;
    }

    .profile-glow-wrap {
        display: flex;
        justify-content: center;
        margin-bottom: 15px;
    }

    .profile-avatar {
        width: 90px;
        height: 90px;
        border-radius: 50%;
        object-fit: cover;
        border: 3px solid #4FB8A6;
        box-shadow: 0 0 30px rgba(56, 189, 248, 0.6);
    }

    .glass-hr {
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(56, 189, 248, 0.35), transparent);
        margin: 1.5rem 0;
    }

    .workspace-metric {
        background: linear-gradient(145deg, rgba(30, 41, 59, 0.7), rgba(15, 23, 42, 0.9));
        border: 1px solid rgba(56, 189, 248, 0.3);
        border-radius: 16px;
        padding: 1.25rem;
        text-align: center;
        box-shadow: 0 8px 30px rgba(0,0,0,0.4);
    }
    .workspace-metric .metric-value {
        font-size: 1.8rem;
        font-weight: 800;
        background: linear-gradient(90deg, #4FB8A6, #8B93A8, #F472B6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .workspace-metric .metric-label {
        font-size: 0.75rem;
        color: #6B7280 !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-top: 0.3rem;
        font-weight: 700;
    }

    [data-testid="stSidebar"] {
        background-color: #050810 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
    }
    </style>
""", unsafe_allow_html=True)

try:
    from modules.user_preferences import render_readability_fix, render_accent_color_css
    render_readability_fix()
    render_accent_color_css()
except ImportError:
    pass

# --- SESSION STATE & COOKIE RESTORATION ---
if "portal_unlocked" not in st.session_state:
    st.session_state.portal_unlocked = False
if "user_identity" not in st.session_state:
    st.session_state.user_identity = {}

handle_oauth_callback()

if not st.session_state.portal_unlocked:
    saved_email = cookie_manager.get(cookie="chrishem_user_email")
    if saved_email:
        user_record = auth_store.get_user_by_email(saved_email)
        if user_record:
            st.session_state.portal_unlocked = True
            st.session_state.user_identity = {
                "email": user_record["email"],
                "name": user_record["name"],
                "role": user_record["role"],
                "is_admin": user_record["role"] == "admin",
            }
            subscription.ensure_trial_started(user_record["email"])

if st.session_state.portal_unlocked:
    handle_checkout_return()

# --- PORTAL GATEWAY SCREEN (LOCKED STATE) ---
if not st.session_state.portal_unlocked:
    st.markdown("<style>[data-testid=\"stSidebar\"] {display: none;}</style>", unsafe_allow_html=True)
    st.markdown("<div style='height: 2vh;'></div>", unsafe_allow_html=True)

    gateway_avatar_b64 = get_user_avatar_base64("")
    avatar_html = f'<img src="data:image/png;base64,{gateway_avatar_b64}" class="profile-avatar">' if gateway_avatar_b64 else '<div style="font-size: 55px; text-align:center;">⚡</div>'

    st.markdown(f"""
    <div class="portal-hero-card">
        <div class="profile-glow-wrap">{avatar_html}</div>
        <div class="portal-title">CHRISHEM SCIENCE HUB & ECOSYSTEM</div>
        <div class="portal-subtitle">Sovereign Enterprise Engine • Secure Multi-Platform Gateway</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    no_admin_yet = db_conn.execute("SELECT COUNT(*) FROM auth_users WHERE role = 'admin'").fetchone()[0] == 0
    if no_admin_yet:
        st.warning(
            "⚙️ **First-time setup:** No admin account exists yet. Set `SOVEREIGN_ADMIN_EMAIL` and "
            "`SOVEREIGN_ADMIN_PASSWORD` in environment variables and restart the app."
        )

    _, portal_col, _ = st.columns([0.4, 3.2, 0.4])
    with portal_col:
        tab_signin, tab_signup, tab_downloads = st.tabs(["🔐 Secure Sign In", "📝 Register Account", "📱 Ecosystem Downloads"])

        with tab_signin:
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            render_oauth_buttons()
            si_email = st.text_input("Portal Email Address", key="si_email_input", placeholder="name@domain.com")
            si_password = st.text_input("Secure Password", type="password", key="si_password_input", placeholder="••••••••")
            remember_me = st.checkbox("Remember Me on this Device", value=True, key="remember_me_checkbox")

            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            if st.button("🚀 Unlock Portal Workspace", use_container_width=True):
                user = auth_store.verify_login(si_email, si_password)
                if user is None:
                    st.error("Incorrect email or password.")
                elif user.get("oauth_only"):
                    st.warning("This account was created via social sign-in. Use social login buttons above.")
                else:
                    st.session_state.portal_unlocked = True
                    st.session_state.user_identity = {
                        "email": user["email"],
                        "name": user["name"],
                        "role": user["role"],
                        "is_admin": user["role"] == "admin",
                    }
                    if remember_me:
                        cookie_manager.set("chrishem_user_email", user["email"], expires_at=datetime.datetime.now() + datetime.timedelta(days=90))

                    subscription.ensure_trial_started(user["email"])
                    st.rerun()

        with tab_signup:
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            su_name = st.text_input("Preferred Full Name", key="su_name_input", placeholder="Analyst Name")
            su_email = st.text_input("Email Address", key="su_email_input", placeholder="name@domain.com")
            su_password = st.text_input("Choose Password", type="password", key="su_password_input", placeholder="At least 6 characters")
            su_password2 = st.text_input("Confirm Password", type="password", key="su_password2_input", placeholder="Re-enter password")

            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            if st.button("✨ Create Sovereign Account", use_container_width=True):
                if not su_email or not su_password:
                    st.error("Email and password are required.")
                elif su_password != su_password2:
                    st.error("Passwords don't match.")
                elif len(su_password) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    result = auth_store.create_user(su_email, su_name or "Analyst", su_password, role="user")
                    if not result["ok"]:
                        st.error(result["error"])
                    else:
                        st.success("Account created successfully! Switch to 'Secure Sign In' above.")

        with tab_downloads:
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            st.markdown("### 🌍 Starter Configuration Bundles")
            d_col1, d_col2 = st.columns(2)
            with d_col1:
                st.download_button("📥 Download Windows Bundle", data=starter_win, file_name="chrishem_hub_windows_starter.zip", mime="application/zip", use_container_width=True)
                st.download_button("📥 Download Linux Bundle", data=starter_linux, file_name="chrishem_hub_linux_starter.zip", mime="application/zip", use_container_width=True)
            with d_col2:
                st.download_button("📥 Download macOS Bundle", data=starter_mac, file_name="chrishem_hub_macos_starter.zip", mime="application/zip", use_container_width=True)
                st.download_button("📥 Download Mobile Bundle", data=starter_pwa, file_name="chrishem_hub_mobile_starter.zip", mime="application/zip", use_container_width=True)

# --- UNLOCKED WORKSPACE DASHBOARD & ROUTING ---
else:
    identity = st.session_state.get("user_identity", {})
    current_user_email = identity.get("email", "")

    sidebar_avatar_b64 = get_user_avatar_base64(current_user_email)
    if sidebar_avatar_b64:
        st.sidebar.markdown(f'<div style="text-align:center; margin-bottom:10px;"><img src="data:image/png;base64,{sidebar_avatar_b64}" style="width:65px; height:65px; border-radius:50%; object-fit:cover; border:2px solid #4FB8A6;"></div>', unsafe_allow_html=True)

    st.sidebar.title("CHRISHEM APEX")
    st.sidebar.success(f"🔓 Operator: {identity.get('name')}")
    st.sidebar.markdown(f"**Email:** `{current_user_email}`")
    st.sidebar.markdown(f"**Privilege:** `{'👑 Admin' if is_admin() else 'Standard User'}`")

    st.sidebar.markdown('<div class="glass-hr"></div>', unsafe_allow_html=True)

    if st.sidebar.button("🔒 Lock Portal & Sign Out", use_container_width=True):
        cookie_manager.delete("chrishem_user_email")
        st.session_state.portal_unlocked = False
        st.rerun()

    st.sidebar.markdown('<div class="glass-hr"></div>', unsafe_allow_html=True)
    st.sidebar.markdown("### 📁 Navigation Matrix")

    # Primary Sidebar Navigation
    menu_selection = st.sidebar.radio("Select Workspace", [
        "⚡ Apex Dashboard",
        "💳 Billing & Subscription",
        "🧠 Brain FM Focus Studio",
        "🗄️ Bio-Research Notion Vault",
        "📝 Query Log",
        "🔬 Bioinformatics Studio",
        "⚙️ Profile Settings",
        "🛡️ Admin Security & User Controls"
    ])

    toast_msg = st.session_state.pop("_billing_toast", None)
    if toast_msg:
        st.toast(toast_msg) if hasattr(st, "toast") else st.info(toast_msg)

    # --- WORKSPACE MODULE ROUTING ---
    if menu_selection == "🧠 Brain FM Focus Studio":
        from modules.brain_fm import render_brain_fm_studio
        render_brain_fm_studio()

    elif menu_selection == "🗄️ Bio-Research Notion Vault":
        from modules.notion_gating import render_notion_template_vault
        render_notion_template_vault()

    elif menu_selection == "💳 Billing & Subscription":
        from modules.billing_ui import render_notion_style_billing
        user_identity = st.session_state.get("user_identity", {})
        render_notion_style_billing(user_identity.get("email"), user_identity.get("name"))

    elif menu_selection == "⚡ Apex Dashboard":
        st.title("⚡ Chrishem Sovereign Apex Hub")
        st.markdown("---")

        status = subscription.get_status(current_user_email)
        plan_label = "Admin (full access)" if is_admin() else status["effective_plan"].title()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown('<div class="workspace-metric"><div class="metric-value">Active</div><div class="metric-label">Gateway Status</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="workspace-metric"><div class="metric-value">{identity.get("name")}</div><div class="metric-label">Active Operator</div></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="workspace-metric"><div class="metric-value">{"Admin" if is_admin() else "Standard"}</div><div class="metric-label">Access Ring</div></div>', unsafe_allow_html=True)

        st.markdown('<div class="glass-hr"></div>', unsafe_allow_html=True)
        st.markdown("### 🌟 Welcome to the Core Ecosystem Workspace")
        st.write("Use the navigation panel on the left to switch between active modules and focus studios.")

        c_a, c_b = st.columns(2)
        with c_a:
            st.info(f"**Account Role:** {'Administrator' if is_admin() else 'Standard User'}")
        with c_b:
            if status["status"] == "trialing" and status["days_left_in_trial"] is not None:
                st.success(f"**Trial:** {plan_label} access — {status['days_left_in_trial']} day(s) left.")
            else:
                st.success(f"**Subscription Plan:** `{plan_label}` ({status['status']}) for `{current_user_email}`.")

    elif menu_selection == "📝 Query Log":
        st.title("📝 Session Query Log")
        st.caption("Records your queries for workspace references.")

        cursor = db_conn.cursor()
        cursor.execute("SELECT prompt, response, timestamp FROM live_chat_history WHERE username = ? ORDER BY id ASC", (identity.get("name"),))
        chat_rows = cursor.fetchall()
        for p, r, ts in chat_rows:
            st.markdown(f"""
            <div style="background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(56, 189, 248, 0.2); border-radius: 10px; padding: 0.85rem; margin-bottom: 0.75rem;">
                <b style="color: #4FB8A6;">[{ts[:19]}]:</b> {p}<br><br>
                <b style="color: #8B93A8;">Note:</b> {r}
            </div>
            """, unsafe_allow_html=True)

        user_prompt = st.text_area("Log a query or note for later reference:", key="portal_ai_input")
        if st.button("💾 Save to Log"):
            if user_prompt.strip():
                note = "Logged for reference."
                cursor.execute("INSERT INTO live_chat_history (username, timestamp, prompt, response) VALUES (?, ?, ?, ?)",
                               (identity.get("name"), datetime.datetime.now().isoformat(), user_prompt, note))
                db_conn.commit()
                st.rerun()

    elif menu_selection == "🔬 Bioinformatics Studio":
        st.title("🧬 Genomic Sequence & GC-Content Studio")
        seq_input = st.text_area("Paste FASTA Sequence Data", placeholder="ATGCGATCGATCGATCGATCG...")
        if st.button("Run Sequence Metric Analysis"):
            if seq_input.strip():
                clean_seq = "".join(seq_input.upper().split())
                length = len(clean_seq)
                gc = ((clean_seq.count('G') + clean_seq.count('C')) / length * 100) if length > 0 else 0
                c1, c2 = st.columns(2)
                c1.metric("Total Base Pairs", f"{length} bp")
                c2.metric("GC-Content Ratio", f"{gc:.2f}%")
            else:
                st.warning("Please provide a sequence string.")

    elif menu_selection == "⚙️ Profile Settings":
        st.title("⚙️ Operator Profile & Avatar Customization")
        st.write("Upload a custom picture to personalize your account avatar.")

        active_b64 = get_user_avatar_base64(current_user_email)
        if active_b64:
            st.markdown(f'<div style="margin-bottom:15px;"><img src="data:image/png;base64,{active_b64}" style="width:110px; height:110px; border-radius:50%; object-fit:cover; border:3px solid #4FB8A6;"></div>', unsafe_allow_html=True)

        uploaded_avatar = st.file_uploader("Upload New Avatar Image (PNG, JPG, JPEG)", type=["png", "jpg", "jpeg"])

        col_up1, col_up2 = st.columns(2)
        with col_up1:
            if st.button("💾 Save Custom Avatar", use_container_width=True):
                if uploaded_avatar is not None:
                    image_bytes = uploaded_avatar.read()
                    cursor = db_conn.cursor()
                    cursor.execute("UPDATE auth_users SET avatar_blob = ? WHERE email = ?", (image_bytes, current_user_email))
                    db_conn.commit()
                    st.success("Avatar updated successfully!")
                    st.rerun()
                else:
                    st.warning("Please select an image file first.")
        with col_up2:
            if st.button("🔄 Revert to Default Picture", use_container_width=True):
                cursor = db_conn.cursor()
                cursor.execute("UPDATE auth_users SET avatar_blob = NULL WHERE email = ?", (current_user_email,))
                db_conn.commit()
                st.success("Reverted to default picture successfully!")
                st.rerun()

    elif menu_selection == "🛡️ Admin Security & User Controls":
        if not is_admin():
            st.error("🚫 Access Denied: This panel requires administrator clearance.")
        else:
            st.title("🛡️ Administrative Control Center")
            cursor = db_conn.cursor()
            cursor.execute("SELECT email, name, role FROM auth_users")
            users = cursor.fetchall()
            user_df = pd.DataFrame(users, columns=["Email", "Name", "Role"])
            st.dataframe(user_df, use_container_width=True)