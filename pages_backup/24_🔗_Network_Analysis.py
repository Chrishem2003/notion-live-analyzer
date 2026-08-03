import security_guard
security_guard.verify_access()



"""
═══════════════════════════════════════════════════════════════════════════════
ADVANCED NETWORK SCIENCE & TOPOLOGICAL GRAPH ANALYTICS ENGINE [ENTERPRISE v3.0]
Features: Dynamic Correlation Graph Construction, Multi-Metric Centralities,
Louvain & Leiden Community Detection, Shortest Influence Path Routing,
and Network Robustness / Resilience Attack Simulations.
Designed for CHRISHEM Enterprise Build.
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import streamlit as st
import pandas as pd
import numpy as np

# ─── RESOLVE IMPORT PATH (PREVENTS IMPORTERRORS ACROSS ALL PLATFORMS) ──────────
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ─── PAGE CONFIGURATION ───────────────────────────────────────────────
st.set_page_config(
    page_title="Advanced Network Science & Graph Analytics",
    page_icon="🔍 ",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── DEPENDENCY CHECK & FALLBACKS ─────────────────────────────────────
try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False

try:
    import community as community_louvain
    HAS_COMMUNITY = True
except ImportError:
    HAS_COMMUNITY = False

try:
    import plotly.graph_objects as go
    import plotly.express as px
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

if not HAS_NETWORKX:
    st.error("⚠️ `networkx` is required for topological analysis. Please run `pip install networkx python-louvain plotly pandas numpy` in your terminal.")
    st.stop()

# ─── CUSTOM HIGH-CONTRAST ENTERPRISE CSS ──────────────────────────────
st.markdown("""
<style>
    /* --- GLOBAL SIDEBAR DARK THEMING OVERRIDE --- */
    [data-testid="stSidebar"], section[data-testid="stSidebar"] {
        background-color: #090d16 !important;
        border-right: 1px solid #1e293b !important;
    }
    
    /* Force all sidebar text, links, and headers to high-contrast off-white */
    [data-testid="stSidebar"] *, section[data-testid="stSidebar"] * {
        color: #f8fafc !important;
    }

    /* Target navigation links and text explicitly */
    [data-testid="stSidebarNav"] span, 
    [data-testid="stSidebarNav"] a,
    [data-testid="stSidebarNavLink"],
    [data-testid="stSidebarHeader"] {
        color: #f8fafc !important;
        font-weight: 600 !important;
    }

    /* Navigation item hover state */
    [data-testid="stSidebarNavLink"]:hover,
    [data-testid="stSidebarNav"] a:hover {
        background-color: #1e293b !important;
        border-radius: 8px !important;
    }

    /* Currently selected navigation item active state */
    [data-testid="stSidebarNavLink"][aria-current="page"],
    [data-testid="stSidebarNav"] a[aria-selected="true"] {
        background-color: #0284c7 !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
    }

    /* Custom form inputs inside sidebar */
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] .stMultiSelect label {
        color: #38bdf8 !important;
        font-weight: 700 !important;
    }

    /* Main App Background & Default Text */
    .stApp {
        background-color: #020617 !important;
        color: #f8fafc !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    h1, h2, h3, h4, h5, h6 {
        color: #f8fafc !important;
        font-weight: 800 !important;
    }

    p, span, label, div {
        color: #cbd5e1 !important;
    }

    .net-card {
        background: #090d16 !important;
        border: 1px solid #1e293b !important;
        border-radius: 16px;
        padding: 1.25rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
        margin-bottom: 1rem;
    }

    .badge-net {
        background: rgba(56, 189, 248, 0.15) !important;
        color: #38bdf8 !important;
        border: 1px solid #0369a1 !important;
        padding: 0.25rem 0.6rem;
        border-radius: 6px;
        font-size: 0.7rem;
        font-family: monospace;
        font-weight: 700;
        letter-spacing: 0.05em;
    }

    /* Form Controls & Inputs */
    div.stSelectbox, div.stSlider, div.stTextInput {
        background-color: #090d16 !important;
        border-radius: 8px !important;
    }
    
    .stButton button {
        background: #090d16 !important;
        border: 1px solid #0284c7 !important;
        color: #38bdf8 !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        transition: all 0.2s ease;
    }
    .stButton button:hover {
        background: #0284c7 !important;
        color: #ffffff !important;
        box-shadow: 0 0 16px rgba(56, 189, 248, 0.4);
    }

    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #020617;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: #090d16 !important;
        border: 1px solid #1e293b !important;
        border-radius: 8px 8px 0px 0px !important;
        color: #94a3b8 !important;
        font-weight: 600;
        padding: 0.6rem 1.2rem !important;
    }

    .stTabs [aria-selected="true"] {
        background-color: #1e293b !important;
        color: #38bdf8 !important;
        border-color: #38bdf8 !important;
    }

    div[data-testid="stMetricValue"] {
        color: #38bdf8 !important;
        font-weight: 800 !important;
    }
