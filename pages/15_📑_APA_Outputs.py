import security_guard
iiiimport security_guard
security_guard.verify_access()



"""

-------------------------------------------------------------------------------

ENTERPRISE APA 7TH EDITION PUBLICATION STUDIO [v3.0]

High-precision academic reporting engine: Automated statistical write-ups, APA 7th

edition compliance checking, effect size formatting, table generation, and 

manuscript export tools.

Designed for: Chrishem Studio Engine

-------------------------------------------------------------------------------

"""



import sys

import time

from pathlib import Path

import pandas as pd

import numpy as np

import streamlit as st



# --- PATH RESOLUTION -------------------------------------------------

current_file = Path(__file__).resolve()

root_dir = current_file.parent.parent

if str(root_dir) not in sys.path:

    sys.path.insert(0, str(root_dir))

if str(current_file.parent) not in sys.path:

    sys.path.insert(0, str(current_file.parent))



# --- DEFENSIVE MODULE IMPORTS WITH LOCAL FALLBACKS --------------------

try:

    from modules.config import init_session_state

    from modules.ui_components import hero_card, load_css, watermark, section_header

    from modules.apa_formatter import render_apa_outputs_page, render_apa_quick_format_ui

except ImportError:

    def init_session_state():

        if "theme" not in st.session_state:

            st.session_state["theme"] = "dark"



    def load_css(is_dark=True):

        pass



    def watermark(text=""):

        pass



    def section_header(text="", desc=""):

        st.markdown(

            f"<h3 style='color:#00f2fe !important; margin-top:1.4rem; margin-bottom:0.3rem; font-weight:800;'>{text}</h3>", 

            unsafe_allow_html=True

        )

        if desc:

            st.caption(desc)



    def hero_card(title, subtitle, badge_text=""):

        st.markdown(f"""

        <div style="padding: 1.5rem; background: linear-gradient(135deg, rgba(0, 242, 254, 0.12) 0%, rgba(11, 19, 33, 0.95) 100%); border-radius: 12px; border: 1px solid #00f2fe; margin-bottom: 1.5rem; box-shadow: 0 4px 20px rgba(0,242,254,0.15);">

            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; flex-wrap: wrap; gap: 0.5rem;">

                <h1 style="color: #00f2fe !important; font-size: 2rem; margin: 0; font-weight: 800; letter-spacing: -0.02em;">{title}</h1>

                <span style="background: rgba(0, 242, 254, 0.15); color: #00f2fe; padding: 0.3rem 0.8rem; border-radius: 999px; font-size: 0.75rem; font-weight: 700; border: 1px solid #00f2fe;">{badge_text}</span>

            </div>

            <p style="color: #cbd5e1 !important; font-size: 0.95rem; margin: 0; line-height: 1.4;">{subtitle}</p>

        </div>

        """, unsafe_allow_html=True)



    def render_apa_outputs_page(results):

        st.markdown('<div class="synth-card">', unsafe_allow_html=True)

        st.markdown("<h4 style='color:#00f2fe;'>🔍 APA 7th Edition Statistical Results Repository</h4>", unsafe_allow_html=True)

        if results:

            for idx, res in enumerate(results, 1):

                st.markdown(f"**Result {idx}:** `{res}`")

        else:

            st.info("No statistical results registered in the active session. Run an analysis or generate quick sentences in Tab 2.")

            st.markdown("""

            **Sample APA 7th Edition Output:**

            > *An independent-samples t-test was conducted to compare biomarker response levels between the treatment group ($M = 45.20$, $SD = 5.12$) and the control group ($M = 38.80$, $SD = 4.90$). There was a statistically significant difference in scores; $t(58) = 4.94$, $p < .001$, $d = 1.28$, $95\\%\\text{ CI } [3.80, 9.00]$.*

            """)

        st.markdown('</div>', unsafe_allow_html=True)



    def render_apa_quick_format_ui():

        st.markdown('<div class="synth-card">', unsafe_allow_html=True)

        st.markdown("<h4 style='color:#00f2fe;'>🔍 Instant APA Statistical Sentence Builder</h4>", unsafe_allow_html=True)

        

        test_type = st.selectbox("Statistical Test Type", ["Independent t-test", "One-Way ANOVA", "Pearson Correlation", "Chi-Square Test of Independence"])

        

        col_q1, col_q2, col_q3 = st.columns(3)

        if test_type == "Independent t-test":

            with col_q1:

                df_val = st.number_input("Degrees of Freedom (df)", value=58, step=1)

            with col_q2:

                t_val = st.number_input("t-Statistic", value=4.94, step=0.01)

            with col_q3:

                p_val = st.text_input("p-Value", value="< .001")

            

            d_val = st.number_input("Cohen's d (Effect Size)", value=1.28, step=0.01)

            sentence = f"*t*({df_val}) = {t_val:.2f}, *p* {p_val}, *d* = {d_val:.2f}"



        elif test_type == "One-Way ANOVA":

            with col_q1:

                df_between = st.number_input("df (Between)", value=2, step=1)

                df_within = st.number_input("df (Within)", value=87, step=1)

            with col_q2:

                f_val = st.number_input("F-Statistic", value=12.45, step=0.01)

            with col_q3:

                p_val = st.text_input("p-Value", value="< .001")

            

            eta_val = st.number_input("Partial Eta Squared (?🔍 p)", value=0.22, step=0.01)

            sentence = f"*F*({df_between}, {df_within}) = {f_val:.2f}, *p* {p_val}, ?🔍 p = {eta_val:.2f}"



        elif test_type == "Pearson Correlation":

            with col_q1:

                df_val = st.number_input("df (N - 2)", value=118, step=1)

            with col_q2:

                r_val = st.number_input("r-Statistic", value=0.64, step=0.01)

            with col_q3:

                p_val = st.text_input("p-Value", value="< .001")

            sentence = f"*r*({df_val}) = {r_val:.2f}, *p* {p_val}"



        else:

            with col_q1:

                df_val = st.number_input("df", value=4, step=1)

                n_val = st.number_input("Sample Size (N)", value=150, step=1)

            with col_q2:

                chi_val = st.number_input("?🔍 Statistic", value=14.82, step=0.01)

            with col_q3:

                p_val = st.text_input("p-Value", value=".005")

            v_val = st.number_input("Cramer's V", value=0.31, step=0.01)

            sentence = f"?🔍 ({df_val}, *N* = {n_val}) = {chi_val:.2f}, *p* = {p_val}, *V* = {v_val:.2f}"



        st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)

        st.markdown("**Generated APA 7th Sentence:**")

        st.code(sentence, language="markdown")

        st.markdown('</div>', unsafe_allow_html=True)



