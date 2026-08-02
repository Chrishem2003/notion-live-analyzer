import streamlit as st

# Initialize unlock state
if 'portal_unlocked' not in st.session_state:
    st.session_state.portal_unlocked = False

# If locked, render the portal gateway
if not st.session_state.portal_unlocked:
    with open('portal.py', 'r', encoding='utf-8-sig') as f:
        code = f.read()
    exec(code)
    st.stop()
else:
    # If unlocked, display a clean dashboard hub on the main page 
    # while letting Streamlit show the sidebar pages normally.
    st.title('? Chrishem Sovereign Apex Hub')
    st.success('?? Gateway Unlocked: Select any module from the sidebar navigation to begin.')
    
    identity = st.session_state.get('user_identity', {})
    st.info(f"**Active Session:** {identity.get('name', 'Analyst')} ({identity.get('role', 'User')})")
    
    if st.button('?? Lock Portal & Sign Out'):
        st.session_state.portal_unlocked = False
        st.rerun()