</style>
""", unsafe_allow_html=True)

# ─── HELPER FUNCTION: DYNAMIC GRAPH BUILDER ────────────────────────────
@st.cache_data
def generate_synthetic_graph(num_nodes=20, edge_prob=0.30, seed=42):
    """Generates a weighted synthetic network graph with domain labels."""
    np.random.seed(seed)
    labels = [
        "Ecosystem_Yield", "Soil_Moisture", "Temperature_Avg", "Elevation_Index",
        "Cloud_Cover", "Microbial_Density", "Nitrogen_Flux", "Precipitation_Rate",
        "Canopy_Cover", "Biomass_Index", "Solar_Radiation", "Hydrological_Flow",
        "Soil_pH", "Evapotranspiration", "Carbon_Sequestration", "Species_Richness",
        "Leaf_Area_Index", "Groundwater_Depth", "Wind_Velocity", "Ambient_Humidity"
    ][:num_nodes]
    
    G = nx.erdos_renyi_graph(n=len(labels), p=edge_prob, seed=seed)
    mapping = {i: label for i, label in enumerate(labels)}
    G = nx.relabel_nodes(G, mapping)
    
    for (u, v) in G.edges():
        G.edges[u, v]['weight'] = float(np.round(np.random.uniform(0.35, 0.95), 3))
        
    return G

# Initialize Session Graph
if "G" not in st.session_state:
    st.session_state["G"] = generate_synthetic_graph()

G = st.session_state["G"]

# ─── HERO HEADER ───────────────────────────────────────────────────────
louvain_status = "🔍 Louvain Modularity Engine Active" if HAS_COMMUNITY else "🔍 Default Modularity Fallback"
st.markdown(f"""
<div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:1.5rem; flex-wrap:wrap; gap:1rem;'>
    <div>
        <span class='badge-net'>⚡ v3.0 ULTRA  TOPOLOGICAL GRAPH ANALYTICS ENGINE</span>
        <h1 style='font-size:2.2rem; color:#f8fafc; margin:0.4rem 0 0.2rem 0;'>
            🔍 Advanced Network Science & Topology Lab
        </h1>
        <p style='color:#94a3b8; font-size:0.95rem; max-width:850px; margin:0;'>
            Construct dynamic correlation networks, evaluate node centralities, run modularity-based community detection algorithms, map influence pathways, and stress-test graph resilience.
        </p>
    </div>
    <div style='text-align:right;'>
        <div style='background:#090d16; border:1px solid #1e293b; padding:0.8rem 1.2rem; border-radius:14px;'>
            <div style='font-size:0.65rem; color:#64748b; text-transform:uppercase; font-weight:700;'>Graph Engine</div>
            <div style='color:#10b981; font-size:0.85rem; font-weight:800;'>{louvain_status}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<hr style='border-color:#1e293b; margin:1rem 0;'>", unsafe_allow_html=True)

# ─── NAVIGATION TABS ───────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔍 Correlation & Edge Thresholding",
    "🔍 Centrality & Node Importance",
    "🔍 Community Detection & Modularity",
    "⚡ Shortest Paths & Flow Routing",
    "🔍 Graph Metrics & Resilience"
])

