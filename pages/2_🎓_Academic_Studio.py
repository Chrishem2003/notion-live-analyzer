import streamlit as st
from datetime import datetime

st.set_page_config(page_title="Academic & CV Studio", page_icon="🎓", layout="wide")
st.subheader("🎓 Academic, CV & Portfolio Writing Studio")
st.caption("AI-powered professional drafting engine with instant downloadable document export.")

mode = st.selectbox("Select Writing Target:", ["Professional CV & Profile Summary", "Academic Research Abstract & Report", "Project Portfolio Description", "Formal Cover Letter"])

st.markdown("---")
if mode == "Professional CV & Profile Summary":
    col1, col2 = st.columns(2)
    with col1:
        full_name = st.text_input("Full Name", value="Kula Chris (Chrishem)")
        field = st.text_input("Core Discipline", value="Biological Sciences & Data Analytics")
    with col2:
        tier = st.selectbox("Experience Tier", ["Undergraduate Researcher & Student", "Junior Data Analyst"])
        target = st.text_input("Target Role", value="Bioinformatics & Data Analytics Intern")

    if st.button("✨ Generate CV Summary"):
        content = f\"\"\"# Professional Profile: {full_name}
* **Discipline:** {field} ({tier})
* **Target Position:** {target}
* **Generated On:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary
Motivated undergraduate student in the Faculty of Science with rigorous training in biological sciences, data analytics, and computational pipelines.
\"\"\"
        st.markdown(content)
        st.download_button("📥 Download Markdown (.md)", content, "Chrishem_CV.md", "text/markdown")
        st.download_button("📥 Download Text (.txt)", content, "Chrishem_CV.txt", "text/plain")
else:
    st.info("Select your desired writing target above to generate customized documents instantly.")
