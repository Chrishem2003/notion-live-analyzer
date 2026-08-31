import streamlit as st
import numpy as np
import pandas as pd

st.set_page_config(page_title="Sovereign Analytics & Intelligence Brain", page_icon="🧬", layout="wide")

st.title("🧬 Sovereign Analytics & Intelligence Brain")
st.caption("Advanced computational engine: SEIR epidemiological modeling and Needleman-Wunsch sequence alignment.")

tab_seir, tab_align = st.tabs(["📈 SEIR Epidemic Simulation", "🧬 Sequence Alignment"])

with tab_seir:
    st.subheader("Stochastic SEIR Forward Euler Simulation")
    col1, col2, col3 = st.columns(3)
    with col1:
        pop_n = st.number_input("Total Population (N)", value=1000000, step=10000)
        i_zero = st.number_input("Initial Infected (I0)", value=100, step=10)
    with col2:
        r_zero = st.number_input("Reproduction Number (R0)", value=2.5, step=0.1)
        gamma_val = st.number_input("Recovery Rate (gamma)", value=0.0714, step=0.005)
    with col3:
        sim_days = st.slider("Simulation Days", min_value=30, max_value=365, value=180)

    if st.button("Run SEIR Simulation", type="primary"):
        beta = r_zero * gamma_val
        sigma = 0.5
        S, E, I, R = [pop_n - i_zero], [0.0], [float(i_zero)], [0.0]
        for day in range(sim_days):
            s, e, i, r = S[-1], E[-1], I[-1], R[-1]
            dS = -beta * s * i / pop_n
            dE = beta * s * i / pop_n - sigma * e
            dI = sigma * e - gamma_val * i
            dR = gamma_val * i
            S.append(max(0.0, s + dS))
            E.append(max(0.0, e + dE))
            I.append(max(0.0, i + dI))
            R.append(min(float(pop_n), r + dR))
        df_seir = pd.DataFrame({"Day": range(sim_days + 1), "Susceptible": S, "Exposed": E, "Infected": I, "Recovered": R})
        st.line_chart(df_seir.set_index("Day"))
        st.success("Simulation complete.")

with tab_align:
    st.subheader("Needleman-Wunsch Global Sequence Alignment")
    seq_a = st.text_input("Sequence A", value="AGGCTATC")
    seq_b = st.text_input("Sequence B", value="AGCATC")
    if st.button("Align Sequences"):
        m, n = len(seq_a), len(seq_b)
        score_matrix = np.zeros((m + 1, n + 1))
        gap_penalty = -2
        for i in range(m + 1): score_matrix[i][0] = gap_penalty * i
        for j in range(n + 1): score_matrix[0][j] = gap_penalty * j
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                match = score_matrix[i-1][j-1] + (2 if seq_a[i-1] == seq_b[j-1] else -1)
                up = score_matrix[i-1][j] + gap_penalty
                left = score_matrix[i][j-1] + gap_penalty
                score_matrix[i][j] = max(match, up, left)
        st.metric("Optimal Alignment Score", int(score_matrix[m][n]))
        st.write("Score Matrix computed successfully via dynamic programming.")
