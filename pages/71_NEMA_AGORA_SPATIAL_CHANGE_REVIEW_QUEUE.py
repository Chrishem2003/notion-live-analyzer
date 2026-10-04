"""Phase 63 — NEMA-AGORA persistent spatial-change review queue demo."""
import tempfile
import streamlit as st
from nema_agora.spatial_change_review_queue import SpatialChangeReviewQueue
st.set_page_config(page_title="NEMA-AGORA Spatial Review Queue",layout="wide")
st.title("NEMA-AGORA — Persistent Spatial Change Review Queue")
st.caption("Phase 63 • append-only analytical review records")
candidate={"state":"REVIEW_PRIORITY_ASSIGNED","candidate_id":"CHANGE-DEMO-001","source_candidate_fingerprint":"a"*64,
"score":0.82,"tier":"HIGH","components":{"ndvi_magnitude":0.8,"ndwi_magnitude":0.6,"quality":0.9,"uncertainty":0.96},
"weights":{"ndvi":0.5,"ndwi":0.5,"quality":0.0,"uncertainty":0.0},"review_threshold":0.5,
"reason_codes":["NDVI_CHANGE_THRESHOLD_MET","NDWI_CHANGE_THRESHOLD_MET","COMBINED_CHANGE_SIGNAL"],
"spatial":{"aoi_id":"DEMO-WETLAND-01","grid_id":"DEMO-GRID-10M"}}
if "phase63_db" not in st.session_state:
    st.session_state.phase63_db=tempfile.NamedTemporaryFile(suffix=".sqlite",delete=False).name
q=SpatialChangeReviewQueue(st.session_state.phase63_db)
if st.button("Enqueue synthetic candidate"):
    try: q.enqueue(candidate); st.success("Candidate persisted as immutable QUEUED review record.")
    except ValueError as exc: st.warning(str(exc))
rows=q.list()
c1,c2,c3=st.columns(3)
c1.metric("Queue items",len(rows)); c2.metric("Queued",sum(x["queue_state"]=="QUEUED" for x in rows)); c3.metric("Human review required",sum(x["human_review_required"] for x in rows))
if rows: st.dataframe(rows,use_container_width=True)
st.json(candidate)
st.warning("This queue records analytical candidates for human review. It does not decide illegality, environmental truth, enforcement, emergency response, NEMA authorisation or production approval. Queue records are append-only; review decisions require a separate human-governed workflow.")
