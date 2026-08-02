import streamlit as st

# Initialize session state flags if not present
if 'portal_unlocked' not in st.session_state:
    st.session_state.portal_unlocked = False

# Execute the portal login interface if locked
if not st.session_state.portal_unlocked:
    with open('portal.py', 'r', encoding='utf-8-sig') as f:
        code = f.read()
    exec(code)
    st.stop()
else:
    # Once unlocked, load standard multipage navigation
    st.switch_page('pages/1_?_Apex_Overview.py') # Or let Streamlit render the sidebar pages normally

