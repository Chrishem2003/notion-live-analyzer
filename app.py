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
            "status": "Encrypted (AES-256)"
        },
        {
            "id": "FILE-002",
            "name": "Waterborne_Pathogen_Surveillance_Report.pdf",
            "type": "PDF Document",
            "size": "18.9 MB",
            "size_bytes": 19818086,
            "modified": "2026-07-28 09:15",
            "status": "Encrypted (Post-Quantum)"
        },
        {
            "id": "FILE-003",
            "name": "Regional_Antimicrobial_Resistance_Data.parquet",
            "type": "Dataset / Parquet",
            "size": "142.0 MB",
            "size_bytes": 148897792,
            "modified": "2026-07-25 18:40",
            "status": "Encrypted (AES-256)"
        }
    ]

# 2. CALCULATE LIVE METRICS
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

# 3. LIVE CLOUD UPLOADER (SESSION STATE PERSISTENCE)
st.subheader("📤 Upload & Ingest Files")

uploaded = st.file_uploader("Drop files here to process and add to your drive explorer:", accept_multiple_files=True, key="cloud_uploader")

if uploaded:
    new_count = 0
    for file in uploaded:
        # Prevent duplicating entries
        if not any(f["name"] == file.name for f in st.session_state["vault_files"]):
            size_kb = file.size / 1024
            size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"
            ext = file.name.split(".")[-1].upper() if "." in file.name else "FILE"
            
            new_item = {
                "id": f"FILE-00{len(st.session_state['vault_files']) + 1}",
                "name": file.name,
                "type": f"{ext} Document",
                "size": size_str,
                "size_bytes": file.size,
                "modified": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "status": "Encrypted (AES-256)"
            }
            # Add to top of grid
            st.session_state["vault_files"].insert(0, new_item)
            new_count += 1
            
    if new_count > 0:
        st.success(f"Added {new_count} file(s) to your Drive Explorer!")
        st.rerun()

st.markdown("---")

# 4. RENDER DRIVE GRID
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
                st.toast(f"Opening details for {item['name']}")
            if b2.button("🗑️ Delete", key=f"d_{idx}"):
                st.session_state["vault_files"] = [f for f in st.session_state["vault_files"] if f["name"] != item["name"]]
                st.rerun()

# --- NON-DESTRUCTIVE VAULT FILE INSPECTION PATCH ---
import io
try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

def safe_get_file_bytes(file_item):
    if "raw_bytes" in file_item and isinstance(file_item["raw_bytes"], bytes):
        return file_item["raw_bytes"]
    content = file_item.get("content", "")
    return content.encode("utf-8") if isinstance(content, str) else b""

def safe_render_file_preview(file_item):
    file_bytes = safe_get_file_bytes(file_item)
    file_name = file_item.get("name", "").lower()
    
    if file_name.endswith(".pdf"):
        if HAS_PYPDF and file_bytes:
            try:
                reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                text = "\n\n".join([f"--- Page {i+1} ---\n" + (p.extract_text() or "") for i, p in enumerate(reader.pages)])
                st.text_area("PDF Document Stream", value=text, height=350)
            except Exception as e:
                st.warning(f"Extracted raw byte stream (PDF parse warning: {e})")
        else:
            st.info("PDF stream loaded into buffer.")
    elif file_name.endswith((".csv", ".xlsx")):
        try:
            import pandas as pd
            df = pd.read_csv(io.BytesIO(file_bytes))
            st.dataframe(df, use_container_width=True)
        except Exception:
            st.text(file_bytes.decode("utf-8", errors="ignore"))
    else:
        st.code(file_bytes.decode("utf-8", errors="ignore"))
# --- END PATCH ---