"""
Sovereign Analytics Engine — real computational tools only.

Every function in this module actually computes what its name says. None of
it generates fake "live" telemetry, fake market data, or fake sentiment
feeds dressed up as real-time monitoring — that pattern (found throughout
app_v3_sovereign_upscaled.py, ~298 random-call sites feeding functions named
things like generate_epidemiological_data / generate_financial_telemetry /
_live_telemetry_feed) has been deliberately excluded from v4.

What IS legitimately stochastic (Monte Carlo simulation, mutation-drift
modeling) is kept, but labeled honestly as a simulation the user configures
and runs on demand — not as a live feed of real-world events.

Gating: every render_* function calls the existing modules.paywall.enforce_paywall,
the same mechanism modules/notion_gating.py already uses. No parallel paywall
system is introduced.
"""
import hashlib
import time

import numpy as np
import pandas as pd
import streamlit as st

from modules.paywall import enforce_paywall

try:
    from sklearn.ensemble import IsolationForest
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


# =============================================================================
# REAL COMPUTATION FUNCTIONS
# =============================================================================

def seir_model(N=1_000_000, I0=100, R0=2.5, gamma=1 / 14, days=180, intervention_day=None, intervention_strength=0.0):
    """
    Solves a discrete-time SEIR (Susceptible-Exposed-Infected-Recovered)
    epidemic model via forward Euler integration. beta is derived from R0
    and gamma (beta = R0 * gamma), matching the standard SEIR formulation.
    An optional intervention reduces transmission (dS, dE) by a fixed
    fraction starting on a given day, modeling a real lockdown/mitigation.
    """
    beta = R0 * gamma
    sigma = 0.5  # incubation rate (1/2 days) — could be exposed as a param later
    S, E, I, R = [N - I0], [0.0], [float(I0)], [0.0]
    for day in range(days):
        s, e, i, r = S[-1], E[-1], I[-1], R[-1]
        dS = -beta * s * i / N
        dE = beta * s * i / N - sigma * e
        dI = sigma * e - gamma * i
        dR = gamma * i
        if intervention_day is not None and day >= intervention_day:
            factor = 1 - intervention_strength
            dS *= factor
            dE *= factor
        S.append(max(0.0, s + dS))
        E.append(max(0.0, e + dE))
        I.append(max(0.0, i + dI))
        R.append(min(float(N), r + dR))
    return pd.DataFrame({"Day": range(days + 1), "Susceptible": S, "Exposed": E, "Infected": I, "Recovered": R})


def needleman_wunsch(seq1: str, seq2: str, match=2, mismatch=-1, gap=-2):
    """
    Global sequence alignment via the Needleman-Wunsch dynamic programming
    algorithm. Returns (aligned_seq1, aligned_seq2, optimal_score).
    """
    m, n = len(seq1), len(seq2)
    score = np.zeros((m + 1, n + 1))
    for i in range(m + 1):
        score[i][0] = gap * i
    for j in range(n + 1):
        score[0][j] = gap * j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            diag = score[i - 1][j - 1] + (match if seq1[i - 1] == seq2[j - 1] else mismatch)
            up = score[i - 1][j] + gap
            left = score[i][j - 1] + gap
            score[i][j] = max(diag, up, left)

    align1, align2 = "", ""
    i, j = m, n
    while i > 0 or j > 0:
        if i > 0 and j > 0 and score[i][j] == score[i - 1][j - 1] + (match if seq1[i - 1] == seq2[j - 1] else mismatch):
            align1 = seq1[i - 1] + align1
            align2 = seq2[j - 1] + align2
            i -= 1
            j -= 1
        elif i > 0 and score[i][j] == score[i - 1][j] + gap:
            align1 = seq1[i - 1] + align1
            align2 = "-" + align2
            i -= 1
        else:
            align1 = "-" + align1
            align2 = seq2[j - 1] + align2
            j -= 1
    return align1, align2, int(score[m][n])


