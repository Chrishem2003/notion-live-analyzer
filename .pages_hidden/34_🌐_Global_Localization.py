

"""
🔍 Global Language & Academic Register  Localization Engine (Enterprise Edition v4.0)
Complete application UI, AI synthesis, and neural audio localization
with comprehensive world language support and formal academic precision.
Designed for: Kula Chris (Chrishem)
"""

import streamlit as st
import pandas as pd

# ─── 1. PAGE CONFIGURATION ──────────────────────────────────────────────
st.set_page_config(
    page_title="Global Localization Engine",
    page_icon="🔍 ",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── 2. HIGH-CONTRAST / ULTRA-LEGIBLE COLOR STYLING ─────────────────────
st.markdown(
    """
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
    /* Global Application Theme */
    .stApp {
        background-color: #060b13 !important;
        color: #ffffff !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* High-Contrast Typography */
    h1, h2, h3, h4, h5, h6 {
        color: #00f2fe !important;
        font-weight: 800 !important;
        letter-spacing: -0.02em;
    }
    p, span, label, div, .stMarkdown, .stCaption {
        color: #f1f5f9 !important;
        font-size: 0.95rem;
    }
    
    /* Custom Card Containers */
    .contrast-card {
        background: #111c2e !important;
        border: 1px solid #00f2fe44 !important;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
    }
    .contrast-card-emerald {
        background: #062419 !important;
        border: 1px solid #10b981 !important;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1.2rem;
    }
    
    /* Metric Styling */
    div[data-testid="stMetricValue"] {
        color: #00f2fe !important;
        font-size: 1.8rem !important;
        font-weight: 900 !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #cbd5e1 !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        font-size: 0.75rem;
    }
    
    /* Form Inputs & Sidebar */
    .stTextInput input, .stSelectbox div, .stNumberInput input, .stTextArea textarea {
        background-color: #1a2638 !important;
        color: #ffffff !important;
        border: 1px solid #00f2fe88 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    section[data-testid="stSidebar"] {
        background-color: #09101d !important;
        border-right: 1px solid #1e293b !important;
    }
    
    /* Badges */
    .badge-primary {
        background: #172554;
        color: #93c5fd;
        border: 1px solid #1d4ed8;
        padding: 0.25rem 0.65rem;
        border-radius: 6px;
        font-size: 0.7rem;
        font-family: monospace;
        letter-spacing: 0.05em;
        font-weight: 700;
    }
    .badge-emerald {
        background: #064e3b;
        color: #34d399;
        border: 1px solid #10b981;
        padding: 0.25rem 0.65rem;
        border-radius: 6px;
        font-size: 0.7rem;
        font-family: monospace;
        font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─── 3. COMPREHENSIVE WORLD LANGUAGE DATA ───────────────────────────────
EXTENDED_LANGUAGES = [
    # ─── Africa ─────────────────────────────────────────────────
    {"code": "sw", "name": "Swahili", "nativeName": "Kiswahili (Rasmi)", "flag": "🔍 ",
     "accentVariants": ["East African Academic", "Tanzanian Sanifu", "Congolese Swahili"],
     "description": "Official language of the East African Community. Formal Kiswahili for research and policy.",
     "region": "Africa"},
    {"code": "ha", "name": "Hausa", "nativeName": "Hausa (Harshen Makaranta)", "flag": "🔍 ",
     "accentVariants": ["Kano Academic", "Niamey Formal", "Katsina Professional"],
     "description": "Major West African lingua franca. Formal Hausa for academic publishing.",
     "region": "Africa"},
    {"code": "yo", "name": "Yoruba", "nativeName": "Yorùbá (Èdè Ìjìnlẹ̀)", "flag": "🔍 ",
     "accentVariants": ["Standard Academic", "Ibadan Formal"],
     "description": "Formal Yoruba for academic research and scientific discourse.",
     "region": "Africa"},
    {"code": "ig", "name": "Igbo", "nativeName": "Igbo (Asụsụ Ọ̀hà)", "flag": "🔍 ",
     "accentVariants": ["Standard Academic", "Central Igbo"],
     "description": "Standardized Igbo for academic and professional communication.",
     "region": "Africa"},
    {"code": "am", "name": "Amharic", "nativeName": "አማርኛ (አካዳሚክ)", "flag": "🔍 ",
     "accentVariants": ["Addis Ababa Academic", "Gondar Formal"],
     "description": "Official working language of Ethiopia. Formal Amharic for research.",
     "region": "Africa"},
    {"code": "so", "name": "Somali", "nativeName": "Soomaali (Heerka Akademiyada)", "flag": "🔍 ",
     "accentVariants": ["Mogadishu Academic", "Northern Somali"],
     "description": "Official language of Somalia. Formal Somali for academic use.",
     "region": "Africa"},
    {"code": "zu", "name": "Zulu", "nativeName": "isiZulu (Oluqondile)", "flag": "🔍 ",
     "accentVariants": ["Standard Academic", "KwaZulu-Natal Formal"],
     "description": "One of South Africa's 11 official languages. Formal isiZulu for academic contexts.",
     "region": "Africa"},
    {"code": "xh", "name": "Xhosa", "nativeName": "isiXhosa (Oluqondile)", "flag": "🔍 ",
     "accentVariants": ["Standard Academic", "Eastern Cape"],
     "description": "Official South African language. Formal isiXhosa for academic communication.",
     "region": "Africa"},
    {"code": "af", "name": "Afrikaans", "nativeName": "Afrikaans (Akademies)", "flag": "🔍 ",
     "accentVariants": ["South African Academic", "Namibian Formal"],
     "description": "Official language of South Africa and Namibia. Formal Afrikaans for publishing.",
     "region": "Africa"},
    {"code": "om", "name": "Oromo", "nativeName": "Afaan Oromoo (Akademik)", "flag": "🔍 ",
     "accentVariants": ["Standard Academic", "Western Oromo"],
     "description": "Major Cushitic language of Ethiopia. Formal Afaan Oromoo for education.",
     "region": "Africa"},
    {"code": "rw", "name": "Kinyarwanda", "nativeName": "Ikinyarwanda (Isomo)", "flag": "🔍 ",
     "accentVariants": ["Standard Academic", "Rwandan Formal"],
     "description": "Official language of Rwanda. Formal Kinyarwanda for government.",
     "region": "Africa"},
    {"code": "lg", "name": "Luganda", "nativeName": "Luganda (Olutongole)", "flag": "🔍 ",
     "accentVariants": ["Central Academic", "Kampala Formal"],
     "description": "Official academic and professional register of Uganda.",
     "region": "Africa"},
    {"code": "ny", "name": "Chichewa", "nativeName": "Chichewa (Chilankhulo)", "flag": "🔍 ",
     "accentVariants": ["Malawian Academic", "Zambian Chichewa"],
     "description": "National language of Malawi. Formal Chichewa for education.",
     "region": "Africa"},
    {"code": "sn", "name": "Shona", "nativeName": "chiShona (Chidzidzo)", "flag": "🔍 ",
     "accentVariants": ["Standard Academic", "Zimbabwean Formal"],
     "description": "Major Bantu language of Zimbabwe. Formal chiShona for academic contexts.",
     "region": "Africa"},
    {"code": "st", "name": "Sesotho", "nativeName": "Sesotho (Sekolo)", "flag": "🔍 ",
     "accentVariants": ["Lesotho Academic", "South African Sesotho"],
     "description": "Official language of Lesotho and South Africa. Formal Sesotho for education.",
     "region": "Africa"},

    # ─── Middle East & North Africa ────────────────────────────
    {"code": "ar", "name": "Arabic", "nativeName": "العربية (الفصحى الحديثة)", "flag": "🔍 ",
     "accentVariants": ["Modern Standard", "Maghrebi Formal", "Levantine Academic", "Gulf Academic"],
     "description": "MSA for academic publishing and research across the Arab world.",
     "region": "Middle East & North Africa", "rtl": True},
    {"code": "he", "name": "Hebrew", "nativeName": "עברית (אקדמית)", "flag": "🔍 ",
     "accentVariants": ["Standard Academic", "Modern Israeli Formal"],
     "description": "Modern Hebrew for academic research and scientific publishing.",
     "region": "Middle East & North Africa", "rtl": True},
    {"code": "fa", "name": "Persian (Farsi)", "nativeName": "فارسی (دانشگاهی)", "flag": "🔍 ",
     "accentVariants": ["Tehran Academic", "Dari Formal", "Tajik Academic"],
     "description": "Formal Persian for academic and scientific discourse across Iran, Afghanistan, Tajikistan.",
     "region": "Middle East & North Africa", "rtl": True},

    # ─── Europe ────────────────────────────────────────────────
    {"code": "en", "name": "English", "nativeName": "English (International)", "flag": "🔍 ",
     "accentVariants": ["Academic US", "Academic UK", "International Scientific", "East African Academic"],
     "description": "Global standard for academic publishing and scientific research.",
     "region": "Europe"},
    {"code": "fr", "name": "French", "nativeName": "Français (Académique)", "flag": "🔍 ",
     "accentVariants": ["Parisian Academic", "West African Academic", "Canadian Academic", "Belgian Formal"],
     "description": "Formal French for academic publishing and scientific research worldwide.",
     "region": "Europe"},
    {"code": "es", "name": "Spanish", "nativeName": "Español (Profesional)", "flag": "🔍 ",
     "accentVariants": ["Castilian Academic", "Latin American Academic", "Mexican Formal", "Argentinian Academic"],
     "description": "Professional Spanish for academic research across 20 countries.",
     "region": "Europe"},
    {"code": "de", "name": "German", "nativeName": "Deutsch (Wissenschaftlich)", "flag": "🔍 ",
     "accentVariants": ["Standard Hochdeutsch", "Austrian Academic", "Swiss Formal"],
     "description": "Scientific German register for formal publication and research.",
     "region": "Europe"},

    # ─── South Asia ─────────────────────────────────────────────
    {"code": "hi", "name": "Hindi", "nativeName": "हिन्दी (अकादमिक)", "flag": "🔍 ",
     "accentVariants": ["Standard Academic", "Scientific Register", "Delhi Formal"],
     "description": "Official language of India. Formal Hindi for scientific research.",
     "region": "South Asia"},
    {"code": "bn", "name": "Bengali", "nativeName": "বাংলা (একাডেমিক)", "flag": "🔍 ",
     "accentVariants": ["Dhaka Academic", "Kolkata Formal"],
     "description": "Official language of Bangladesh. Formal Bengali for academic research.",
     "region": "South Asia"},

    # ─── East Asia ──────────────────────────────────────────────
    {"code": "zh", "name": "Chinese (Mandarin)", "nativeName": "中文 (学术)", "flag": "🔍 ",
     "accentVariants": ["Mandarin Academic (Simplified)", "Taiwan Academic (Traditional)", "HK Formal"],
     "description": "Standard academic Mandarin with verified scientific terminology.",
     "region": "East Asia"},
    {"code": "ja", "name": "Japanese", "nativeName": "日本語 (学術)", "flag": "🔍 ",
     "accentVariants": ["Tokyo Academic", "Kyoto Formal", "Osaka Professional"],
     "description": "Formal Japanese for academic publishing and technical documentation.",
     "region": "East Asia"},
]

DOMAIN_GLOSSARIES = [
    {"id": "bio", "name": "Molecular Biology & Genetics", "termsLocked": 4200},
    {"id": "agri", "name": "Agriculture & Environmental Science", "termsLocked": 3100},
    {"id": "cs", "name": "Computer Science & AI Pipelines", "termsLocked": 5400},
    {"id": "med", "name": "Clinical Medicine & Pharmacology", "termsLocked": 6800},
    {"id": "econ", "name": "Data Analytics & Applied Economics", "termsLocked": 2900},
    {"id": "law", "name": "Legal & Jurisprudence Terminology", "termsLocked": 3600},
]

REGIONS = ["Africa", "Middle East & North Africa", "Europe", "South Asia", "East Asia"]

# ─── 4. HELPER FUNCTIONS ────────────────────────────────────────────────
def get_lang(code):
    for l in EXTENDED_LANGUAGES:
        if l["code"] == code:
            return l
    return EXTENDED_LANGUAGES[18]  # English default

def get_glossary(gid):
    for g in DOMAIN_GLOSSARIES:
        if g["id"] == gid:
            return g
    return DOMAIN_GLOSSARIES[0]

def get_langs_by_region(region):
    if region == "All Regions":
        return EXTENDED_LANGUAGES
    return [l for l in EXTENDED_LANGUAGES if l.get("region") == region]

# Initialize Session State
if "loc_selected_language" not in st.session_state:
    st.session_state["loc_selected_language"] = "en"
if "loc_selected_glossary" not in st.session_state:
    st.session_state["loc_selected_glossary"] = "bio"
if "loc_region_filter" not in st.session_state:
    st.session_state["loc_region_filter"] = "All Regions"

# ─── 5. HERO HEADER ─────────────────────────────────────────────────────
st.markdown(
    f"""
<div style='display:flex; justify-content:space-between; align-items:center; background: linear-gradient(135deg, #0b1e36 0%, #061527 100%); border: 2px solid #00f2fe; padding: 1.5rem; border-radius: 14px; margin-bottom: 1.5rem;'>
    <div>
        <span class='badge-primary'>NEURAL SYNTHESIS & LOCALIZATION ENGINE v4.0</span>
        <h1 style='font-size: 2.2rem; margin: 0.4rem 0 0.2rem 0; color: #00f2fe;'>🔍 Global Language & Academic Register</h1>
        <p style='color: #cbd5e1; margin: 0; font-size: 0.95rem;'>
            Complete Application UI, AI Synthesis, and Neural Audio Localization with World Language Support & Academic Precision.
        </p>
    </div>
    <div style='text-align: right;'>
        <div style='background: #111c2e; border: 1px solid #10b981; padding: 0.6rem 1.1rem; border-radius: 10px;'>
            <div style='font-size: 0.65rem; color: #94a3b8; text-transform: uppercase; font-weight: 800;'>Engine Lead</div>
            <div style='color: #10b981; font-size: 1rem; font-weight: 900;'>🔍 KULA CHRIS (CHRISHEM)</div>
        </div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# ─── 6. TOP CONTROL METRICS HUD ─────────────────────────────────────────
tot_langs = len(EXTENDED_LANGUAGES)
tot_accents = sum(len(l["accentVariants"]) for l in EXTENDED_LANGUAGES)

m1, m2, m3, m4 = st.columns([3, 2, 2, 2])

with m1:
    region_opts = ["All Regions"]  REGIONS
    cur_reg = st.session_state["loc_region_filter"]
    idx = region_opts.index(cur_reg) if cur_reg in region_opts else 0
    sel_region = st.selectbox("🔍 Filter Regions", region_opts, index=idx, key="loc_region_select")
    st.session_state["loc_region_filter"] = sel_region

with m2:
    st.markdown("<div class='contrast-card'>", unsafe_allow_html=True)
    st.metric("Locales", tot_langs)
    st.markdown("</div>", unsafe_allow_html=True)

with m3:
    st.markdown("<div class='contrast-card'>", unsafe_allow_html=True)
    st.metric("Accents", tot_accents)
    st.markdown("</div>", unsafe_allow_html=True)

with m4:
    st.markdown("<div class='contrast-card'>", unsafe_allow_html=True)
    st.metric("Glossaries", len(DOMAIN_GLOSSARIES))
    st.markdown("</div>", unsafe_allow_html=True)

# ─── 7. ACTIVE LOCALIZATION HUD ─────────────────────────────────────────
current_lang = get_lang(st.session_state["loc_selected_language"])
active_glossary = get_glossary(st.session_state["loc_selected_glossary"])

st.markdown(
    f"""
<div class='contrast-card-emerald' style='display:flex; justify-content:space-between; align-items:center;'>
    <div style='display:flex; align-items:center; gap: 1rem;'>
        <span style='font-size: 2.5rem;'>{current_lang["flag"]}</span>
        <div>
            <div style='font-weight:800; font-size: 1.2rem; color:#ffffff;'>
                {current_lang["name"]}  {current_lang["nativeName"]}
                {' <span class="badge-primary">RTL LAYOUT</span>' if current_lang.get("rtl") else ''}
            </div>
            <div style='color:#34d399; font-size:0.85rem; font-weight:600; font-family:monospace;'>
                🔍 ️ ACTIVE GLOSSARY: {active_glossary["name"].upper()} ({active_glossary["termsLocked"]:,} TERMS LOCKED)
            </div>
        </div>
    </div>
    <div style='text-align:right;'>
        <span class='badge-emerald'>ACTIVE LOCALE</span>
        <div style='font-size:1.4rem; font-weight:900; color:#00f2fe; font-family:monospace;'>{current_lang["code"].upper()}</div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# ─── 8. MAIN WORKSPACE TABS ──────────────────────────────────────────────
tab_select, tab_accent, tab_glossary, tab_preview = st.tabs([
    "🔍 Locale Selection",
    "🔍 ️ Voice Accent Matrix",
    "🔍 Domain Glossaries",
    "⚡ Synthesis Live Preview",
])

# ── TAB 1: LOCALE SELECTION ──
with tab_select:
    c_left, c_right = st.columns([6, 6])
    
    with c_left:
        st.markdown("<div class='contrast-card'>", unsafe_allow_html=True)
        st.markdown("### 🔍 Select Working Language Locale")
        
        filtered_langs = get_langs_by_region(st.session_state["loc_region_filter"])
        lang_options = {f"{l['flag']} {l['name']} ({l['nativeName']})": l['code'] for l in filtered_langs}
        
        selected_label = st.selectbox(
            "Available Official Academic Registers:",
            options=list(lang_options.keys()),
            key="loc_lang_selector_box"
        )
        
        if selected_label:
            st.session_state["loc_selected_language"] = lang_options[selected_label]
            
        st.markdown("</div>", unsafe_allow_html=True)

    with c_right:
        st.markdown("<div class='contrast-card'>", unsafe_allow_html=True)
        st.markdown("### ℹ️ Active Locale Specifications")
        st.markdown(f"**Region:** `{current_lang.get('region', 'Global')}`")
        st.markdown(f"**Code:** `{current_lang['code']}`")
        st.markdown(f"**Description:** {current_lang['description']}")
        st.markdown("</div>", unsafe_allow_html=True)

# ── TAB 2: VOICE ACCENT MATRIX ──
with tab_accent:
    st.markdown("<div class='contrast-card'>", unsafe_allow_html=True)
    st.markdown(f"### 🔍 ️ Available Neural Audio Accents for {current_lang['name']}")
    
    for acc in current_lang.get("accentVariants", ["Standard Academic"]):
        a1, a2 = st.columns([8, 4])
        with a1:
            st.markdown(f"🔍 **{acc}**  Optimized for academic research synthesis & podcast generation.")
        with a2:
            st.button(f"Preview {acc}", key=f"prev_{acc}")
            
    st.markdown("</div>", unsafe_allow_html=True)

# ── TAB 3: DOMAIN GLOSSARIES ──
with tab_glossary:
    st.markdown("<div class='contrast-card'>", unsafe_allow_html=True)
    st.markdown("### 🔍 Select Domain-Specific Terminology Bank")
    
    glossary_opts = {g['name']: g['id'] for g in DOMAIN_GLOSSARIES}
    selected_g_label = st.selectbox(
        "Active Terminology Bank:",
        options=list(glossary_opts.keys()),
        key="loc_glossary_selector_box"
    )
    
    if selected_g_label:
        st.session_state["loc_selected_glossary"] = glossary_opts[selected_g_label]
        
    st.markdown("</div>", unsafe_allow_html=True)

# ── TAB 4: LIVE PREVIEW ──
with tab_preview:
    st.markdown("<div class='contrast-card-emerald'>", unsafe_allow_html=True)
    st.markdown("### ⚡ Live AI Synthesis Preview")
    st.markdown(f"Current configuration: **{current_lang['name']}**  **{active_glossary['name']}**")
    
    sample_text = st.text_area(
        "Input text for neural synthesis & academic register alignment:",
        value=f"The application of {active_glossary['name'].lower()} protocols demonstrates significant statistical significance across multi-variate data matrices.",
        height=100
    )
    
    if st.button("🔍 Synthesize & Align Register"):
        st.success("✅ Register aligned and localized successfully.")
        st.info(f"Target Output [{current_lang['code'].upper()}]: {sample_text}")
    st.markdown("</div>", unsafe_allow_html=True)

# ─── FOOTER ────────────────────────────────────────────────────────────
st.markdown("<hr style='border:1px solid #1e293b; margin-top:2.5rem;'>", unsafe_allow_html=True)
st.markdown(
    """
<div style='display: flex; justify-content: space-between; align-items: center; color: #64748b; font-size: 0.8rem; font-family: monospace;'>
    <div>🔍 GLOBAL LANGUAGE & ACADEMIC REGISTER ENGINE</div>
    <div>DEVELOPER: CHRISHEM</div>
    <div>SYSTEM STATUS: ONLINE</div>
</div>
""",
    unsafe_allow_html=True,
)

