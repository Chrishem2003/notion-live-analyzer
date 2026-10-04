"""NEMA-AGORA Phase 20 - Evidence Provenance."""
from __future__ import annotations
import pandas as pd
import streamlit as st
from nema_agora.access import has_permission
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.config import database_path_from_secrets, mode_from_secrets
from nema_agora.provenance import EVENT_TYPES, verify_provenance_chain
from nema_agora.service import NemaAgoraService
from nema_agora.storage import NemaAgoraRepository

st.set_page_config(page_title="NEMA-AGORA Provenance", page_icon="🔗", layout="wide")
st.title("🔗 NEMA-AGORA — Evidence Provenance")
st.caption("Phase 20 — reproducibility and evidence lineage")
st.warning("Provenance records describe evidence lineage. They do not establish environmental truth, regulatory status, NEMA authorization, enforcement authority, or production approval.")

mode=mode_from_secrets(st.secrets)
principal=principal_from_streamlit_user(st.user, st.secrets) if mode=="persistent" else None
db_path=database_path_from_secrets(st.secrets) if mode=="persistent" else None
service=NemaAgoraService(NemaAgoraRepository(db_path)) if principal and principal.is_authorised and db_path else None
if not service:
    st.info("Authenticate in persistent mode to inspect provenance.")
    st.stop()
if not has_permission(principal.role, "intelligence:provenance"):
    st.error("Your role cannot inspect provenance.")
    st.stop()

event_type=st.selectbox("Evidence type", ["ALL"]+list(EVENT_TYPES))
event_id=st.text_input("Event ID (optional)")
records=service.list_provenance(principal,event_type=None if event_type=="ALL" else event_type,event_id=event_id or None,limit=500)
st.metric("Provenance records",len(records))
if records:
    st.dataframe(pd.DataFrame(records),use_container_width=True,hide_index=True)
    st.subheader("Chain verification")
    result=verify_provenance_chain(records)
    st.json(result)
    if result["valid"]: st.success("The displayed provenance set has no missing parent references or duplicate event identities.")
    else: st.error("Provenance chain verification found a consistency problem.")
else:
    st.info("No provenance records match the selected filter.")

st.caption("Phase 20 is an evidence-lineage layer. It is intentionally descriptive and does not turn records into environmental or regulatory truth.")
