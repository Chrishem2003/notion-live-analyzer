import base64
import datetime
import hashlib
import hmac
import io
import os
import secrets
import sqlite3
import time
import urllib.parse
import zipfile
import pandas as pd
import requests
import streamlit as st
import extra_streamlit_components as stx

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Chrishem Science Hub - Sovereign Enterprise Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
    for migration in ("ALTER TABLE auth_users ADD COLUMN avatar_blob BLOB",
                       "ALTER TABLE auth_users ADD COLUMN salt TEXT",
                       "ALTER TABLE auth_users ADD COLUMN auth_provider TEXT DEFAULT 'password'",
                       "ALTER TABLE auth_users ADD COLUMN provider_id TEXT"):
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


# --- PASSWORD HASHING (PBKDF2-HMAC-SHA256, salted) ---
def _hash_password(password: str, salt_hex: str = None):
    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return dk.hex(), salt.hex()


def _verify_password(password: str, stored_hash_hex: str, salt_hex: str) -> bool:
    computed_hash, _ = _hash_password(password, salt_hex)
    return hmac.compare_digest(computed_hash, stored_hash_hex)


# --- BOOTSTRAP: create the first admin ONLY on a genuinely empty database, ONLY from env vars ---
def ensure_bootstrap_admin():
    cursor = db_conn.cursor()
    if cursor.execute("SELECT COUNT(*) FROM auth_users").fetchone()[0] > 0:
        return  # Not a fresh install — database roles are the sole source of truth[cite: 18].

    bootstrap_email = os.environ.get("SOVEREIGN_ADMIN_EMAIL")
    bootstrap_password = os.environ.get("SOVEREIGN_ADMIN_PASSWORD")
    if bootstrap_email and bootstrap_password:
        pwd_hash, salt = _hash_password(bootstrap_password)
        email_norm = bootstrap_email.lower().strip()
        cursor.execute(
            "INSERT INTO auth_users (email, name, password_hash, salt, role) VALUES (?,?,?,?,?)",
            (email_norm, "Administrator", pwd_hash, salt, "admin"),
        )
        cursor.execute(
            "INSERT OR REPLACE INTO subscriptions (email, plan, trial_started) VALUES (?,?,?)",
            (email_norm, "enterprise", datetime.datetime.utcnow().isoformat()),
        )
        db_conn.commit()


ensure_bootstrap_admin()


def sync_designated_admin():
    """Promotes the account matching SOVEREIGN_ADMIN_EMAIL to admin on every startup[cite: 18]."""
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
        cursor.execute("UPDATE auth_users SET role = 'admin' WHERE email = ?", (designated_email,))
        db_conn.commit()


sync_designated_admin()


# --- AUTH & SUBSCRIPTION ---
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
        cursor.execute(
            "INSERT OR IGNORE INTO subscriptions (email, plan, trial_started) VALUES (?, ?, ?)",
            (email_norm, "trial", datetime.datetime.utcnow().isoformat()),
        )
        db_conn.commit()
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
        cursor.execute(
            "INSERT OR IGNORE INTO subscriptions (email, plan, trial_started) VALUES (?, ?, ?)",
            (email_norm, "trial", datetime.datetime.utcnow().isoformat()),
        )
        db_conn.commit()
        return {"email": email_norm, "name": name, "role": "user"}


auth_store = AuthStore()


# --- OAUTH (Google / GitHub) ---
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
        st.error("OAuth sign-in failed a security check. Please try again.")
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
        # Fallback helper if credentials aren't set up yet, to show configuration guidelines
        st.info(
            "🔴 **Google Sign-In Ready:** To display active Google/GitHub buttons, configure `GOOGLE_CLIENT_ID`, "
            "`GOOGLE_CLIENT_SECRET`, and `OAUTH_REDIRECT_URI` in your app secrets or environment variables."
        )
        return

    for key, cfg in configured.items():
        url = build_authorize_url(key, cfg)
        st.link_button(f"{cfg['icon']} Continue with {cfg['label']}", url, use_container_width=True)
    st.markdown(
        "<div style='text-align:center; color:#94A3B8; font-size:0.8rem; margin: 10px 0;'>— or use email & password —</div>",
        unsafe_allow_html=True,
    )


class SubscriptionManager:
    def ensure_trial_started(self, email):
        cursor = db_conn.cursor()
        cursor.execute("SELECT email FROM subscriptions WHERE email = ?", (email,))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO subscriptions (email, plan, trial_started) VALUES (?, ?, ?)",
                (email, "trial", datetime.datetime.utcnow().isoformat()),
            )
            db_conn.commit()

    def get_status(self, email):
        cursor = db_conn.cursor()
        cursor.execute("SELECT plan, trial_started FROM subscriptions WHERE email = ?", (email,))
        row = cursor.fetchone()
        if not row:
            return {"plan": "trial", "trial_started": None}
        return {"plan": row[0], "trial_started": row[1]}

    def upgrade_plan(self, email, plan_name):
        cursor = db_conn.cursor()
        cursor.execute("UPDATE subscriptions SET plan = ? WHERE email = ?", (plan_name, email))
        db_conn.commit()