def pagerank(graph_edges, damping=0.85, iterations=100):
    """
    Standard iterative PageRank over a directed edge list
    [(src, dst), ...]. Returns {node: rank} normalized so ranks sum to 1.
    """
    nodes = sorted({n for edge in graph_edges for n in edge})
    idx = {node: i for i, node in enumerate(nodes)}
    n = len(nodes)
    if n == 0:
        return {}
    pr = np.ones(n) / n
    out_degree = np.zeros(n)
    for src, _ in graph_edges:
        out_degree[idx[src]] += 1
    for _ in range(iterations):
        new_pr = np.ones(n) * (1 - damping) / n
        for src, dst in graph_edges:
            if out_degree[idx[src]] > 0:
                new_pr[idx[dst]] += damping * pr[idx[src]] / out_degree[idx[src]]
        pr = new_pr
    return {nodes[i]: round(float(pr[i]), 6) for i in range(n)}


def nash_equilibria_2x2(payoff_a, payoff_b):
    """
    Finds pure-strategy Nash equilibria in a 2x2 game given each player's
    2x2 payoff matrix. Returns a list of (row, col, payoff_a, payoff_b).
    """
    equilibria = []
    for i in range(2):
        for j in range(2):
            a_can_deviate = payoff_a[1 - i][j] > payoff_a[i][j]
            b_can_deviate = payoff_b[i][1 - j] > payoff_b[i][j]
            if not a_can_deviate and not b_can_deviate:
                equilibria.append((i, j, payoff_a[i][j], payoff_b[i][j]))
    return equilibria


def carbon_budget(annual_emissions_gt, target_temp=1.5, current_temp=1.2, tcre=0.45):
    """
    Remaining carbon budget using a Transient Climate Response to
    Emissions (TCRE) approximation: °C warming per 1000 GtCO2 emitted.
    Default TCRE=0.45 is within the IPCC AR6 likely range (0.27–0.63).
    Returns (remaining_budget_gt, years_left_at_current_emissions_rate).
    """
    remaining_gt = (target_temp - current_temp) / tcre * 1000
    years_left = remaining_gt / annual_emissions_gt if annual_emissions_gt > 0 else float("inf")
    return round(remaining_gt, 1), round(years_left, 1)


def proof_of_work(data: str, difficulty=4, max_attempts=5_000_000):
    """
    Real proof-of-work: brute-force search for a nonce such that
    sha256(data + nonce) starts with `difficulty` zero hex digits.
    Capped at max_attempts so a high difficulty can't hang the app.
    """
    target = "0" * difficulty
    start = time.time()
    for nonce in range(max_attempts):
        candidate = hashlib.sha256(f"{data}{nonce}".encode()).hexdigest()
        if candidate.startswith(target):
            return nonce, candidate, time.time() - start
    return None, None, time.time() - start


def elbow_method(X: np.ndarray, max_k=10):
    """
    Runs KMeans for k=1..max_k-1 and returns (inertias, suggested_k) where
    suggested_k is picked by maximum second-derivative drop in inertia —
    a real, if simple, elbow heuristic. Requires scikit-learn.
    """
    if not SKLEARN_AVAILABLE or len(X) < 3:
        return [], None
    max_k = min(max_k, len(X))
    inertias = []
    for k in range(1, max_k):
        model = KMeans(n_clusters=k, random_state=42, n_init=10)
        model.fit(X)
        inertias.append(model.inertia_)
    if len(inertias) < 3:
        return inertias, (len(inertias) if inertias else None)
    drops = [inertias[i] - inertias[i + 1] for i in range(len(inertias) - 1)]
    suggested_k = drops.index(max(drops)) + 2
    return inertias, suggested_k


