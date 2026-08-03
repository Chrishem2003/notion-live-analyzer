import security_guard
mport streamlit as st

def verify_access():
    if not st.session_state.get('portal_unlocked', False):
        st.error('?? Access Denied: Please authenticate through the Main Gateway Portal first.')
        if st.button('?? Return to Login Portal'):
            st.switch_page('app.py')
        st.stop()

