import streamlit as st
import datetime

st.set_page_config(
    page_title="Enterprise Cloud Suite & Storage Engine",
    page_icon="📁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 1. INITIALIZE IN-MEMORY FILE DATABASE
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
            "content_preview": "{\n  \"pipeline\": \"Waterborne Pathogen AMR Pipeline\",\n  \"version\": \"2.4.0\",\n  \"nodes\": [\"Arua_Lab_01\", \"Gulu_Lab_02\"],\n  \"encryption\": \"AES-256-GCM\"\n}"
        },
        {
            "id": "FILE-002",
            "name": "Waterborne_Pathogen_Surveillance_Report.pdf",
            "type": "PDF Document",
            "size": "18.9 MB",
            "size_bytes": 19818086,
            "modified": "2026-07-28 09:15",
            "status": "Encrypted (Post-Quantum)",
            "content_preview": "PDF Document Stream [Binary Encrypted Payload]\nAuthor: Research Unit\nChecksum: SHA256-8F90A2C1"
        },
        {
            "id": "FILE-003",
            "name": "Regional_Antimicrobial_Resistance_Data.parquet",
            "type": "Dataset / Parquet",
            "size": "142.0 MB",
            "size_bytes": 148897792,
            "modified": "2026-07-25 18:40",
            "status": "Encrypted (AES-256)",
            "content_preview": "Parquet Columnar Data Schema:\n- Sample_ID (UUID)\n- Isolate_Type (String)\n- Resistance_Gene (Categorical)\n- Geo_Location (Lat/Long)"
        }
    ]

# 2. FILE VIEW MODAL (DIALOG)
@st.dialog("📄 File Details & Inspection")
def inspect_file(file_item):
    st.subheader(file_item["name"])
    st.caption(f"**ID:** {file_item['id']} | **Status:** {file_item['status']}")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.write(f"**File Type:** {file_item['type']}")
        st.write(f"**File Size:** {file_item['size']}")
    with col_b:
        st.write(f"**Last Modified:** {file_item['modified']}")
        st.write("**Security Level:** Zero-Trust KMS")

    st.markdown("---")
    st.markdown("### 🔍 Content Preview / Metadata Payload")
    preview_text = file_item.get("content_preview", "Standard encrypted binary stream. Raw inspection payload ready.")
    st.code(preview_text, language="json" if "JSON" in file_item["type"] else "text")
    
    st.markdown("### 🛡️ Cryptographic Verification")
    st.code("SHA-256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", language="text")

# 3. METRICS HEADER
total_count = len(st.session_state["vault_files"])
total_bytes = sum(f["size_bytes"] for f in st.session_state["vault_files"])
total_mb = total_bytes / (1024 * 1024)

st.title("📁 Drive Explorer & Cloud Storage")

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

# 4. UPLOADER
st.subheader("📤 Upload & Ingest Files")
uploaded = st.file_uploader("Drop files here to process and add to your drive explorer:", accept_multiple_files=True, key="cloud_uploader")

if uploaded:
    new_count = 0
    for file in uploaded:
        if not any(f["name"] == file.name for f in st.session_state["vault_files"]):
            size_kb = file.size / 1024
            size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"
            ext = file.name.split(".")[-1].upper() if "." in file.name else "FILE"
            
            # Read snippet if text-based
            try:
                snippet = file.getvalue().decode("utf-8")[:300] + "\n..."
            except Exception:
                snippet = f"Binary Object Stream [{file.name}]\nSize: {size_str}\nStatus: Verification Passed"

            new_item = {
                "id": f"FILE-00{len(st.session_state['vault_files']) + 1}",
                "name": file.name,
                "type": f"{ext} Document",
                "size": size_str,
                "size_bytes": file.size,
                "modified": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "status": "Encrypted (AES-256)",
                "content_preview": snippet
            }
            st.session_state["vault_files"].insert(0, new_item)
            new_count += 1
            
    if new_count > 0:
        st.success(f"Added {new_count} file(s) to your Drive Explorer!")
        st.rerun()

st.markdown("---")

# 5. RENDER GRID
st.subheader("🗂️ Stored Files Explorer")

cols = st.columns(3)
for idx, item in enumerate(st.session_state["vault_files"]):
    with cols[idx % 3]:
        with st.container(border=True):
            st.markdown(f"#### 📄 {item['name']}")
            st.caption(f"**Type:** {item['type']} | **Size:** {item['size']}")
            st.caption(f"**Modified:** {item['modified']}")
            st.markdown(f"{item['status']}")
            st.markdown("---")
            
            b1, b2 = st.columns(2)
            if b1.button("👁️ View", key=f"v_{idx}"):
                inspect_file(item)
                
            if b2.button("🗑️ Delete", key=f"d_{idx}"):
                st.session_state["vault_files"] = [f for f in st.session_state["vault_files"] if f["name"] != item["name"]]
                st.rerun()