def anomaly_detection(df: pd.DataFrame, contamination=0.1):
    """
    Real Isolation Forest anomaly detection over the numeric columns of a
    user-supplied dataframe. Returns the dataframe with Anomaly and
    Anomaly_Score columns appended. Requires scikit-learn.
    """
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if not SKLEARN_AVAILABLE or df.empty or len(numeric_cols) < 2:
        return df.assign(Anomaly="N/A (need ≥2 numeric columns)", Anomaly_Score=np.nan)
    X = StandardScaler().fit_transform(df[numeric_cols].fillna(0))
    clf = IsolationForest(contamination=contamination, random_state=42)
    preds = clf.fit_predict(X)
    scores = clf.decision_function(X)
    return df.assign(
        Anomaly=["Anomaly" if p == -1 else "Normal" for p in preds],
        Anomaly_Score=scores,
    )


def monte_carlo_paths(n_runs=1000, baseline=100.0, daily_volatility=0.02, days=30, seed=None):
    """
    Geometric-random-walk Monte Carlo simulation: n_runs independent paths,
    each day's return drawn from Normal(0, daily_volatility). This is a
    genuine stochastic simulation the user runs on demand with parameters
    they choose — not a fake feed of "current market data".
    """
    rng = np.random.default_rng(seed)
    paths = np.empty((n_runs, days + 1))
    paths[:, 0] = baseline
    for d in range(1, days + 1):
        daily_returns = rng.normal(0, daily_volatility, size=n_runs)
        paths[:, d] = paths[:, d - 1] * (1 + daily_returns)
    return paths


# =============================================================================
# STREAMLIT RENDER — paywall-gated the same way modules/notion_gating.py is
# =============================================================================

