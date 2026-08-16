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

from modules import subscription
import modules.billing_stripe as billing_stripe

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Chrishem Science Hub - Sovereign Enterprise Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

PBKDF2_ITERATIONS = 260_000


@st.cache_resource
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
            pass

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


# --- PASSWORD HASHING ---
def _hash_password(password: str, salt_hex: str = None):
    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return dk.hex(), salt.hex()


def _verify_password(password: str, stored_hash_hex: str, salt_hex: str) -> bool:
    computed_hash, _ = _hash_password(password, salt_hex)
    return hmac.compare_digest(computed_hash, stored_hash_hex)


def ensure_bootstrap_admin():
    cursor = db_conn.cursor()
    if cursor.execute("SELECT COUNT(*) FROM auth_users").fetchone()[0] > 0:
        return

    bootstrap_email = os.environ.get("SOVEREIGN_ADMIN_EMAIL")
    bootstrap_password = os.environ.get("SOVEREIGN_ADMIN_PASSWORD")
    if bootstrap_email and bootstrap_password:
        pwd_hash, salt = _hash_password(bootstrap_password)
        email_norm = bootstrap_email.lower().strip()
        cursor.execute(
            "INSERT INTO auth_users (email, name, password_hash, salt, role) VALUES (?,?,?,?,?)",
            (email_norm, "Administrator", pwd_hash, salt, "admin"),
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


# --- OAUTH CONFIGURATION ---
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
        st.error(f"{provider_key.title()} sign-in is not configured.")
        return False

    try:
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
        access_token = resp.json().get("access_token")
        
        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
        u_resp = requests.get(cfg["userinfo_url"], headers=headers, timeout=10)
        u_resp.raise_for_status()
        data = u_resp.json()

        email = data.get("email")
        name = data.get("name") or data.get("login") or email.split("@")[0]
        provider_id = str(data.get("sub") or data.get("id"))

        user = auth_store.get_or_create_oauth_user(email, name, provider_key, provider_id)
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
    except Exception as e:
        st.query_params.clear()
        st.error(f"OAuth sign-in failed: {e}")
        return False


def render_oauth_buttons():
    configured = get_configured_providers()
    if not configured or not get_redirect_uri():
        return
    for key, cfg in configured.items():
        url = build_authorize_url(key, cfg)
        st.link_button(f"{cfg['icon']} Continue with {cfg['label']}", url, use_container_width=True)


def handle_checkout_return():
    qp = st.query_params
    if qp.get("checkout") == "success" and qp.get("session_id"):
        result = billing_stripe.verify_checkout_session(qp["session_id"])
        st.query_params.clear()
        if result:
            st.session_state["_billing_toast"] = f"✅ Upgraded to **{result['plan'].title()}**."
        else:
            st.session_state["_billing_toast"] = "⚠️ Confirmation pending. Check billing status."
    elif qp.get("checkout") == "cancelled":
        st.query_params.clear()
        st.session_state["_billing_toast"] = "ℹ️ Checkout cancelled."


def is_admin():
    identity = st.session_state.get("user_identity", {})
    return identity.get("role") == "admin"


def create_starter_bundle(platform_name):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr("README.md", f"# Chrishem Starter ({platform_name})\nRun `streamlit run app.py`.")
        zip_file.writestr("config.toml", "[server]\nheadless = true")
    return zip_buffer.getvalue()


starter_win = create_starter_bundle("Windows")
starter_linux = create_starter_bundle("Linux")

# --- STUNNING CSS DESIGN THEME ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
        color: #F8FAFC !important;
    }

    .stApp {
        background: radial-gradient(circle at 15% 20%, #0d1326 0%, #04060a 85%);
        background-attachment: fixed;
    }

    /* Gorgeous Dark Glassmorphism Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #030712 0%, #0b1120 100%) !important;
        border-right: 1px solid rgba(56, 189, 248, 0.15);
    }
    [data-testid="stSidebar"] * {
        color: #E2E8F0 !important;
    }

    /* Hero Glass Card */
    .portal-hero-card {
        background: linear-gradient(135deg, rgba(17, 24, 39, 0.85) 0%, rgba(11, 17, 32, 0.95) 100%);
        border: 1px solid rgba(56, 189, 248, 0.3);
        border-radius: 28px;
        padding: 40px 30px;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.8), 0 0 30px rgba(56, 189, 248, 0.1);
        max-width: 860px;
        margin: 2rem auto;
    }

    .portal-title {
        font-size: 2.4rem;
        font-weight: 800;
        background: linear-gradient(135deg, #38BDF8 0%, #818CF8 50%, #F472B6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        letter-spacing: -0.5px;
    }

    .portal-subtitle {
        font-size: 0.9rem;
        color: #94A3B8 !important;
        font-weight: 700;
        text-align: center;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-top: 8px;
        margin-bottom: 22px;
    }

    /* Metrics & Cards */
    .workspace-metric {
        background: linear-gradient(145deg, rgba(30, 41, 59, 0.6), rgba(15, 23, 42, 0.85));
        border: 1px solid rgba(56, 189, 248, 0.25);
        border-radius: 20px;
        padding: 1.5rem;
        text-align: center;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .workspace-metric:hover {
        transform: translateY(-3px);
        border-color: rgba(56, 189, 248, 0.6);
    }
    .workspace-metric .metric-value {
        font-size: 2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #38BDF8, #818CF8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .workspace-metric .metric-label {
        font-size: 0.75rem;
        color: #94A3B8 !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 0.4rem;
        font-weight: 600;
    }

    /* Custom Form Styling Adjustments */
    .stTextInput input, .stTextArea textarea {
        background-color: rgba(15, 23, 42, 0.7) !important;
        border: 1px solid rgba(56, 189, 248, 0.2) !important;
        color: #F8FAFC !important;
        border-radius: 12px !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #38BDF8 !important;
        box-shadow: 0 0 15px rgba(56, 189, 248, 0.3) !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- SESSION RESTORATION ---
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

# --- PORTAL GATEWAY SCREEN (LOCKED) ---
if not st.session_state.portal_unlocked:
    st.markdown("<style>[data-testid=\"stSidebar\"] {display: none;}</style>", unsafe_allow_html=True)
    
    st.markdown("""
    <div class="portal-hero-card">
        <div style="display: flex; justify-content: center; margin-bottom: 10px;"><div style="font-size: 50px; text-align:center;">⚡</div></div>
        <div class="portal-title">CHRISHEM SCIENCE HUB</div>
        <div class="portal-subtitle">Sovereign Enterprise Engine • Secure Multi-Platform Gateway</div>
    </div>
    """, unsafe_allow_html=True)

    _, portal_col, _ = st.columns([0.4, 3.2, 0.4])
    with portal_col:
        tab_signin, tab_signup, tab_downloads = st.tabs(["🔐 Secure Sign In", "📝 Register Account", "📱 Ecosystem Downloads"])

        with tab_signin:
            render_oauth_buttons()
            si_email = st.text_input("Portal Email Address", key="si_email_input", placeholder="name@domain.com")
            si_password = st.text_input("Secure Password", type="password", key="si_password_input", placeholder="••••••••")
            remember_me = st.checkbox("Remember Me on this Device", value=True, key="remember_me_checkbox")

            if st.button("🚀 Unlock Portal Workspace", use_container_width=True):
                user = auth_store.verify_login(si_email, si_password)
                if user is None:
                    st.error("Incorrect email or password.")
                elif user.get("oauth_only"):
                    st.warning("Account created via social sign-in. Use social buttons.")
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
            su_name = st.text_input("Full Name", key="su_name_input", placeholder="Analyst Name")
            su_email = st.text_input("Email Address", key="su_email_input", placeholder="name@domain.com")
            su_password = st.text_input("Choose Password", type="password", key="su_password_input", placeholder="••••••••")
            su_password2 = st.text_input("Confirm Password", type="password", key="su_password2_input", placeholder="••••••••")

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
                        st.success("Account created successfully! Switch to 'Secure Sign In'.")

        with tab_downloads:
            st.markdown("### 🌍 Starter Configuration Bundles")
            st.download_button("📥 Download Windows Bundle", data=starter_win, file_name="windows_starter.zip", mime="application/zip", use_container_width=True)
            st.download_button("📥 Download Linux Bundle", data=starter_linux, file_name="linux_starter.zip", mime="application/zip", use_container_width=True)

# --- UNLOCKED WORKSPACE DASHBOARD ---
else:
    identity = st.session_state.get("user_identity", {})
    current_user_email = identity.get("email", "")

    st.sidebar.markdown("### ⚡ CHRISHEM APEX")
    st.sidebar.markdown(f"**Operator:** `{identity.get('name')}`")
    st.sidebar.markdown(f"**Email:** `{current_user_email}`")
    st.sidebar.markdown(f"**Privilege:** `{'👑 Admin' if is_admin() else 'Standard User'}`")
    st.sidebar.markdown("---")

    if st.sidebar.button("🔒 Lock Portal & Sign Out", use_container_width=True):
        cookie_manager.delete("chrishem_user_email")
        st.session_state.portal_unlocked = False
        st.rerun()

    menu_selection = st.sidebar.radio("Navigation Workspace", [
        "⚡ Apex Dashboard",
        "💳 Billing & Subscription",
        "📝 Query Log",
        "🔬 Bioinformatics Studio",
        "⚙️ Profile Settings",
        "🛡️ Admin Security Center"
    ])

    toast_msg = st.session_state.pop("_billing_toast", None)
    if toast_msg:
        st.toast(toast_msg) if hasattr(st, "toast") else st.info(toast_msg)

    st.title("⚡ Chrishem Sovereign Apex Hub")
    st.markdown("---")

    status = subscription.get_status(current_user_email)
    plan_label = "Admin (full access)" if is_admin() else status["effective_plan"].title()

    if menu_selection == "⚡ Apex Dashboard":
        st.markdown("### 🌟 Welcome to the Core Ecosystem Workspace")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown('<div class="workspace-metric"><div class="metric-value">Active</div><div class="metric-label">Gateway Status</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="workspace-metric"><div class="metric-value">{identity.get("name")}</div><div class="metric-label">Active Operator</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="workspace-metric"><div class="metric-value">{"Admin" if is_admin() else "Standard"}</div><div class="metric-label">Access Ring</div></div>', unsafe_allow_html=True)

    elif menu_selection == "💳 Billing & Subscription":
        st.markdown("### 💳 Billing & Subscription Management")
        s1, s2, s3 = st.columns(3)
        s1.metric("Current plan", plan_label)
        s2.metric("Status", status["status"].title())
        s3.metric("Trial days left", status["days_left_in_trial"] if status["days_left_in_trial"] is not None else "—")

    elif menu_selection == "📝 Query Log":
        st.markdown("### 📝 Session Query Log")
        user_prompt = st.text_area("Log a query or note for reference:", key="portal_ai_input")
        if st.button("💾 Save to Log"):
            if user_prompt.strip():
                cursor = db_conn.cursor()
                cursor.execute("INSERT INTO live_chat_history (username, timestamp, prompt, response) VALUES (?, ?, ?, ?)",
                               (identity.get("name"), datetime.datetime.now().isoformat(), user_prompt, "Logged successfully."))
                db_conn.commit()
                st.rerun()

    elif menu_selection == "🔬 Bioinformatics Studio":
        st.markdown("### 🧬 Genomic Sequence Analysis")
        seq_input = st.text_area("Paste FASTA Sequence Data", placeholder="ATGCGATCG...")
        if st.button("Run Sequence Metric Analysis"):
            if seq_input.strip():
                clean_seq = "".join(seq_input.upper().split())
                length = len(clean_seq)
                gc = ((clean_seq.count('G') + clean_seq.count('C')) / length * 100) if length > 0 else 0
                st.metric("Total Base Pairs", f"{length} bp")
                st.metric("GC-Content Ratio", f"{gc:.2f}%")

    elif menu_selection == "⚙️ Profile Settings":
        st.markdown("### ⚙️ Operator Profile Preferences")
        uploaded_avatar = st.file_uploader("Upload New Avatar Image", type=["png", "jpg", "jpeg"])
        if st.button("💾 Save Custom Avatar", use_container_width=True):
            if uploaded_avatar is not None:
                image_bytes = uploaded_avatar.read()
                cursor = db_conn.cursor()
                cursor.execute("UPDATE auth_users SET avatar_blob = ? WHERE email = ?", (image_bytes, current_user_email))
                db_conn.commit()
                st.success("Avatar successfully updated!")
                st.rerun()

    elif menu_selection == "🛡️ Admin Security Center":
        if not is_admin():
            st.error("🚫 Access Denied: Requires administrator clearance.")
        else:
            st.markdown("### 🛡️ Administrative Control Center")
            cursor = db_conn.cursor()
            cursor.execute("SELECT email, name, role FROM auth_users")
            users = cursor.fetchall()
            st.dataframe(pd.DataFrame(users, columns=["Email", "Name", "Role"]), use_container_width=True)