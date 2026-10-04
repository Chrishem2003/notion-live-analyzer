"""NEMA-AGORA Phase 24 — Evidence Observatory."""
import streamlit as st
from nema_agora.access import has_permission
from nema_agora.auth import principal_from_streamlit_user
from nema_agora.config import database_path_from_secrets, mode_from_secrets
from nema_agora.evidence import build_scorecard, fingerprint_scorecard
from nema_agora.impact import ImpactStore
from nema_agora.accessibility import AccessibilityStore
from nema_agora.provenance import ProvenanceStore
from nema_agora.field_eval import FieldEvaluationStore

st.set_page_config(page_title="NEMA-AGORA Evidence Observatory",page_icon="🧭",layout="wide")
st.title("🧭 NEMA-AGORA — Evidence Observatory")
st.caption("A transparent engineering/research evidence dashboard.")

st.warning("The scorecard measures evidence coverage and system behaviour. It is not environmental impact, environmental truth, regulatory status, NEMA authorization, or production approval.")

if mode_from_secrets(st.secrets)!="persistent":
    st.info("Persistent authenticated mode is required."); st.stop()
principal=principal_from_streamlit_user(st.user,st.secrets)
if not principal or not principal.is_authorised:
    st.error("Authenticated provisioned access is required."); st.stop()
if not has_permission(principal.role,"intelligence:evidence"):
    st.error("Your role cannot access the Evidence Observatory."); st.stop()

db=database_path_from_secrets(st.secrets)
impact=len(ImpactStore(db).list())
accessibility=len(AccessibilityStore(db).list())
provenance=len(ProvenanceStore(db).list())
field=len(FieldEvaluationStore(db).list())
try:
    from nema_agora.review_governance import ReviewStore
    reviews=len(ReviewStore(db).list_reviews())
except Exception:
    reviews=0

score=build_scorecard(impact_count=impact,accessibility_count=accessibility,
    provenance_count=provenance,field_evaluation_count=field,human_review_count=reviews)

c1,c2,c3=st.columns(3)
c1.metric("Evidence coverage",f"{score.overall_coverage:.0%}")
c2.metric("Evidence domains",len(score.domain_scores))
c3.metric("Warnings",len(score.warnings))

st.subheader("Domain coverage")
for domain,value in score.domain_scores.items():
    st.progress(value,text=f"{domain.replace('_',' ').title()}: {value:.0%}")

st.subheader("Evidence counts")
st.json(score.evidence_counts)

if score.warnings:
    st.subheader("Evidence gaps")
    for warning in score.warnings: st.warning(warning)

st.subheader("Reproducibility fingerprint")
st.code(fingerprint_scorecard(score))
st.caption(score.decision_notice)
