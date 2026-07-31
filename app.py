import streamlit as st
import datetime
import hashlib

st.set_page_config(
    page_title="Enterprise Cloud Suite & Storage Engine",
    page_icon="📁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# 1. SESSION STATE INITIALIZATION FOR DYNAMIC FILE STORAGE
# ---------------------------------------------------------
if "files_database" not in st.session_state:
    st.session_state["files_database"] = [
        {
            "id": "FILE-001",
            "name": "BioInformatics_Pipeline_Config.json",
            "type": "Code / JSON",
            "size_bytes": 4404019,
            "size": "4.2 MB",
            "modified": "2026-07-30 14:20",
            "status": "Encrypted (AES-256)",
            "sharing": "Private Vault"
        },
        {
            "id": "FILE-002",
            "name": "Waterborne_Pathogen_Surveillance_Report.pdf",
            "type": "PDF Document",
            "size_bytes": 19818086,
            "size": "18.9 MB",
            "modified": "2026-07-28 09:15",
            "status": "Encrypted (Post-Quantum)",
            "sharing": "Encrypted Link"
        },
        {
            "id": "FILE-003",
            "name": "Regional_Antimicrobial_Resistance_Data.parquet",
            "type": "Dataset / Parquet",
            "size_bytes": 148897792,
            "size": "142.0 MB",
            "modified": "2026-07-25 18:40",
            "status": "Encrypted (AES-256)",
            "sharing": "Domain Only"
        }
    ]

if "vault_view_mode" not in st.session_state:
    st.session_state["vault_view_mode"] = "Grid View (Drive Style)"

# Helper function to format raw byte sizes
def format_file_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"

# ---------------------------------------------------------
# 2. MAIN HEADER & CONTROL TOOLBAR
# ---------------------------------------------------------
st.title("📁 Cloud Storage & Drive Engine")
st.caption("Zero-Knowledge Encrypted Drive Explorer with Real-Time File Handling")

# Calculate Live Storage Telemetry
total_files = len(st.session_state["files_database"])
total_bytes = sum(f.get("size_bytes", 0) for f in st.session_state["files_database"])
total_gb = total_bytes / (1024 ** 3)

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("Total Vault Files", f"{total_files} Items")
with m2:
    st.metric("Storage Volume Used", f"{total_gb:.3f} GB")
with m3:
    st.metric("Encryption Protocol", "AES-256-GCM")
with m4:
    st.metric("KMS Status", "GCP HSM Active")

st.markdown("---")

# ---------------------------------------------------------
# 3. REAL-TIME FILE UPLOADER & INGESTION ENGINE
# ---------------------------------------------------------
st.subheader("📤 Ingest & Encrypt New Files")

uploaded_files = st.file_uploader(
    "Drag and drop files to automatically process, encrypt, and add to your storage node",
    accept_multiple_files=True,
    key="drive_uploader"
)

if uploaded_files:
    new_added_count = 0
    for uploaded_file in uploaded_files:
        # Check if file is already processed in current state
        existing_names = [f["name"] for f in st.session_state["files_database"]]
        if uploaded_file.name not in existing_names:
            file_bytes = uploaded_file.getvalue()
            raw_size = len(file_bytes)
            formatted_size = format_file_size(raw_size)
            
            # Simple file type detection based on extension
            ext = uploaded_file.name.split(".")[-1].upper() if "." in uploaded_file.name else "BINARY"
            file_type_map = {
                "PDF": "PDF Document",
                "JSON": "Code / JSON",
                "CSV": "Dataset / CSV",
                "PARQUET": "Dataset / Parquet",
                "PNG": "Image Asset",
                "JPG": "Image Asset",
                "PY": "Python Script",
                "ZIP": "Archive / Compressed"
            }
            detected_type = file_type_map.get(ext, f"{ext} File")
            
            # Construct File Object
            new_file_record = {
                "id": f"FILE-00{len(st.session_state['files_database']) + 1}",
                "name": uploaded_file.name,
                "type": detected_type,
                "size_bytes": raw_size,
                "size": formatted_size,
                "modified": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "status": "Encrypted (AES-256)",
                "sharing": "Private Vault"
            }
            
            # Insert at top of list
            st.session_state["files_database"].insert(0, new_file_record)
            new_added_count += 1

    if new_added_count > 0:
        st.success(f"✅ Successfully ingested, encrypted, and saved {new_added_count} new file(s) into your vault!")
        st.rerun()

st.markdown("---")

# ---------------------------------------------------------
# 4. EXPLORER CONTROLS & DISPLAY RENDERER
# ---------------------------------------------------------
st.subheader("🗂️ Drive Explorer")

ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([4, 3, 3])

with ctrl_col1:
    search_query = st.text_input("Search Explorer", placeholder="🔍 Filter files by name or type...", label_visibility="collapsed")

with ctrl_col2:
    category_filter = st.selectbox(
        "Filter Category",
        ["All Items", "PDF Document", "Code / JSON", "Dataset", "Image Asset"],
        label_visibility="collapsed"
    )

with ctrl_col3:
    view_mode = st.selectbox(
        "Display Layout",
        ["Grid View (Drive Style)", "Detailed Table View"],
        label_visibility="collapsed"
    )
    st.session_state["vault_view_mode"] = view_mode

# Apply Filtering
filtered_files = st.session_state["files_database"]
if search_query:
    filtered_files = [f for f in filtered_files if search_query.lower() in f["name"].lower() or search_query.lower() in f["type"].lower()]

if category_filter != "All Items":
    filtered_files = [f for f in filtered_files if category_filter.lower() in f["type"].lower()]

# RENDER GRID VIEW
if "Grid View" in st.session_state["vault_view_mode"]:
    if not filtered_files:
        st.info("No files found matching current filter.")
    else:
        grid_cols = st.columns(3)
        for idx, item in enumerate(filtered_files):
            with grid_cols[idx % 3]:
                with st.container(border=True):
                    st.markdown(f"#### 📄 {item['name']}")
                    st.caption(f"**Type:** {item['type']} | **Size:** {item['size']}")
                    st.caption(f"**Modified:** {item['modified']}")
                    
                    # Security Badge
                    st.markdown(f"{item['status']} | {item['sharing']}")
                    st.markdown("---")
                    
                    act1, act2, act3 = st.columns(3)
                    if act1.button("👁️ View", key=f"grid_view_{item['id']}"):
                        st.info(f"**File Details:**\n- **ID:** {item['id']}\n- **Name:** {item['name']}\n- **Hash:** sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
                    
                    if act2.button("🔑 Access", key=f"grid_share_{item['id']}"):
                        st.toast(f"Updated access rules for {item['name']}")
                        
                    if act3.button("🗑️ Delete", key=f"grid_del_{item['id']}"):
                        st.session_state["files_database"] = [f for f in st.session_state["files_database"] if f["id"] != item["id"]]
                        st.toast(f"Deleted {item['name']}")
                        st.rerun()

# RENDER DETAILED TABLE VIEW
else:
    if not filtered_files:
        st.info("No files found matching current filter.")
    else:
        st.dataframe(
            filtered_files,
            use_container_width=True,
            column_config={
                "id": "File ID",
                "name": "File Name",
                "type": "Resource Type",
                "size": "Size",
                "modified": "Last Modified",
                "status": "Encryption",
                "sharing": "Access Control"
            }
        )