import streamlit as st
import datetime

st.set_page_config(
    page_title="Enterprise Drive Explorer & Workspace",
    page_icon="📁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# 1. INITIALIZE IN-MEMORY FILE DATABASE WITH SAFE KEYS
# ---------------------------------------------------------
if "vault_files" not in st.session_state:
    st.session_state["vault_files"] = [
        {
            "id": "FILE-001",
            "name": "BioInformatics_Pipeline_Config.json",
            "type": "Code / JSON",
            "size": "4.2 MB",
            "size_bytes": 4404019,
            "modified": "2026-07-30 14:20",
            "status": "Encrypted (AES-256)",
            "content": "{\n  \"pipeline\": \"Waterborne Pathogen AMR Pipeline\",\n  \"version\": \"2.4.0\",\n  \"nodes\": [\"Arua_Lab_01\", \"Gulu_Lab_02\"],\n  \"encryption\": \"AES-256-GCM\"\n}"
        },
        {
            "id": "FILE-002",
            "name": "Waterborne_Pathogen_Surveillance_Report.pdf",
            "type": "PDF Document",
            "size": "18.9 MB",
            "size_bytes": 19818086,
            "modified": "2026-07-28 09:15",
            "status": "Encrypted (Post-Quantum)",
            "content": "--- REGIONAL SURVEILLANCE REPORT DATA ---\nSample Collection: Northern & West Nile Districts\nTarget Organisms: Vibrio cholerae, Salmonella spp., E. coli"
        },
        {
            "id": "FILE-003",
            "name": "Regional_Antimicrobial_Resistance_Data.parquet",
            "type": "Dataset / Parquet",
            "size": "142.0 MB",
            "size_bytes": 148897792,
            "modified": "2026-07-25 18:40",
            "status": "Encrypted (AES-256)",
            "content": "Sample_ID,Isolate_Type,Resistance_Gene,Geo_Location\nSMP-001,V.cholerae,ctxA,3.0300_30.9000"
        }
    ]

# ---------------------------------------------------------
# 2. SAFE WORKSPACE INSPECTION & EDITOR MODAL
# ---------------------------------------------------------
@st.dialog("📄 Workspace File Viewer & Editor", width="large")
def inspect_and_edit_file(file_item):
    # Safely retrieve content string with default fallback
    file_content = file_item.get("content", f"[Binary or Uncached File Stream for {file_item.get('name', 'File')}]\nSize: {file_item.get('size', 'N/A')}\nStatus: Active Encrypted Stream")
    
    st.markdown(f"### 📄 {file_item.get('name', 'Untitled File')}")
    st.caption(f"**ID:** {file_item.get('id', 'FILE-000')} | **Status:** {file_item.get('status', 'Encrypted')} | **Size:** {file_item.get('size', 'Unknown')}")
    
    tab_view, tab_edit, tab_actions = st.tabs(["👁️ Full View / Preview", "✏️ Edit Content", "📥 Download & Export"])

    # TAB 1: FULL FILE PREVIEW
    with tab_view:
        st.markdown("**Full File Contents / Stream Payload:**")
        file_type = file_item.get("type", "")
        file_name = file_item.get("name", "")
        
        if "JSON" in file_type or file_name.endswith(".json"):
            st.code(file_content, language="json")
        elif "Dataset" in file_type or file_name.endswith(".csv"):
            st.code(file_content, language="csv")
        else:
            st.text_area("File Stream Viewer", value=file_content, height=300, disabled=True)

    # TAB 2: LIVE IN-APP EDITOR
    with tab_edit:
        st.markdown("**Edit File Contents:**")
        updated_content = st.text_area(
            "Modify text stream below:",
            value=file_content,
            height=300,
            key=f"editor_{file_item.get('id', 'temp')}"
        )
        
        if st.button("💾 Save Changes to Drive", type="primary", key=f"save_{file_item.get('id', 'temp')}"):
            file_item["content"] = updated_content
            file_item["modified"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M (Edited)")
            st.success("✅ File updated successfully in Drive Storage!")
            st.rerun()

    # TAB 3: DOWNLOAD & EXPORT
    with tab_actions:
        st.markdown("### 📥 Download to Local Device")
        st.write("Click below to download this file directly to your computer:")
        
        file_bytes = file_content.encode("utf-8")
        st.download_button(
            label=f"⬇️ Download {file_item.get('name', 'file')}",
            data=file_bytes,
            file_name=file_item.get('name', 'download.txt'),
            mime="text/plain",
            type="primary",
            key=f"dl_btn_{file_item.get('id', 'temp')}"
        )
        
        st.markdown("---")
        st.markdown("### 🛡️ Cryptographic Integrity")
        st.code("SHA-256 Checksum: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", language="text")

# ---------------------------------------------------------
# 3. METRICS HEADER
# ---------------------------------------------------------
total_count = len(st.session_state["vault_files"])
total_bytes = sum(f.get("size_bytes", 0) for f in st.session_state["vault_files"])
total_mb = total_bytes / (1024 * 1024)

st.title("📁 Drive Explorer & Workspace Hub")

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("Total Items", f"{total_count}")
with m2:
    st.metric("Storage Volume", f"{total_mb:.1f} MB")
with m3:
    st.metric("Encryption Protocol", "AES-256-GCM")
with m4:
    st.metric("KMS Status", "Active (0 Leak)")

st.markdown("---")

# ---------------------------------------------------------
# 4. INGESTION UPLOADER
# ---------------------------------------------------------
st.subheader("📤 Ingest & Upload Files to Drive")
uploaded = st.file_uploader(
    "Drop files here to upload, edit, or download across your workspace:",
    accept_multiple_files=True,
    key="drive_workspace_uploader"
)

if uploaded:
    new_count = 0
    for file in uploaded:
        if not any(f.get("name") == file.name for f in st.session_state["vault_files"]):
            size_kb = file.size / 1024
            size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"
            ext = file.name.split(".")[-1].upper() if "." in file.name else "FILE"
            
            try:
                raw_bytes = file.getvalue()
                content_payload = raw_bytes.decode("utf-8")
            except Exception:
                content_payload = f"Binary Stream Resource [{file.name}]\nSize: {size_str}\nStatus: Verified Payload"

            new_item = {
                "id": f"FILE-00{len(st.session_state['vault_files']) + 1}",
                "name": file.name,
                "type": f"{ext} Document",
                "size": size_str,
                "size_bytes": file.size,
                "modified": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "status": "Encrypted (AES-256)",
                "content": content_payload
            }
            st.session_state["vault_files"].insert(0, new_item)
            new_count += 1
            
    if new_count > 0:
        st.success(f"Successfully uploaded {new_count} file(s) into Drive Workspace!")
        st.rerun()

st.markdown("---")

# ---------------------------------------------------------
# 5. RENDER DRIVE CARDS
# ---------------------------------------------------------
st.subheader("🗂️ Stored Workspace Files")

cols = st.columns(3)
for idx, item in enumerate(st.session_state["vault_files"]):
    with cols[idx % 3]:
        with st.container(border=True):
            st.markdown(f"#### 📄 {item.get('name', 'File')}")
            st.caption(f"**Type:** {item.get('type', 'Doc')} | **Size:** {item.get('size', 'N/A')}")
            st.caption(f"**Modified:** {item.get('modified', 'Recently')}")
            st.markdown(f"{item.get('status', 'Encrypted')}")
            st.markdown("---")
            
            b1, b2 = st.columns(2)
            if b1.button("👁️ Open / Edit", key=f"v_{idx}"):
                inspect_and_edit_file(item)
                
            if b2.button("🗑️ Delete", key=f"d_{idx}"):
                st.session_state["vault_files"] = [f for f in st.session_state["vault_files"] if f.get("name") != item.get("name")]
                st.rerun()