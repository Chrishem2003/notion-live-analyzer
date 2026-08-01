

import streamlit as st
import pandas as pd

def get_default_inventory() -> pd.DataFrame:
    """Returns baseline lab inventory dataset."""
    data = [
        {"ItemID": "RGT-001", "Name": "Taq DNA Polymerase", "Category": "Enzyme", "Quantity": 250, "Unit": "U", "Location": "-20°C Box A1", "MinThreshold": 50},
        {"ItemID": "RGT-002", "Name": "10x PCR Buffer", "Category": "Buffer", "Quantity": 15, "Unit": "mL", "Location": "-20°C Box A1", "MinThreshold": 5},
        {"ItemID": "RGT-003", "Name": "dNTP Mix (10mM)", "Category": "Reagent", "Quantity": 2, "Unit": "mL", "Location": "-20°C Box A2", "MinThreshold": 3},
        {"ItemID": "SMP-101", "Name": "BRCA1 cDNA Isolates", "Category": "Sample", "Quantity": 45, "Unit": "uL", "Location": "-80°C Rack 3-B", "MinThreshold": 10},
        {"ItemID": "PRM-501", "Name": "Forward Primer 27F", "Category": "Primer", "Quantity": 100, "Unit": "uM", "Location": "-20°C Box P1", "MinThreshold": 20}
    ]
    return pd.DataFrame(data)

def render_inventory_tab():
    st.subheader("🧪 Laboratory Inventory & Sample Provenance Engine")
    st.caption("Manage physical freezer locations, sample volumes, and automated reagent reorder thresholds.")

    if "inventory_db" not in st.session_state:
        st.session_state["inventory_db"] = get_default_inventory()

    df = st.session_state["inventory_db"]

    inv_col1, inv_col2 = st.columns([2, 1])

    with inv_col1:
        st.markdown("### 📦 Stock Status & Storage Mapping")
        
        # Highlight low stock
        low_stock = df[df["Quantity"] <= df["MinThreshold"]]
        if not low_stock.empty:
            st.error(f"⚠️ **Alert:** {len(low_stock)} item(s) below minimum stock threshold!")
            st.dataframe(low_stock[["Name", "Quantity", "Unit", "Location", "MinThreshold"]], use_container_width=True)
        else:
            st.success("✅ All reagents and samples are above reorder thresholds.")

        st.dataframe(df, use_container_width=True)

    with inv_col2:
        st.markdown("### 🧮 PCR Master Mix Calculator")
        st.caption("Auto-calculate total component volumes with overflow waste margin.")
        
        rxn_count = st.number_input("Number of Reactions", min_value=1, max_value=384, value=10, step=1)
        waste_pct = st.slider("Excess Margin (%)", min_value=0, max_value=20, value=10, step=5)
        
        effective_rxns = rxn_count * (1  (waste_pct / 100.0))
        
        buffer_vol = round(5.0 * effective_rxns, 2)
        dntp_vol = round(1.0 * effective_rxns, 2)
        primer_f_vol = round(1.0 * effective_rxns, 2)
        primer_r_vol = round(1.0 * effective_rxns, 2)
        taq_vol = round(0.25 * effective_rxns, 2)
        water_vol = round(15.75 * effective_rxns, 2)
        
        mm_df = pd.DataFrame([
            {"Component": "Nuclease-Free Water", "Per Rxn (uL)": 15.75, f"Total ({rxn_count} rxns  {waste_pct}%)": water_vol},
            {"Component": "10x Reaction Buffer", "Per Rxn (uL)": 5.00, f"Total ({rxn_count} rxns  {waste_pct}%)": buffer_vol},
            {"Component": "dNTP Mix (10mM)", "Per Rxn (uL)": 1.00, f"Total ({rxn_count} rxns  {waste_pct}%)": dntp_vol},
            {"Component": "Forward Primer (10uM)", "Per Rxn (uL)": 1.00, f"Total ({rxn_count} rxns  {waste_pct}%)": primer_f_vol},
            {"Component": "Reverse Primer (10uM)", "Per Rxn (uL)": 1.00, f"Total ({rxn_count} rxns  {waste_pct}%)": primer_r_vol},
            {"Component": "Taq DNA Polymerase", "Per Rxn (uL)": 0.25, f"Total ({rxn_count} rxns  {waste_pct}%)": taq_vol},
            {"Component": "Total Master Mix Volume", "Per Rxn (uL)": 24.00, f"Total ({rxn_count} rxns  {waste_pct}%)": round(24.0 * effective_rxns, 2)}
        ])
        
        st.table(mm_df)