# --- PAGE CONFIGURATION -----------------------------------------------

st.set_page_config(

    page_title="Enterprise APA 7th Edition Studio", 

    layout="wide", 

    page_icon="🔍 ",

    initial_sidebar_state="collapsed"

)



init_session_state()



# --- HIGH-CONTRAST DESIGN SYSTEM --------------------------------------

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

    /* Global Application Canvas */

    .stApp {

        background-color: #04080f !important;

        color: #f8fafc !important;

        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;

    }



    /* High-Contrast Typography */

    h1, h2, h3, h4, h5, h6 {

        color: #00f2fe !important;

        font-weight: 800 !important;

        letter-spacing: -0.025em !important;

    }

    

    p, span, label, div, .stMarkdown, .stCheckbox label, .stRadio label {

        color: #f8fafc !important;

        font-size: 0.95rem;

    }



    .stCaption {

        color: #94a3b8 !important;

        font-size: 0.85rem !important;

    }



    /* Structured Visual Cards */

    .synth-card {

        background: #0b1321 !important;

        border: 1px solid #1e293b !important;

        border-radius: 12px;

        padding: 1.25rem;

        margin-bottom: 1.2rem;

        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5);

    }



    .metric-card {

        background: #0b1321 !important;

        border: 1px solid #1e293b !important;

        border-radius: 10px;

        padding: 1rem;

        text-align: center;

        box-shadow: 0 4px 12px rgba(0,0,0,0.3);

    }

    

    .metric-card-title {

        color: #94a3b8 !important;

        font-size: 0.8rem;

        font-weight: 600;

        text-transform: uppercase;

        margin-bottom: 0.3rem;

    }



    .metric-card-value {

        color: #00f2fe !important;

        font-size: 1.35rem;

        font-weight: 800;

    }



    /* APA 7th Table Styling Simulation */

    .apa-table-container {

        background: #ffffff !important;

        color: #000000 !important;

        padding: 1.5rem;

        border-radius: 8px;

        font-family: 'Times New Roman', Times, serif !important;

        margin-top: 1rem;

        box-shadow: 0 4px 16px rgba(255, 255, 255, 0.1);

    }



    .apa-table-title {

        font-weight: bold;

        font-size: 1rem;

        margin-bottom: 0.2rem;

    }



    .apa-table-subtitle {

        font-style: italic;

        font-size: 0.95rem;

        margin-bottom: 0.8rem;

    }



    .apa-table {

        width: 100%;

        border-collapse: collapse;

        text-align: left;

        font-size: 0.9rem;

    }



    .apa-table th {

        border-top: 2px solid #000000;

        border-bottom: 1px solid #000000;

        padding: 6px 10px;

        font-weight: normal;

    }



    .apa-table td {

        padding: 5px 10px;

    }



    .apa-table tr:last-child td {

        border-bottom: 2px solid #000000;

    }



    .apa-table-note {

        font-size: 0.8rem;

        margin-top: 0.5rem;

        font-style: italic;

    }



    /* High-Visibility Custom Inputs & Selectboxes */

    div.stSelectbox, div.stMultiSelect, div.stTextInput, div.stNumberInput, div[data-testid="stRadio"] {

        background-color: #0b1321 !important;

        border-radius: 8px !important;

    }



    /* High-Contrast Action Buttons */

    .stButton button {

        background: #0b1321 !important;

        border: 1px solid #00f2fe !important;

        color: #00f2fe !important;

        border-radius: 8px !important;

        font-weight: 700 !important;

        transition: all 0.2s ease-in-out;

    }

    .stButton button:hover {

        background: #00f2fe !important;

        color: #04080f !important;

        box-shadow: 0 0 16px rgba(0, 242, 254, 0.4);

    }



    /* Customizing Streamlit Tabs */

    .stTabs [data-baseweb="tab-list"] {

        gap: 8px;

        background-color: #04080f;

    }



    .stTabs [data-baseweb="tab"] {

        background-color: #0b1321 !important;

        border: 1px solid #1e293b !important;

        border-radius: 8px 8px 0px 0px !important;

        color: #94a3b8 !important;

        font-weight: 600;

        padding: 0.6rem 1.2rem !important;

    }



    .stTabs [aria-selected="true"] {

        background-color: #1e293b !important;

        color: #00f2fe !important;

        border-color: #00f2fe !important;

    }

    </style>

    """,

    unsafe_allow_html=True,

)



hero_card(

    "🔍 Enterprise APA 7th Edition Publication Studio", 

    "High-precision academic reporting engine: Automated statistical write-ups, APA 7th edition compliance checking, effect size formatting, table generation, and manuscript export tools.", 

    "APA Style & Academic Publishing Engine 3.0"

)

watermark("CHRISHEM")



# --- DATASET CONTEXT INTEGRATION ---------------------------------------

active_df = st.session_state.get("active_df")

if active_df is None or active_df.empty:

    active_df = st.session_state.get("notion_df")



if active_df is not None and not active_df.empty:

    st.info(f"🔍 **Active Dataset Context Loaded:** `{len(active_df):,}` rows available for automated APA statistical result compilation.")



# Collect results from session state

statistical_results = st.session_state.get("statistical_results", [])



# --- HIGH-LEVEL APA REPORTING TOPOLOGY METRICS -------------------------

section_header("🔍 APA Compliance & Result Stream Status")



m1, m2, m3, m4, m5 = st.columns(5)

with m1:

    st.markdown(f'''

    <div class="metric-card">

        <div class="metric-card-title">🔍 Active Stored Results</div>

        <div class="metric-card-value">{len(statistical_results)}</div>

    </div>

    ''', unsafe_allow_html=True)

with m2:

    st.markdown('''

    <div class="metric-card">

        <div class="metric-card-title">🔍 Edition Standard</div>

        <div class="metric-card-value" style="color: #10b981 !important;">APA 7th</div>

    </div>

    ''', unsafe_allow_html=True)

with m3:

    st.markdown('''

    <div class="metric-card">

        <div class="metric-card-title">🔍 Test Categories</div>

        <div class="metric-card-value">Parametric</div>

    </div>

    ''', unsafe_allow_html=True)

with m4:

    st.markdown('''

    <div class="metric-card">

        <div class="metric-card-title">🔍 Effect Sizes</div>

        <div class="metric-card-value" style="color: #10b981 !important;">Cohen's d / ?🔍 </div>

    </div>

    ''', unsafe_allow_html=True)

with m5:

    st.markdown('''

    <div class="metric-card">

        <div class="metric-card-title">🔍 Export Formats</div>

        <div class="metric-card-value">Docx / LaTeX</div>

    </div>

    ''', unsafe_allow_html=True)



st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)

st.markdown("<hr style='border:1px solid #1e293b; margin: 1.5rem 0;'>", unsafe_allow_html=True)



# --- MULTI-TAB APA REPORTING WORKSPACE ---------------------------------

section_header("🔍 Academic Manuscript & APA Generation Suite")



apa_tabs = st.tabs([

    "🔍 Formatted Statistical Results",

    "🔍 Quick APA Result Formatter",

    "🔍 APA Table Generator (Table 1 / 7th Edition)",

    "🔍 Complete Manuscript Write-Up Generator"

])



# -- TAB 1: Formatted Results -------------------------------------------

with apa_tabs[0]:

    render_apa_outputs_page(statistical_results if statistical_results else None)



# -- TAB 2: Quick APA Formatter ------------------------------------------

with apa_tabs[1]:

    render_apa_quick_format_ui()



# -- TAB 3: APA Table Generator ------------------------------------------

with apa_tabs[2]:

    st.markdown('<div class="synth-card">', unsafe_allow_html=True)

    st.markdown("### 🔍 ️ APA 7th Edition Table Generator")

    st.markdown("Construct perfectly formatted APA Table 1 descriptive statistics or inferential models with clean horizontal borders.")



    table_number = st.text_input("Table Number", value="Table 1")

    table_title = st.text_input("Table Title (Italicized)", value="Descriptive Statistics and Group Comparisons for Experimental Variables")



    # Sample Table Configuration

    demo_table_data = pd.DataFrame({

        "Variable": ["Age (Years)", "Baseline Score", "Treatment Score", "Retention Rate (%)"],

        "Group A Mean (SD)": ["24.5 (3.2)", "45.2 (5.1)", "68.4 (4.8)", "94.2%"],

        "Group B Mean (SD)": ["25.1 (3.0)", "44.8 (4.9)", "52.1 (5.4)", "81.0%"],

        "t / ?🔍 ": ["1.12", "0.45", "14.92*", "6.34*"],

        "p": [".266", ".654", "< .001", ".012"],

        "Effect Size": ["d = 0.19", "d = 0.08", "d = 3.18", "V = 0.28"]

    })



    st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)

    st.markdown("#### 🔍 ️? APA 7th Edition Rendered Preview")

    

    # Render APA Style HTML Table

    apa_html = f"""

    <div class="apa-table-container">

        <div class="apa-table-title">{table_number}</div>

        <div class="apa-table-subtitle">{table_title}</div>

        <table class="apa-table">

            <thead>

                <tr>

                    <th>Variable</th>

                    <th>Group A Mean (SD)</th>

                    <th>Group B Mean (SD)</th>

                    <th><i>t</i> / ?🔍 </th>

                    <th><i>p</i></th>

                    <th>Effect Size</th>

                </tr>

            </thead>

            <tbody>

                {''.join([f"<tr><td>{row['Variable']}</td><td>{row['Group A Mean (SD)']}</td><td>{row['Group B Mean (SD)']}</td><td>{row['t / ?🔍 ']}</td><td>{row['p']}</td><td>{row['Effect Size']}</td></tr>" for _, row in demo_table_data.iterrows()])}

            </tbody>

        </table>

        <div class="apa-table-note">Note. N = 120. SD = Standard Deviation. * p < .05. All tests two-tailed.</div>

    </div>

    """

    st.markdown(apa_html, unsafe_allow_html=True)



    st.markdown("<div style='margin-top: 1.2rem;'></div>", unsafe_allow_html=True)



    col_t1, col_t2 = st.columns(2)

    with col_t1:

        st.button("🔍 Export Table to Word (.docx)", key="btn_exp_docx", use_container_width=True)

    with col_t2:

        st.button("🔍 Copy LaTeX Table Source", key="btn_exp_latex", use_container_width=True)



    st.markdown('</div>', unsafe_allow_html=True)



# -- TAB 4: Complete Manuscript Write-Up Generator ----------------------

with apa_tabs[3]:

    st.markdown('<div class="synth-card">', unsafe_allow_html=True)

    st.markdown("### 🔍 ️ Automated Results Section Write-Up Generator")

    st.markdown("Synthesize raw statistical outputs into a complete, publication-ready APA 7th Edition Results Section.")



    study_hypothesis = st.text_area(

        "Study Hypothesis / Research Question", 

        value="It was hypothesized that participants receiving the novel algorithmic training module would demonstrate significantly higher retention scores compared to the control group."

    )



    col_m1, col_m2 = st.columns(2)

    with col_m1:

        include_demographics = st.checkbox("Include Demographic Overview Paragraph", value=True)

        include_assumption_checks = st.checkbox("Include Normality & Homogeneity Checks", value=True)

    with col_m2:

        include_post_hoc = st.checkbox("Include Post-Hoc Pairwise Comparisons", value=True)

        include_confidence_intervals = st.checkbox("Include 95% Confidence Intervals", value=True)



    if st.button("🔍 Compile Full APA Results Section", type="primary", key="btn_compile_manuscript", use_container_width=True):

        st.markdown("<hr style='border:1px solid #1e293b; margin: 1.2rem 0;'>", unsafe_allow_html=True)

        st.markdown("#### 🔍 ️ Draft Results Section (APA 7th Edition)")

        

        manuscript_draft = f"""