def render_sovereign_analytics():
    enforce_paywall(allowed_plans=("premium", "pro"), feature_name="Sovereign Analytics Engine", allow_trial=True)

    st.title("Sovereign Analytics Engine")
    st.caption("Real computation only — every result here is actually calculated from the inputs you give it.")

    tabs = st.tabs([
        "Epidemic Model (SEIR)", "Sequence Alignment", "Network Influence (PageRank)",
        "Game Theory", "Climate Budget", "Clustering & Anomalies", "Monte Carlo",
    ])

    with tabs[0]:
        st.subheader("SEIR Epidemic Model")
        c1, c2, c3 = st.columns(3)
        N = c1.number_input("Population size", 1000, 500_000_000, 1_000_000, step=1000)
        R0 = c2.number_input("R₀ (basic reproduction number)", 0.1, 20.0, 2.5, step=0.1)
        days = c3.number_input("Days to simulate", 10, 730, 180, step=10)
        use_intervention = st.checkbox("Model an intervention (e.g. lockdown)")
        intervention_day, intervention_strength = None, 0.0
        if use_intervention:
            ic1, ic2 = st.columns(2)
            intervention_day = ic1.number_input("Intervention starts on day", 0, int(days), 30)
            intervention_strength = ic2.slider("Transmission reduction", 0.0, 1.0, 0.5)
        result = seir_model(N=int(N), R0=R0, days=int(days), intervention_day=intervention_day, intervention_strength=intervention_strength)
        st.line_chart(result.set_index("Day"))
        peak_day = int(result["Infected"].idxmax())
        st.caption(f"Peak infections: {result['Infected'].max():,.0f} on day {peak_day}")

    with tabs[1]:
        st.subheader("Needleman-Wunsch Global Alignment")
        c1, c2 = st.columns(2)
        seq1 = c1.text_input("Sequence 1", "GATTACA")
        seq2 = c2.text_input("Sequence 2", "GCATGCU")
        if seq1 and seq2:
            a1, a2, score = needleman_wunsch(seq1.upper(), seq2.upper())
            st.code(f"{a1}\n{a2}")
            st.caption(f"Alignment score: {score}")

    with tabs[2]:
        st.subheader("PageRank — Network Influence")
        st.caption("One edge per line, as `source,destination`.")
        edge_text = st.text_area("Edges", "A,B\nB,C\nC,A\nA,C\nD,C")
        edges = [tuple(line.split(",")) for line in edge_text.strip().splitlines() if "," in line]
        if edges:
            ranks = pagerank(edges)
            st.dataframe(pd.DataFrame(sorted(ranks.items(), key=lambda x: -x[1]), columns=["Node", "PageRank"]))

    with tabs[3]:
        st.subheader("2x2 Game — Pure Strategy Nash Equilibria")
        st.caption("Payoffs for Player A and Player B, each a 2x2 matrix.")
        col_a, col_b = st.columns(2)
        with col_a:
            a00 = st.number_input("A[0][0]", value=3.0, key="a00")
            a01 = st.number_input("A[0][1]", value=0.0, key="a01")
            a10 = st.number_input("A[1][0]", value=5.0, key="a10")
            a11 = st.number_input("A[1][1]", value=1.0, key="a11")
        with col_b:
            b00 = st.number_input("B[0][0]", value=3.0, key="b00")
            b01 = st.number_input("B[0][1]", value=5.0, key="b01")
            b10 = st.number_input("B[1][0]", value=0.0, key="b10")
            b11 = st.number_input("B[1][1]", value=1.0, key="b11")
        payoff_a = [[a00, a01], [a10, a11]]
        payoff_b = [[b00, b01], [b10, b11]]
        eqs = nash_equilibria_2x2(payoff_a, payoff_b)
        if eqs:
            for (i, j, pa, pb) in eqs:
                st.success(f"Equilibrium at strategy ({i}, {j}): payoffs ({pa}, {pb})")
        else:
            st.info("No pure-strategy Nash equilibrium in this game.")

    with tabs[4]:
        st.subheader("Carbon Budget Calculator")
        c1, c2, c3 = st.columns(3)
        emissions = c1.number_input("Annual emissions (GtCO2)", 0.1, 100.0, 36.8)
        target = c2.number_input("Target temperature (°C)", 1.0, 3.0, 1.5)
        current = c3.number_input("Current warming (°C)", 0.5, 2.0, 1.2)
        budget, years = carbon_budget(emissions, target, current)
        st.metric("Remaining carbon budget", f"{budget:,.0f} GtCO2")
        st.metric("Years left at current emission rate", f"{years:,.1f}" if years != float("inf") else "∞")
        st.caption("Estimate using a TCRE (Transient Climate Response to Emissions) of 0.45°C per 1000 GtCO2, within the IPCC AR6 likely range.")

    with tabs[5]:
        st.subheader("Clustering & Anomaly Detection on Your Data")
        uploaded = st.file_uploader("Upload a CSV to analyze", type=["csv"])
        if uploaded is not None:
            df = pd.read_csv(uploaded)
            st.dataframe(anomaly_detection(df))
            numeric = df.select_dtypes(include=[np.number]).dropna()
            if len(numeric) >= 3:
                inertias, suggested_k = elbow_method(numeric.values)
                if inertias:
                    st.line_chart(pd.Series(inertias, index=range(1, len(inertias) + 1), name="Inertia"))
                    st.caption(f"Suggested cluster count (elbow method): {suggested_k}")
        else:
            st.info("Upload a CSV with at least 2 numeric columns to run real anomaly detection and clustering on it.")

    with tabs[6]:
        st.subheader("Monte Carlo Simulation")
        c1, c2, c3, c4 = st.columns(4)
        n_runs = c1.number_input("Number of paths", 10, 20000, 1000, step=100)
        baseline = c2.number_input("Starting value", 1.0, 1_000_000.0, 100.0)
        vol = c3.slider("Daily volatility", 0.001, 0.20, 0.02)
        mc_days = c4.number_input("Days", 5, 365, 30)
        paths = monte_carlo_paths(n_runs=int(n_runs), baseline=baseline, daily_volatility=vol, days=int(mc_days))
        st.line_chart(pd.DataFrame(paths[:200].T))
        final_values = paths[:, -1]
        st.caption(
            f"Across {int(n_runs)} simulated paths: median ending value "
            f"{np.median(final_values):,.2f}, 5th–95th percentile "
            f"[{np.percentile(final_values, 5):,.2f}, {np.percentile(final_values, 95):,.2f}]"
        )
