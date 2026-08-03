
"""
Network Analysis Engine  Correlation networks, social network analysis,
co-occurrence networks, centrality metrics, community detection.
"""
from __future__ import annotations

from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
import warnings

from modules.pandas_compat import text_columns
warnings.filterwarnings('ignore')

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False

try:
    from scipy import stats as scipy_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

try:
    import community as community_louvain  # python-louvain
    HAS_LOUVAIN = True
except ImportError:
    HAS_LOUVAIN = False


class NetworkAnalyzer:
    """Construct and analyze networks from research data."""

    def __init__(self):
        self._check_deps()

    def _check_deps(self):
        if not HAS_NETWORKX:
            raise ImportError("networkx required. Install: pip install networkx")

    # â”€â”€â”€ Correlation Network â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def correlation_network(
        self,
        df: pd.DataFrame,
        variables: List[str],
        method: str = "pearson",
        threshold: float = 0.3,
        min_abs_corr: float = 0.1,
    ) -> Dict[str, Any]:
        """Build a weighted network from variable correlations."""
        corr = df[variables].corr(method=method)

        G = nx.Graph()
        edges = []
        for i, v1 in enumerate(variables):
            G.add_node(v1, type="variable")
            for v2 in variables[i  1:]:
                r = corr.loc[v1, v2]
                if abs(r) >= min_abs_corr:
                    color = "#2ecc71" if r > 0 else "#e74c3c"
                    G.add_edge(v1, v2, weight=abs(r), correlation=r, color=color)
                    edges.append({"source": v1, "target": v2, "correlation": round(float(r), 4),
                                  "weight": round(float(abs(r)), 4), "sign": "positive" if r > 0 else "negative"})

        # Centrality metrics
        degree = dict(G.degree(weight='weight'))
        betweenness = nx.betweenness_centrality(G, weight='weight')
        eigenvector = nx.eigenvector_centrality(G, weight='weight', max_iter=1000) if len(G) > 1 else {}
        try:
            pagerank = nx.pagerank(G, weight='weight')
        except Exception:
            pagerank = {}

        # Community detection
        communities = {}
        if HAS_LOUVAIN and len(G) >= 3:
            try:
                partition = community_louvain.best_partition(G, weight='weight')
                communities = {}
                for node, comm_id in partition.items():
                    if comm_id not in communities:
                        communities[comm_id] = []
                    communities[comm_id].append(node)
            except Exception:
                pass

        return {
            "type": "correlation_network",
            "n_nodes": G.number_of_nodes(),
            "n_edges": G.number_of_edges(),
            "density": round(float(nx.density(G)), 4),
            "graph": G,
            "edges": edges,
            "centrality": {
                "degree": {k: round(float(v), 4) for k, v in degree.items()},
                "betweenness": {k: round(float(v), 4) for k, v in betweenness.items()},
                "eigenvector": {k: round(float(v), 4) for k, v in eigenvector.items()},
                "pagerank": {k: round(float(v), 4) for k, v in pagerank.items()},
            },
            "communities": communities,
            "top_central_nodes": sorted(degree, key=degree.get, reverse=True)[:5],
            "method": method,
            "threshold": threshold,
        }

    # â”€â”€â”€ Co-occurrence Network â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def cooccurrence_network(
        self,
        df: pd.DataFrame,
        text_col: str,
        top_n_words: int = 50,
        window_size: int = 3,
    ) -> Dict[str, Any]:
        """Build a co-occurrence network from text data."""
        all_text = " ".join(df[text_col].dropna().astype(str).values)
        words = all_text.lower().split()
        word_freq = pd.Series(words).value_counts()

        # Get top words (exclude very short)
        top_words = set(word_freq.head(top_n_words * 2).index)
        top_words = {w for w in top_words if len(w) > 2}
        top_words = sorted(top_words, key=lambda w: word_freq[w], reverse=True)[:top_n_words]
        word_set = set(top_words)

        G = nx.Graph()
        for w in top_words:
            G.add_node(w, type="word", frequency=int(word_freq[w]))

        # Count co-occurrences within window
        cooccur = {}
        for i, word in enumerate(words):
            if word not in word_set:
                continue
            start = max(0, i - window_size)
            end = min(len(words), i  window_size  1)
            for j in range(start, end):
                if i != j and words[j] in word_set:
                    pair = tuple(sorted([word, words[j]]))
                    cooccur[pair] = cooccur.get(pair, 0)  1

        min_cooccur = max(1, max(cooccur.values()) // 20) if cooccur else 1
        for (w1, w2), count in cooccur.items():
            if count >= min_cooccur:
                G.add_edge(w1, w2, weight=count)

        degree = dict(G.degree(weight='weight'))
        betweenness = nx.betweenness_centrality(G, weight='weight') if len(G) > 1 else {}

        return {
            "type": "cooccurrence_network",
            "n_nodes": G.number_of_nodes(),
            "n_edges": G.number_of_edges(),
            "density": round(float(nx.density(G)), 4),
            "graph": G,
            "top_words": top_words[:20],
            "centrality": {
                "degree": {k: round(float(v), 4) for k, v in degree.items()},
                "betweenness": {k: round(float(v), 4) for k, v in betweenness.items()},
            },
        }

    # â”€â”€â”€ Get Layout Positions for Plotting â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    @staticmethod
    def get_layout_positions(G: nx.Graph, layout: str = "spring") -> Dict[str, Tuple[float, float]]:
        """Compute node positions using specified layout algorithm."""
        if layout == "spring":
            return nx.spring_layout(G, k=2, iterations=50)
        elif layout == "circular":
            return nx.circular_layout(G)
        elif layout == "kamada_kawai":
            return nx.kamada_kawai_layout(G)
        elif layout == "shell":
            return nx.shell_layout(G)
        elif layout == "spectral":
            return nx.spectral_layout(G)
        else:
            return nx.spring_layout(G, k=2, iterations=50)

    @staticmethod
    def network_to_plotly(G: nx.Graph, pos: Dict, node_color_map: Optional[Dict] = None) -> "plotly.graph_objects.Figure":
        """Convert NetworkX graph to Plotly figure."""
        import plotly.graph_objects as go

        edge_trace_x, edge_trace_y = [], []
        edge_weights = []
        for edge in G.edges(data=True):
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_trace_x.extend([x0, x1, None])
            edge_trace_y.extend([y0, y1, None])
            edge_weights.append(edge[2].get('weight', 1))

        edge_trace = go.Scatter(
            x=edge_trace_x, y=edge_trace_y,
            mode='lines',
            line=dict(color='rgba(100,100,150,0.2)', width=1),
            hoverinfo='none',
            showlegend=False,
        )

        node_x, node_y, node_text, node_sizes, node_colors = [], [], [], [], []
        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            node_text.append(str(node))
            degree = G.degree(node, weight='weight')
            node_sizes.append(10  degree * 2)
            node_colors.append(node_color_map.get(node, '#1d4ed8') if node_color_map else '#1d4ed8')

        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markerstext',
            text=node_text,
            textposition="middle center",
            textfont=dict(size=9, color='#333'),
            marker=dict(
                size=node_sizes,
                color=node_colors,
                line=dict(color='white', width=1),
                opacity=0.85,
            ),
            hoverinfo='text',
            showlegend=False,
        )

        fig = go.Figure(data=[edge_trace, node_trace])
        fig.update_layout(
            title="Network Graph",
            showlegend=False,
            hovermode='closest',
            margin=dict(b=20, l=20, r=20, t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=600,
            plot_bgcolor='rgba(0,0,0,0)',
        )
        return fig


# â”€â”€â”€ UI â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def render_network_analysis_ui():
    """Render the Network Analysis page."""
    import streamlit as st
    import plotly.graph_objects as go
    import plotly.express as px

    st.markdown("## ðŸ”— Network Analysis Engine")
    st.markdown("*Correlation networks, centrality metrics, community detection*")

    df = st.session_state.get("active_df")
    if df is None or df.empty:
        st.warning("No data loaded.")
        return

    engine = NetworkAnalyzer()
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    tab1, tab2 = st.tabs(["ðŸ”— Correlation Network", "ðŸ“ Co-occurrence Network"])

    with tab1:
        st.subheader("ðŸ”— Correlation Network")
        vars_for_network = st.multiselect("Select variables (3 recommended)", options=numeric_cols,
                                          default=numeric_cols[:min(10, len(numeric_cols))], key="net_vars")
        method = st.selectbox("Correlation method", options=["pearson", "spearman", "kendall"], key="net_method")
        min_corr = st.slider("Minimum absolute correlation", 0.0, 1.0, 0.3, 0.05, key="net_min_corr")

        if st.button("ðŸ”— Build Network", type="primary", use_container_width=True) and len(vars_for_network) >= 2:
            result = engine.correlation_network(df, vars_for_network, method, min_corr)
            G = result.get("graph")
            if G and G.number_of_edges() > 0:
                pos = engine.get_layout_positions(G, "spring")
                node_colors = {}
                communities = result.get("communities", {})
                color_palette = px.colors.qualitative.Set2
                for comm_id, members in communities.items():
                    color = color_palette[comm_id % len(color_palette)]
                    for m in members:
                        node_colors[m] = color
                fig = engine.network_to_plotly(G, pos, node_colors if node_colors else None)
                st.plotly_chart(fig, use_container_width=True)

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Nodes", result['n_nodes'])
                    st.metric("Edges", result['n_edges'])
                with col2:
                    st.metric("Density", result['density'])
                    st.metric("Communities", len(communities))

                # Centrality table
                cent = result.get("centrality", {})
                if cent.get("degree"):
                    cent_df = pd.DataFrame(cent).round(4)
                    cent_df.index.name = "Node"
                    cent_df = cent_df.reset_index()
                    st.subheader(" Centrality Metrics")
                    st.dataframe(cent_df, use_container_width=True, hide_index=True)
            else:
                st.warning("No edges found. Try lowering the correlation threshold.")

    with tab2:
        st.subheader("ðŸ“ Co-occurrence Network (from text)")
        text_cols = text_columns(df)
        if text_cols:
            text_col = st.selectbox("Text column", options=text_cols, key="net_text_col")
            top_n = st.slider("Top N words", 10, 100, 50, key="net_top_n")
            window = st.slider("Co-occurrence window", 1, 10, 3, key="net_window")

            if st.button("ðŸ“ Build Co-occurrence Network", type="primary", use_container_width=True):
                result = engine.cooccurrence_network(df, text_col, top_n, window)
                G = result.get("graph")
                if G and G.number_of_edges() > 0:
                    pos = engine.get_layout_positions(G, "spring")
                    fig = engine.network_to_plotly(G, pos)
                    st.plotly_chart(fig, use_container_width=True)
                    st.metric("Nodes", result['n_nodes'])
                    st.metric("Edges", result['n_edges'])
                    st.metric("Density", result['density'])
                else:
                    st.warning("No co-occurrences found. Try a larger window.")
        else:
            st.warning("No text columns available for co-occurrence analysis.")

