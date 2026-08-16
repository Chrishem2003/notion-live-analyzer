"""
Page 60 — Multi-Agent Swarm & Async Task Console
Unifies: agents.py (multi-agent swarm), tasks.py (async runner),
rag_engine.py (hybrid RAG), self_correcting_executor.py (LLM self-correction).
"""
import sys
from pathlib import Path

import streamlit as st

current_file = Path(__file__).resolve()
root_dir = current_file.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

st.set_page_config(page_title="Agent Swarm & Task Console", page_icon="🦾", layout="wide")

import pandas as pd  # noqa: E402


def _hero(title, subtitle, badge):
    st.markdown(
        f"""
        <div style="padding:1.6rem;background:linear-gradient(135deg,rgba(245,158,11,.12),rgba(11,19,33,.96));border-radius:14px;border:1px solid rgba(245,158,11,.35);margin-bottom:1.2rem;">
            <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.5rem;">
                <h1 style="color:#f59e0b !important;font-size:1.9rem;margin:0;font-weight:800;">{title}</h1>
                <span style="background:rgba(245,158,11,.15);color:#f59e0b;padding:.3rem .8rem;border-radius:999px;font-size:.75rem;font-weight:700;border:1px solid #f59e0b;">{badge}</span>
            </div>
            <p style="color:#cbd5e1 !important;margin:.4rem 0 0;font-size:.95rem;">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


_hero(
    "🦾 Multi-Agent Problem-Solver Swarm & Async Task Console",
    "Orchestrate a collaborative 3-persona agent swarm (Research & Literature • Data & Technical Auditor • Synthesis & Strategy), run long tasks asynchronously with live progress, query hybrid Graph+Vector RAG, and execute self-correcting analysis code.",
    "LangGraph-Style Agent Orchestration",
)

tab1, tab2, tab3, tab4 = st.tabs([
    "🧠 Agent Swarm Console",
    "⚙️ Async Task Runner",
    "🔎 Hybrid RAG Query",
    "🛠️ Self-Correcting Executor",
])

# ─────────────────────────────────────────────────────────────────────
# TAB 1: Agent Swarm
# ─────────────────────────────────────────────────────────────────────
with tab1:
    st.markdown("### 🧠 3-Persona Agent Swarm Orchestration")
    challenge = st.text_area(
        "Describe a complex multi-sector challenge",
        value="Design a drought-resilient agricultural strategy for smallholder farmers in East Africa, integrating climate data and crop-science literature.",
        height=120,
    )
    col_a, col_b = st.columns(2)
    with col_a:
        sector = st.text_input("Sector", value="Agriculture & Food Security")
    with col_b:
        country = st.text_input("Country / Region", value="East Africa")
    papers_limit = st.slider("Max papers to retrieve", 5, 50, 15, 5)
    if st.button("🚀 Deploy Agent Swarm", type="primary", use_container_width=True):
        try:
            from agents import run_agent_swarm

            bar = st.progress(0, text="Spawning agent swarm...")

            def cb(p, m=""):
                bar.progress(int(p), text=m)

            result = run_agent_swarm(
                query=challenge, sector=sector, country=country,
                papers_limit=papers_limit, progress_cb=cb,
            )
            bar.progress(100, text="Swarm complete — report ready")

            literature = result.get("literature", {})
            data_audit = result.get("data_audit", {})
            synthesis = result.get("synthesis", {})

            c1, c2, c3 = st.columns(3)
            c1.metric("Research Agent", f"{literature.get('count', 0)} papers", delta=literature.get("source", "OK"))
            c2.metric("Data Auditor", f"{data_audit.get('audit_count', 0)} records", delta=f"{data_audit.get('sector', '')}")
            c3.metric("Run ID", result.get("run_id", "—"))

            st.markdown("### 🔬 Research & Literature Specialist")
            st.info(f"Source: {literature.get('source', 'simulated')}")
            for c in literature.get("citations", [])[:5]:
                st.markdown(f"- {c}")

            st.markdown("### 📊 Data & Technical Auditor")
            for r in data_audit.get("records", [])[:8]:
                st.markdown(f"- {r}")

            st.markdown("### 🧭 Synthesis & Strategy Architect")
            st.markdown(synthesis.get("action_plan", "No plan generated."))
            st.caption(f"Priority: {synthesis.get('priority', 'STANDARD')}")

            with st.expander("View raw swarm JSON"):
                st.json(result)
        except Exception as e:
            st.error(f"Swarm execution failed: {e}")

# ─────────────────────────────────────────────────────────────────────
# TAB 2: Async Task Runner
# ─────────────────────────────────────────────────────────────────────
with tab2:
    st.markdown("### ⚙️ Asynchronous Task Queue (Celery/Redis with ThreadPool fallback)")
    st.caption("Long-running jobs run in the background so the UI never blocks. Uses Celery+Redis if available, otherwise an in-process thread pool.")
    task_kind = st.selectbox("Task type", ["echo", "sample_pipeline", "run_agent_swarm", "index_document"])
    task_payload = st.text_input("Task payload / query", value="agriculture drought resilience satellite NDVI")
    if st.button("▶️ Submit Async Task", type="primary"):
        try:
            from tasks import dispatch_task

            task_id = dispatch_task(task_kind, query=task_payload, label=task_payload).get("id")
            st.success(f"Task `{task_id}` submitted asynchronously.")
            st.session_state["last_task_id"] = task_id
        except Exception as e:
            st.error(f"Failed to submit task: {e}")

    st.markdown("### 📡 Live Task Status")
    if st.button("🔄 Refresh Task Status"):
        try:
            from modules.task_status_registry import list_tasks

            tasks = list_tasks(limit=20)
            if tasks:
                df_t = pd.DataFrame(tasks)
                st.dataframe(df_t[["id", "name", "status", "progress", "message", "updated_at"]], use_container_width=True)
                for t in tasks:
                    if t.get("error"):
                        with st.expander(f"Error for {t['id']}"):
                            st.code(t["error"], language="text")
            else:
                st.info("No tasks yet.")
        except Exception as e:
            st.error(f"Status refresh failed: {e}")

# ─────────────────────────────────────────────────────────────────────
# TAB 3: Hybrid RAG
# ─────────────────────────────────────────────────────────────────────
with tab3:
    st.markdown("### 🔎 Hybrid Graph + Vector RAG Query")
    st.caption("Retrieves chunks via vector similarity (pgvector/SQLite) and expands via a NetworkX knowledge graph for multi-hop context.")
    ingest_text = st.text_area(
        "Source documents (one per line) to index",
        value="Satellite NDVI correlates with crop yield.\nDrought reduces soil moisture and biomass.\nEarly warning systems improve farmer adaptation.",
        height=120,
    )
    if st.button("📥 Index Documents", use_container_width=True):
        try:
            import time
            from rag_engine import index_document

            doc_id = f"doc-{int(time.time())}"
            n = index_document(doc_id=doc_id, title="Enterprise Knowledge Base", body=ingest_text)
            st.success(f"Indexed {n} source chunks (doc: {doc_id}).")
        except Exception as e:
            st.error(f"Indexing failed: {e}")

    query = st.text_input("RAG query", value="How does drought affect crop yield?")
    if st.button("🔎 Retrieve Context", type="primary"):
        try:
            from rag_engine import query_rag

            res = query_rag(query, top_k=3)
            results = res.get("results", [])
            if results:
                st.markdown("**Retrieved context (multi-hop):**")
                for i, r in enumerate(results, 1):
                    st.markdown(f"{i}. **{r['title']}** (score {r['combined_score']}) — {r['body'][:150]}...")
            else:
                st.info("No matching context. Index documents first.")
        except Exception as e:
            st.error(f"RAG query failed: {e}")

# ─────────────────────────────────────────────────────────────────────
# TAB 4: Self-Correcting Executor
# ─────────────────────────────────────────────────────────────────────
with tab4:
    st.markdown("### 🛠️ Automated Schema Self-Correction Executor")
    st.caption("Paste analysis code. If it raises an exception, the stack trace is fed back to the LLM, which fixes and re-runs the code automatically (up to 3 retries).")
    default_code = """import pandas as pd
import numpy as np
df = st.session_state.get('active_df')
if df is None or df.empty:
    df = pd.DataFrame({'x': np.random.normal(0,1,100), 'y': np.random.normal(0,1,100)})
print(df.corr())
mean = df[['x','y']].mean().to_dict()
mean
"""
    code_input = st.text_area("Python analysis code", value=default_code, height=200)
    if st.button("▶️ Execute with Self-Correction", type="primary"):
        try:
            from modules.self_correcting_executor import safe_execute

            res = safe_execute(code_input, {"st": st})
            if res.get("success"):
                st.success(f"Code executed successfully in {res['attempts']} attempt(s).")
                if res.get("output"):
                    st.code(res["output"], language="text")
                st.write("**Result variables:**")
                st.json(res.get("result_vars", {}))
            else:
                st.error(f"Execution failed after {res['attempts']} attempt(s).")
                st.code(res.get("traceback", "No traceback"), language="python")
        except Exception as e:
            st.error(f"Executor failed: {e}")

st.markdown("---")
st.caption("CHRISHEM Multi-Problem Solver • Agent Swarm & Task Console")