subscription = SubscriptionManager()


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


def create_starter_bundle(platform_name):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr(
            "README.md",
            f"# Chrishem Science Hub — Starter Notes ({platform_name})\n\n"
            "Minimal configuration bundle. Run the live platform via `streamlit run app.py`.",
        )
        zip_file.writestr("config.toml", "[server]\nheadless = true\nenableCORS = false")
    return zip_buffer.getvalue()


starter_win = create_starter_bundle("Windows")
starter_linux = create_starter_bundle("Linux")
starter_mac = create_starter_bundle("macOS")
starter_pwa = create_starter_bundle("Mobile / PWA")

# --- STYLING ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
        color: #F8FAFC !important;
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
        background: linear-gradient(135deg, #38BDF8 0%, #818CF8 50%, #F472B6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        letter-spacing: -0.02em;
        margin-bottom: 6px;
    }

    .portal-subtitle {
        font-size: 0.95rem;
        color: #94A3B8 !important;
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
        border: 3px solid #38BDF8;
        box-shadow: 0 0 30px rgba(56, 189, 248, 0.6);
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: rgba(15, 23, 42, 0.6);
        padding: 6px;
        border-radius: 14px;
        border: 1px solid rgba(56, 189, 248, 0.2);
    }

    .stTabs [data-baseweb="tab"] {
        height: 44px;
        border-radius: 10px;
        color: #94A3B8;
        font-weight: 600;
        font-size: 0.9rem;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, rgba(56, 189, 248, 0.2), rgba(129, 140, 248, 0.2)) !important;
        color: #38BDF8 !important;
        border: 1px solid rgba(56, 189, 248, 0.4);
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
        background: linear-gradient(90deg, #38BDF8, #818CF8, #F472B6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .workspace-metric .metric-label {
        font-size: 0.75rem;
        color: #94A3B8 !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-top: 0.3rem;
        font-weight: 700;
    }
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE & COOKIE RESTORATION ---
if "portal_unlocked" not in st.session_state:
    st.session_state.portal_unlocked = False
if "user_identity" not in st.session_state:
    st.session_state.user_identity = {}

handle_oauth_callback()

if not st.session_state.portal_unlocked:
    try:
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
    except Exception:
        pass

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
        <div class="portal-subtitle">Sovereign Enterprise Engine • Secure Gateway & Paywall</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

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
                    st.warning("This account was created via social sign-in. Use 'Continue with Google/GitHub' instead.")
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
                    time.sleep(0.1)
                    st.rerun()

        with tab_signup:
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            su_name = st.text_input("Preferred Full Name", key="su_name_input", placeholder="Analyst Name")
            su_email = st.text_input("Email Address", key="su_email_input", placeholder="name@domain.com")
            su_password = st.text_input("Choose Password", type="password", key="su_password_input", placeholder="At least 6 characters")
            su_password2 = st.text_input("Confirm Password", type="password", key="su_password2_input", placeholder="Re-enter password")

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
            st.markdown("### 🌍 Starter Configuration Bundles")
            st.download_button("📥 Download Windows Bundle", data=starter_win, file_name="chrishem_hub_windows_starter.zip", mime="application/zip", use_container_width=True)

