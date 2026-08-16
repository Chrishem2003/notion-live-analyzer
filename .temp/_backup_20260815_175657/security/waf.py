
import re
import streamlit as st

def sanitize_payload(user_input: str) -> str:
    """
    Intercepts and neutralizes malicious patterns (SQL injection, XSS vectors).
    """
    if not isinstance(user_input, str):
        return str(user_input)
    
    # Detect potential SQLi or script injection signatures
    sql_patterns = re.compile(r"(--|;|UNION|SELECT|DROP|INSERT|DELETE|UPDATE|OR\s1=1)", re.IGNORECASE)
    xss_patterns = re.compile(r"(<script>|javascript:|onerror=|onload=)", re.IGNORECASE)
    
    if sql_patterns.search(user_input) or xss_patterns.search(user_input):
        with open("security_audit.log", "a") as f:
            f.write(f"Threat Blocked: Malicious payload signature matched -> {user_input}\n")
        st.error("SECURITY ALERT: Malicious payload intercepted by CHRISHEM Firewall.")
        st.stop()
        
    return user_input
