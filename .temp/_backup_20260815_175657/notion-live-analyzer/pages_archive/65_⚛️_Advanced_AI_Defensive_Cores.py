"""
Page 65 — Advanced AI & Defensive Cores
Exposes the neural forecaster, neural sentinel, quantum core, quantum vault,
biodefense core, cluster mesh, and CVE auditor modules for advanced AI,
quantum, and defensive security analysis.
"""
import sys
from pathlib import Path

import streamlit as st

current_file = Path(__file__).resolve()
root_dir = current_file.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

st.set_page_config(
    page_title="Advanced AI & Defensive Cores",
    page_icon="⚛️",
    layout="wide",
)


def _hero(title, subtitle, badge):
    st.markdown(
        f"""
        <div style="padding:1.6rem;background:linear-gradient(135deg,rgba(99,102,241,.14),rgba(11,19,33,.96));border-radius:14px;border:1px solid rgba(99,102,241,.4);margin-bottom:1.2rem;">
            <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.5rem;">
                <h1 style="color:#818cf8 !important;font-size:1.9rem;margin:0;font-weight:800;">{title}</h1>
                <span style="background:rgba(99,102,241,.16);color:#818cf8;padding:.3rem .8rem;border-radius:999px;font-size:.75rem;font-weight:700;border:1px solid #818cf8;">{badge}</span>
            </div>
            <p style="color:#cbd5e1 !important;margin:.4rem 0 0;font-size:.95rem;">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


_hero(
    "⚛️ Advanced AI & Defensive Cores",
    "Neural forecasting, neural sentinel monitoring, quantum computation core, quantum-backed vault, biodefense surveillance, cluster mesh orchestration, and CVE vulnerability auditing.",
    "Advanced AI, Quantum & Defense Core",
)

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
    [
        "🧠 Neural Forecaster",
        "🛡️ Neural Sentinel",
        "⚛️ Quantum Core",
        "🔐 Quantum Vault",
        "🧬 Biodefense",
        "🕸️ Cluster Mesh",
        "🚨 CVE Auditor",
    ]
)

with tab1:
    try:
        from modules.neural_forecaster import render_neural_forecaster_panel

        render_neural_forecaster_panel()
    except Exception as e:
        st.error(f"Neural forecaster failed to load: {e}")

with tab2:
    try:
        from modules.neural_sentinel import render_neural_sentinel_panel

        render_neural_sentinel_panel()
    except Exception as e:
        st.error(f"Neural sentinel failed to load: {e}")

with tab3:
    try:
        from modules.quantum_core import render_quantum_core_panel

        render_quantum_core_panel()
    except Exception as e:
        st.error(f"Quantum core failed to load: {e}")

with tab4:
    try:
        from modules.quantum_vault import render_quantum_vault_panel

        render_quantum_vault_panel()
    except Exception as e:
        st.error(f"Quantum vault failed to load: {e}")

with tab5:
    try:
        from modules.biodefense_core import render_biodefense_panel

        render_biodefense_panel()
    except Exception as e:
        st.error(f"Biodefense core failed to load: {e}")

with tab6:
    try:
        from modules.cluster_mesh import render_cluster_mesh_panel

        render_cluster_mesh_panel()
    except Exception as e:
        st.error(f"Cluster mesh failed to load: {e}")

with tab7:
    try:
        from modules.cve_auditor import render_cve_auditor_panel

        render_cve_auditor_panel()
    except Exception as e:
        st.error(f"CVE auditor failed to load: {e}")

st.markdown("---")
st.caption("CHRISHEM Multi-Problem Solver • Advanced AI & Defensive Cores Module")