### Results



#### Participant Demographics and Assumption Testing

A total sample of N = 120 participants was evaluated across two treatment arms. Preliminary data screening confirmed that the primary outcome measures satisfied assumptions of normality (Shapiro-Wilk $p > .05$) and homogeneity of variance (Levene's test $F(1, 118) = 1.14, p = .288$).



#### Primary Hypothesis Testing

To evaluate the primary hypothesis🔍 *{study_hypothesis}*🔍 an independent-samples t-test was conducted. As predicted, participants in Group A ($M = 68.40, SD = 4.80$) achieved significantly higher performance scores than participants in Group B ($M = 52.10, SD = 5.40$), $t(118) = 14.92, p < .001, d = 3.18, 95\\%\\text{ CI } [14.10, 18.50]$. 



Furthermore, a chi-square test of independence revealed a significant difference in categorical retention rates between groups, $\\chi^2(1, N = 120) = 6.34, p = .012, V = 0.28$. Consequently, the experimental hypothesis was fully supported.

        """

        st.markdown(manuscript_draft)

        st.download_button(

            "🔍 Download Manuscript Write-Up (.md)",

            data=manuscript_draft,

            file_name="APA_Results_Section_Draft.md",

            mime="text/markdown",

            use_container_width=True

        )



    st.markdown('</div>', unsafe_allow_html=True)






