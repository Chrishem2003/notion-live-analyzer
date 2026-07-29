st.markdown("<style>.stApp{background-color:#0d1117!important;color:#f0f6fc!important;}h1,h2,h3,h4,h5,h6,span,p,label,.stMarkdown,.stCaption{color:#f0f6fc!important;}</style>",unsafe_allow_html=True)

import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Access Control & Licensing", page_icon="🔐", layout="wide")
st.subheader("🔐 Sovereign Access Control & Tiered Licensing Hub")
st.caption("Manage secure user licenses, African student verification portals, and administrative privileges.")

if "user_email" not in st.session_state:
    st.session_state.user_email = "chrishem242@gmail.com"
if "user_tier" not in st.session_state:
    st.session_state.user_tier = "Master Admin"
if "student_verified" not in st.session_state:
    st.session_state.student_verified = True

col1, col2, col3 = st.columns(3)
with col1:
    email = st.text_input("User Email Address", value=st.session_state.user_email)
    if email != st.session_state.user_email:
        st.session_state.user_email = email
        if email.strip().lower() == "chrishem242@gmail.com":
            st.session_state.user_tier = "Master Admin"
            st.session_state.student_verified = True
        else:
            st.session_state.user_tier = "Free (Unverified)"
        st.rerun()
with col2:
    st.text_input("Assigned Access Tier", value=st.session_state.user_tier, disabled=True)
with col3:
    status = "Verified (Admin)" if st.session_state.student_verified else "Pending ID Verification"
    st.text_input("Verification Status", value=status, disabled=True)

st.markdown("---")
if st.session_state.user_tier != "Master Admin":
    st.markdown("### 🌍 African Student Free Access Verification Portal")
    with st.form("student_verify_form"):
        country = st.selectbox("African Country", ["Uganda", "Kenya", "Tanzania", "Rwanda", "Nigeria", "Ghana", "South Africa", "Other"])
        institution = st.text_input("Institution Name", value="Muni University")
        student_id = st.text_input("Student ID Number")
        nat_front = st.file_uploader("National ID (Front Scan)", type=["png", "jpg", "jpeg", "pdf"])
        nat_back = st.file_uploader("National ID (Back Scan)", type=["png", "jpg", "jpeg", "pdf"])
        uni_front = st.file_uploader("University ID (Front Scan)", type=["png", "jpg", "jpeg", "pdf"])
        uni_back = st.file_uploader("University ID (Back Scan)", type=["png", "jpg", "jpeg", "pdf"])
        
        if st.form_submit_button("Submit Credentials"):
            if nat_front and nat_back and uni_front and uni_back and student_id:
                st.session_state.student_verified = True
                st.session_state.user_tier = "Standard (Verified Student)"
                st.success("Verification Successful! Upgraded to Free Standard Access.")
                st.rerun()
            else:
                st.error("Please upload all 4 required ID documents and enter your student ID number.")

if st.session_state.user_email.strip().lower() == "chrishem242@gmail.com":
    st.markdown("### 👑 Master Admin Enclave")
    users_df = pd.DataFrame([
        {"Identity": "Master Administrator", "Role": "Master Admin", "Tier": "Apex Sovereign", "Status": "Active"},
        {"Identity": "Muni Research Cohort", "Role": "African Student", "Tier": "Standard (Verified)", "Status": "Active"}
    ])
    st.dataframe(users_df, use_container_width=True)
