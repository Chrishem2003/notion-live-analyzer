"""NEMA-AGORA Phase 42 — Closure Evidence & Provenance."""
import streamlit as st
from nema_agora.access import has_permission
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.config import database_path_from_secrets, mode_from_secrets
from nema_agora.closure_evidence import reconcile_with_evidence

st.set_page_config(page_title='NEMA-AGORA Closure Evidence',page_icon='⌘',layout='wide')
st.title('NEMA-AGORA — Closure Evidence & Provenance')
st.caption('Phase 42-v1 • evidence registry, provenance binding, operational reconciliation')
st.info('Authenticated read-only governance surface. Evidence supports closure evaluation; evidence presence never silently closes an exception.')
if mode_from_secrets(st.secrets)!='persistent': st.warning('Persistent authenticated mode is required.'); st.stop()
principal=principal_from_streamlit_user(st.user,st.secrets)
if not principal or not principal.is_authorised or principal.role not in {'reviewer','coordinator','admin'} or not has_permission(principal.role,'audit:read'):
    st.error('Authorized reviewer, coordinator, or admin access is required.'); st.stop()
try:
    result=reconcile_with_evidence(database_path_from_secrets(st.secrets))
except Exception as exc:
    st.error(f'Phase 42 evaluation failed closed: {exc}'); st.stop()
report=result['report']; closure=result['closure']
if report['control_required'] or report['unresolved_critical']: st.error('Human control is required for one or more unresolved governance exceptions.')
elif report['review_required']: st.warning('Human review is required before any closure can be accepted.')
else: st.success('No unresolved governance exception requires review or control under the current derived state.')
cols=st.columns(6)
for col,label,value in zip(cols,['Exceptions','Open','Review','Control','Closed','Stale resolutions'],[report['total_exceptions'],report['open'],report['review_required'],report['control_required'],report['closed'],report['stale_resolutions']]): col.metric(label,value)
st.subheader('Operational reconciliation'); st.dataframe([report],use_container_width=True,hide_index=True)
st.subheader('Provenance chain'); st.code(closure['provenance_chain'])
st.subheader('Closure results'); st.dataframe(closure['results'],use_container_width=True,hide_index=True)
st.subheader('Closure evidence registry')
if result['evidence']: st.dataframe(result['evidence'],use_container_width=True,hide_index=True)
else: st.info('No closure evidence is registered.')
st.caption(report['decision_notice'])