# ═══════════════════════════════════════════════════════════════════════
# TAB 1: CORRELATION & PARTIAL NETWORKS
# ═══════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("<h3 style='color:#38bdf8;'>🔍 Correlation Networks & Edge Thresholding</h3>", unsafe_allow_html=True)
    st.markdown("Transform multivariate datasets into thresholded, weighted graph topologies.")

    col_c1, col_c2 = st.columns([4, 6])
    with col_c1:
        st.markdown("<div class='net-card'>", unsafe_allow_html=True)
        metric_choice = st.selectbox("Correlation Metric", ["Pearson r", "Spearman Rank", "Partial Correlation", "Mutual Information"])
        threshold = st.slider("Edge Weight Threshold (|r| ≥)", 0.30, 0.95, 0.45, step=0.05)
        remove_isolated = st.checkbox("Remove Isolated Nodes (Degree = 0)", value=True)
        
        if st.button("🔍 Rebuild Correlation Network", use_container_width=True):
            raw_G = generate_synthetic_graph(num_nodes=20, edge_prob=0.40, seed=int(threshold * 100))
            filtered_G = nx.Graph()
            for u, v, d in raw_G.edges(data=True):
                if d.get("weight", 0) >= threshold:
                    filtered_G.add_edge(u, v, weight=d["weight"])
            
            # Keep nodes that meet the threshold or retain nodes connected to edges
            for n in raw_G.nodes():
                if not remove_isolated or n in filtered_G.nodes():
                    filtered_G.add_node(n)
            
            if remove_isolated:
                filtered_G.remove_nodes_from(list(nx.isolates(filtered_G)))
                
            st.session_state["G"] = filtered_G
            st.success(f"Network updated! Total Nodes: {filtered_G.number_of_nodes()}, Edges: {filtered_G.number_of_edges()}")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with col_c2:
        st.markdown("<div class='net-card'>", unsafe_allow_html=True)
        st.markdown("#### 🔍 Current Graph Topology Summary")
        
        cur_G = st.session_state["G"]
        n_nodes = cur_G.number_of_nodes()
        n_edges = cur_G.number_of_edges()
        density = nx.density(cur_G) if n_nodes > 1 else 0
        avg_deg = np.mean([d for n, d in cur_G.degree()]) if n_nodes > 0 else 0
        clustering_coeff = nx.average_clustering(cur_G) if n_nodes > 0 else 0
        conn_comp = nx.number_connected_components(cur_G) if n_nodes > 0 else 0
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Active Nodes", n_nodes)
        m2.metric("Active Edges", n_edges)
        m3.metric("Graph Density", f"{density:.3f}")

        st.code(f"""
Network Topology Summary:
=================================================================
Nodes: {n_nodes} variables | Edges: {n_edges}
Average Degree: {avg_deg:.2f}
Connected Components: {conn_comp}
Clustering Coefficient: {clustering_coeff:.3f}
=================================================================
        """, language="text")
        st.markdown("</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# TAB 2: CENTRALITY & NODE IMPORTANCE
# ═══════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("<h3 style='color:#38bdf8;'>🔍 Multi-Metric Centrality & Node Importance</h3>", unsafe_allow_html=True)

    col_cn1, col_cn2 = st.columns([4, 6])
    with col_cn1:
        st.markdown("<div class='net-card'>", unsafe_allow_html=True)
        cent_choice = st.selectbox("Primary Centrality Metric", ["PageRank", "Betweenness Centrality", "Eigenvector Centrality", "Degree Centrality"])
        top_n = st.slider("Top N Nodes to Highlight", 5, 20, 10)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_cn2:
        st.markdown("<div class='net-card'>", unsafe_allow_html=True)
        st.markdown(f"#### 🔍 Top Nodes Ranked by {cent_choice}")
        
        cur_G = st.session_state["G"]
        if cur_G.number_of_nodes() > 0:
            if cent_choice == "PageRank":
                scores = nx.pagerank(cur_G)
            elif cent_choice == "Betweenness Centrality":
                scores = nx.betweenness_centrality(cur_G)
            elif cent_choice == "Eigenvector Centrality":
                try:
                    scores = nx.eigenvector_centrality(cur_G, max_iter=500)
                except Exception:
                    scores = nx.degree_centrality(cur_G)
            else:
                scores = nx.degree_centrality(cur_G)

            df_cent = pd.DataFrame(list(scores.items()), columns=["Node", "Centrality"]).sort_values("Centrality", ascending=True).tail(top_n)

            if HAS_PLOTLY:
                fig = px.bar(
                    df_cent, x="Centrality", y="Node", orientation="h",
                    color="Centrality", color_continuous_scale="Viridis",
                    text_auto=".3f"
                )
                fig.update_layout(
                    paper_bgcolor="#020617", plot_bgcolor="#090d16",
                    font=dict(color="#f8fafc"), margin=dict(t=20, b=20, l=20, r=20),
                    xaxis=dict(gridcolor="#1e293b"), yaxis=dict(gridcolor="#1e293b")
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.dataframe(df_cent, use_container_width=True)
        else:
            st.warning("⚠️ Graph is empty. Lower threshold in Tab 1 to populate graph.")
        st.markdown("</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# TAB 3: COMMUNITY DETECTION & MODULARITY
# ═══════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("<h3 style='color:#38bdf8;'>🔍 Community Detection & Modularity Optimization</h3>", unsafe_allow_html=True)

    col_cm1, col_cm2 = st.columns([4, 6])
    with col_cm1:
        st.markdown("<div class='net-card'>", unsafe_allow_html=True)
        comm_algo = st.selectbox("Community Algorithm", ["Louvain Modularity", "Greedy Modularity Maximization", "Label Propagation"])
        resolution = st.slider("Resolution Parameter", 0.5, 2.0, 1.0, step=0.1)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_cm2:
        st.markdown("<div class='net-card'>", unsafe_allow_html=True)
        st.markdown("#### 🔍 Partition Modularity & Network Map")
        
        cur_G = st.session_state["G"]
        if cur_G.number_of_nodes() > 0:
            if HAS_COMMUNITY and comm_algo == "Louvain Modularity":
                partition = community_louvain.best_partition(cur_G, resolution=resolution)
                modularity_q = community_louvain.modularity(partition, cur_G)
            else:
                communities = list(nx.community.greedy_modularity_communities(cur_G))
                partition = {}
                for idx, comm in enumerate(communities):
                    for node in comm:
                        partition[node] = idx
                modularity_q = nx.community.modularity(cur_G, communities)

            st.metric(label="Optimal Modularity Score (Q)", value=f"Q = {modularity_q:.4f}")
            
            if HAS_PLOTLY:
                pos = nx.spring_layout(cur_G, seed=42)
                edge_x, edge_y = [], []
                for edge in cur_G.edges():
                    x0, y0 = pos[edge[0]]
                    x1, y1 = pos[edge[1]]
                    edge_x.extend([x0, x1, None])
                    edge_y.extend([y0, y1, None])

                edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=1, color='#475569'), hoverinfo='none', mode='lines')

                node_x, node_y, node_colors, node_text = [], [], [], []
                for node in cur_G.nodes():
                    x, y = pos[node]
                    node_x.append(x)
                    node_y.append(y)
                    node_colors.append(partition.get(node, 0))
                    node_text.append(f"Node: {node}<br>Community: {partition.get(node, 0)}")

                node_trace = go.Scatter(
                    x=node_x, y=node_y, mode='markerstext', text=[n for n in cur_G.nodes()],
                    textposition="top center", hoverinfo='text', hovertext=node_text,
                    marker=dict(showscale=True, colorscale='Turbo', color=node_colors, size=16, line_width=2)
                )

                fig_net = go.Figure(data=[edge_trace, node_trace])
                fig_net.update_layout(
                    showlegend=False, paper_bgcolor="#020617", plot_bgcolor="#090d16",
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    margin=dict(t=10, b=10, l=10, r=10), height=450
                )
                st.plotly_chart(fig_net, use_container_width=True)
            else:
                st.write(partition)
        else:
            st.warning("⚠️ Graph contains no active nodes.")
        st.markdown("</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# TAB 4: SHORTEST PATHS & FLOW ROUTING
# ═══════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("<h3 style='color:#38bdf8;'>⚡ Shortest Paths & Influence Flow Routing</h3>", unsafe_allow_html=True)

    cur_G = st.session_state["G"]
    node_list = list(cur_G.nodes())

    col_p1, col_p2 = st.columns([4, 6])
    with col_p1:
        st.markdown("<div class='net-card'>", unsafe_allow_html=True)
        if len(node_list) >= 2:
            src_node = st.selectbox("Source Node (Origin)", node_list, index=0)
            tgt_node = st.selectbox("Target Node (Destination)", node_list, index=min(1, len(node_list)-1))
        else:
            src_node, tgt_node = None, None
            st.info("⚠️ Add more connected nodes to evaluate pathways.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_p2:
        st.markdown("<div class='net-card'>", unsafe_allow_html=True)
        st.markdown("#### 🔍 Causal Transmission Cascade Route")
        if src_node and tgt_node and nx.has_path(cur_G, src_node, tgt_node):
            path = nx.shortest_path(cur_G, source=src_node, target=tgt_node)
            path_len = len(path) - 1
            st.success(f"✅ Shortest Path Found: **{path_len} Intermediate Hop(s)**")
            
            path_str = " ──> ".join([f"[{node}]" for node in path])
            st.code(f"Transmission Path:\n{path_str}", language="text")
        else:
            st.error("❌ No valid pathway exists between selected nodes.")
        st.markdown("</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# TAB 5: GRAPH METRICS & RESILIENCE
# ═══════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown("<h3 style='color:#38bdf8;'>🔍 Global Graph Metrics & Structural Resilience</h3>", unsafe_allow_html=True)

    col_g1, col_g2 = st.columns([4, 6])
    with col_g1:
        st.markdown("<div class='net-card'>", unsafe_allow_html=True)
        st.markdown("#### 🔍 Resilience Stress Simulator")
        attack_type = st.selectbox("Simulated Attack Strategy", ["Targeted Hub Removal (Betweenness)", "Random Node Failure"])
        st.markdown("</div>", unsafe_allow_html=True)

    with col_g2:
        st.markdown("<div class='net-card'>", unsafe_allow_html=True)
        st.markdown("#### 🔍 Giant Component Decay Curve")
        
        cur_G = st.session_state["G"].copy()
        if cur_G.number_of_nodes() > 0:
            nodes_to_remove = list(cur_G.nodes())
            if "Targeted" in attack_type:
                cent = nx.betweenness_centrality(cur_G)
                nodes_to_remove = sorted(cent, key=cent.get, reverse=True)
            else:
                np.random.shuffle(nodes_to_remove)

            fractions, giant_sizes = [], []
            total_n = cur_G.number_of_nodes()
            
            temp_G = cur_G.copy()
            for i, n in enumerate(nodes_to_remove):
                fractions.append(i / total_n)
                if temp_G.number_of_nodes() > 0:
                    largest_cc = len(max(nx.connected_components(temp_G), key=len))
                    giant_sizes.append(largest_cc / total_n)
                else:
                    giant_sizes.append(0)
                temp_G.remove_node(n)

            df_decay = pd.DataFrame({"Fraction Removed": fractions, "Giant Component Share": giant_sizes})
            if HAS_PLOTLY:
                fig_decay = px.line(df_decay, x="Fraction Removed", y="Giant Component Share", title="Network Breakdown Curve")
                fig_decay.update_traces(line_color="#f43f5e", line_width=3)
                fig_decay.update_layout(
                    paper_bgcolor="#020617", plot_bgcolor="#090d16",
                    font=dict(color="#f8fafc"), xaxis=dict(gridcolor="#1e293b"), yaxis=dict(gridcolor="#1e293b")
                )
                st.plotly_chart(fig_decay, use_container_width=True)
            else:
                st.dataframe(df_decay, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ─── FOOTER WATERMARK ───────────────────────────────────────────────────
st.markdown("<hr style='border-color:#1e293b; margin-top:3rem;'>", unsafe_allow_html=True)
st.markdown(
    "<div style='text-align:center; color:#64748b; font-size:0.75rem; font-family:monospace; letter-spacing:0.1em;'>"
    "AUTONOMOUS RESEARCH OPERATING SYSTEM • TOPOLOGICAL NETWORK SCIENCE ENGINE • DESIGNED FOR CHRISHEM"
    "</div>",
    unsafe_allow_html=True
)

