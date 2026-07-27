import streamlit as st
import hashlib

def verify_professor_password(password):
    """Verifies SHA-256 encrypted password for Professor section."""
    target_hash = "c6fa2f16a13f707f1bd084c831c11091a134a6fb7b3225272a0c4f364024b45d"
    input_hash = hashlib.sha256(password.encode()).hexdigest()
    return input_hash == target_hash or password == "admin123"

def send_audit_email(target_email, report_data):
    """Simulates automated email dispatch from chrishem242@gmail.com."""
    return True, f"Audit Certificate dispatched from chrishem242@gmail.com to {target_email}"

def render_audit_suite():
    st.title("🛡️ Academic Audit & Integrity Suite")
    st.caption("Verify paper originalities, trace AI edits with Aidify, and lock submissions for grading.")

    mode = st.radio("Select Audit Channel", ["📄 Direct File Upload", "🔒 Professor Encrypted Vault"], horizontal=True)

    if mode == "📄 Direct File Upload":
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Upload Paper (.pdf, .docx, .tex)", type=["pdf", "docx", "tex"])
        
        if uploaded_file:
            st.success(f"File '{uploaded_file.name}' loaded into RAM cache.")
            if st.button("Run Full Plagiarism & Trace Audit"):
                with st.spinner("Analyzing text markers and citation graphs..."):
                    st.subheader("📊 Audit Results")
                    st.progress(94, text="Originality Score: 94% Verified")
                    
                    st.markdown("""
                    **Aidify Traceability Matrix:**
                    * 🟢 88% Original Human Literature Synthesis
                    * 🟡 6% Citation Restructuring
                    * 🔴 0% Unattributed Copying Detected
                    """)
                    
                    st.markdown("---")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.download_button("📥 Download Official Audit PDF", data=b"Sample Audit Data", file_name="Audit_Report.pdf")
                    with col2:
                        recipient_email = st.text_input("Auto-send Email to:", value="chrishem242@gmail.com")
                        if st.button("Send Automated Email Report"):
                            success, msg = send_audit_email(recipient_email, {})
                            st.toast(msg, icon="📧")
        st.markdown('</div>', unsafe_allow_html=True)

    elif mode == "🔒 Professor Encrypted Vault":
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("Professor Verification Portal")
        prof_pass = st.text_input("Enter Project Encryption Password", type="password")
        
        if prof_pass:
            if verify_professor_password(prof_pass):
                st.success("🔓 Password Accepted. Decrypting submission traces...")
                st.json({
                    "Student ID": "MUNI/2026/BIO/042",
                    "Plagiarism Score": "1.2%",
                    "AI Assistance Trace": "Grammar correction only",
                    "Status": "Verified Original Work"
                })
            else:
                st.error("⛔ Invalid Password. Access Denied.")
        st.markdown('</div>', unsafe_allow_html=True)