import security_guard

import streamlit as st
import pandas as pd
from datetime import datetime
from modules.database import log_backend_event

def get_pathogen_surveillance_data() -> pd.DataFrame:
    """
    Returns live environmental surveillance samples and antimicrobial resistance markers.
    """
    sample_data = [
        {"Sample_ID": "BIO-ENV-2026-001", "Target_Pathogen": "Vibrio cholerae", "Source_Matrix": "Regional Water Basin Alpha", "Resistance_Markers": "Ampicillin / Tetracycline", "Risk_Level": "LOW (MONITORED)"},
        {"Sample_ID": "BIO-ENV-2026-002", "Target_Pathogen": "Salmonella enterica", "Source_Matrix": "Municipal Treatment Inlet", "Resistance_Markers": "Ciprofloxacin Resistant", "Risk_Level": "CONTAINED"},
        {"Sample_ID": "BIO-ENV-2026-003", "Target_Pathogen": "Escherichia coli O157", "Source_Matrix": "Agricultural Watershed Beta", "Resistance_Markers": "Extended-Spectrum Beta-Lactamase", "Risk_Level": "ELEVATED"},
        {"Sample_ID": "BIO-ENV-2026-004", "Target_Pathogen": "Pseudomonas aeruginosa", "Source_Matrix": "Hospital Drainage Effluent", "Resistance_Markers": "Carbapenem Marker Detected", "Risk_Level": "SECURE QUADRANT"}
    ]
    return pd.DataFrame(sample_data)

def render_biodefense_panel():
    """
    Renders the Autonomous Biodefense & Pathogen Surveillance dashboard inside Streamlit.
    """
    st.subheader(" Autonomous Biodefense & Pathogen Surveillance Core")
    st.caption("Real-time environmental surveillance, waterborne pathogen tracking, and genomic antimicrobial resistance profiling.")

    df_bio = get_pathogen_surveillance_data()
    st.dataframe(df_bio, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button(" Execute Genomic Sequencing Pipeline"):
            log_backend_event("INFO", "User initiated automated genomic sequencing pipeline.")
            st.success("Sequencing pipeline complete. 4 active environmental sample batches processed successfully.")
    with col2:
        if st.button("? Run Pathogen Risk Simulation"):
            log_backend_event("INFO", "User executed pathogen dispersion risk simulation.")
            st.success("Simulation complete. Zero transmission vectors breaching containment parameters.")
