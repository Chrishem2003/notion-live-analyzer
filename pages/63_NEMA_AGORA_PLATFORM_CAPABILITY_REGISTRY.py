"""NEMA-AGORA Phase 55 — Platform Capability Registry."""
import streamlit as st
from nema_agora.platform_capability_registry import validate_capabilities
st.set_page_config(page_title="NEMA-AGORA Capability Registry",layout="wide")
st.title("NEMA-AGORA — Platform Capability Registry")
st.caption("Phase 55-v1 • roadmap-to-implementation control")
result=validate_capabilities()
st.metric("Capabilities",result["capability_count"]); st.metric("Registry state",result["state"])
st.dataframe(result["capabilities"],use_container_width=True)
st.subheader("Findings"); st.json(result["findings"])
st.caption("Planning and architecture evidence only. No capability status authorizes NEMA integration, enforcement, emergency response, production use or autonomous environmental decisions.")