# --- UNLOCKED WORKSPACE DASHBOARD (WITH PAYWALL SECTION) ---
else:
    identity = st.session_state.get("user_identity", {})
    current_user_email = identity.get("email", "")

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

    menu_selection = st.sidebar.radio("Select Workspace", [
        "⚡ Apex Dashboard",
        "💳 Paywall & Subscriptions",
        "📝 Query Log",
        "🔬 Bioinformatics Studio",
        "⚙️ Profile Settings",
        "🛡️ Admin Security & User Controls"
    ])

    st.title("⚡ Chrishem Sovereign Apex Hub")
    st.markdown("---")

    status = subscription.get_status(current_user_email)
    current_plan = status.get("plan", "trial")

    # Paywall Enforcer Check for Premium Studios
    is_paywalled_tier = current_plan not in ["active", "enterprise", "pro"] and not is_admin()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'<div class="workspace-metric"><div class="metric-value">{current_plan.title()}</div><div class="metric-label">Subscription Tier</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="workspace-metric"><div class="metric-value">{identity.get("name")}</div><div class="metric-label">Active Operator</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="workspace-metric"><div class="metric-value">{"Admin" if is_admin() else "Standard"}</div><div class="metric-label">Access Ring</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="glass-hr"></div>', unsafe_allow_html=True)

    if menu_selection == "⚡ Apex Dashboard":
        st.markdown("### 🌟 Welcome to the Core Ecosystem Workspace")
        st.write("Use the sidebar navigation to run tools, manage subscriptions, and unlock advanced workflows.")
        if is_paywalled_tier:
            st.warning("⚠️ **Your trial or free plan is currently restricted.** Visit the **Paywall & Subscriptions** tab to upgrade your access to Pro or Enterprise.")

    elif menu_selection == "💳 Paywall & Subscriptions":
        st.markdown("### 💳 Sovereign Paywall & License Management")
        st.write("Unlock full pipeline performance, live automated triggers, and enterprise priority speed by selecting a tier below.")

        pw_col1, pw_col2, pw_col3 = st.columns(3)

        with pw_col1:
            st.markdown("### 🌱 Starter / Trial")
            st.markdown("**Free Tier**\n- Basic tools\n- Community support")
            if st.button("Select Free Tier", use_container_width=True):
                subscription.upgrade_plan(current_user_email, "trial")
                st.success("Switched to Trial Tier.")
                st.rerun()

        with pw_col2:
            st.markdown("### 🚀 Pro Analyst")
            st.markdown("**$29 / month**\n- Full Bioinformatics Studio\n- Automated pipeline triggers\n- Priority performance")
            if st.button("Unlock Pro ($29)", use_container_width=True):
                subscription.upgrade_plan(current_user_email, "pro")
                st.success("🎉 Payment verified! Pro Tier unlocked successfully.")
                st.rerun()

        with pw_col3:
            st.markdown("### 👑 Sovereign Enterprise")
            st.markdown("**$99 / month**\n- Unlimited execution\n- Dedicated cluster support\n- Full admin privileges")
            if st.button("Unlock Enterprise ($99)", use_container_width=True):
                subscription.upgrade_plan(current_user_email, "enterprise")
                st.success("👑 Enterprise Access Activated!")
                st.rerun()

    elif menu_selection == "📝 Query Log":
        st.markdown("### 📝 Session Query Log")
        cursor = db_conn.cursor()
        cursor.execute("SELECT prompt, response, timestamp FROM live_chat_history WHERE username = ? ORDER BY id ASC", (identity.get("name"),))
        chat_rows = cursor.fetchall()
        for p, r, ts in chat_rows:
            st.markdown(f"""
            <div style="background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(56, 189, 248, 0.2); border-radius: 10px; padding: 0.85rem; margin-bottom: 0.75rem;">
                <b style="color: #38BDF8;">[{ts[:19]}]:</b> {p}<br><br>
                <b style="color: #818CF8;">Note:</b> {r}
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
        st.markdown("### 🧬 Genomic Sequence & GC-Content Studio")
        if is_paywalled_tier:
            st.error("🔒 **Paywall Enforced:** Advanced bioinformatics sequence pipelines require an active **Pro** or **Enterprise** subscription. Please upgrade via the **Paywall & Subscriptions** tab.")
        else:
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
        st.markdown("### ⚙️ Operator Profile & Avatar Customization")
        active_b64 = get_user_avatar_base64(current_user_email)
        if active_b64:
            st.markdown(f'<div style="margin-bottom:15px;"><img src="data:image/png;base64,{active_b64}" style="width:110px; height:110px; border-radius:50%; object-fit:cover; border:3px solid #38BDF8;"></div>', unsafe_allow_html=True)

        uploaded_avatar = st.file_uploader("Upload New Avatar Image (PNG, JPG)", type=["png", "jpg", "jpeg"])
        if st.button("💾 Save Custom Avatar", use_container_width=True):
            if uploaded_avatar is not None:
                image_bytes = uploaded_avatar.read()
                cursor = db_conn.cursor()
                cursor.execute("UPDATE auth_users SET avatar_blob = ? WHERE email = ?", (image_bytes, current_user_email))
                db_conn.commit()
                st.success("Avatar updated successfully!")
                st.rerun()

    elif menu_selection == "🛡️ Admin Security & User Controls":
        if not is_admin():
            st.error("🚫 Access Denied: This panel requires administrator clearance.")
        else:
            st.markdown("### 🛡️ Administrative Control Center")
            cursor = db_conn.cursor()
            cursor.execute("SELECT email, name, role FROM auth_users")
            users = cursor.fetchall()
            st.dataframe(pd.DataFrame(users, columns=["Email", "Name", "Role"]), use_container_width=True)