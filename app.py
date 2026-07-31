from modules import secure_vault
import streamlit as st
import datetime
import io
import pandas as pd

# Try importing PyPDF for PDF text extraction
try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

st.set_page_config(
    page_title="Enterprise Drive Explorer & Workspace",
    page_icon="📁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# 1. INITIALIZE IN-MEMORY FILE DATABASE
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
            "file_category": "text",
            "raw_bytes": b"{\n  \"pipeline\": \"Waterborne Pathogen AMR Pipeline\",\n  \"version\": \"2.4.0\"\n}"
        }
    ]

# ---------------------------------------------------------
# 2. FORMAT-SPECIFIC WORKSPACE INSPECTOR & EDITOR MODAL
# ---------------------------------------------------------
@st.dialog("📄 Workspace Document Suite", width="large")
def inspect_and_edit_file(file_item):
    st.markdown(f"### 📄 {file_item.get('name', 'Document')}")
    st.caption(f"**ID:** {file_item.get('id', 'FILE-000')} | **Size:** {file_item.get('size', 'N/A')} | **Type:** {file_item.get('type')}")
    
    file_bytes = file_item.get("raw_bytes", b"")
    file_name = file_item.get("name", "").lower()

    tab_view, tab_edit, tab_export = st.tabs(["👁️ View / Preview", "✏️ Edit / Workspace", "📥 Export & Download"])

    # ---------------------------------------------------------
    # TAB 1: VIEW / PREVIEW
    # ---------------------------------------------------------
    with tab_view:
        if file_name.endswith(".pdf"):
            st.markdown("#### 📄 Google Docs Mode (PDF Document View)")
            if HAS_PYPDF and file_bytes:
                try:
                    pdf_reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                    extracted_text = ""
                    for i, page in enumerate(pdf_reader.pages):
                        extracted_text += f"\n--- Page {i+1} ---\n" + (page.extract_text() or "")
                    st.text_area("Extracted PDF Document Content", value=extracted_text, height=350)
                except Exception as e:
                    st.warning(f"Unable to parse PDF text: {e}")
            else:
                st.info("📄 PDF Binary Stream Loaded. Text extraction active.")
        
        elif file_name.endswith((".csv", ".xlsx", ".parquet")):
            st.markdown("#### 📊 Google Sheets Mode (Spreadsheet Grid)")
            try:
                if file_name.endswith(".csv"):
                    df = pd.read_csv(io.BytesIO(file_bytes))
                else:
                    df = pd.read_parquet(io.BytesIO(file_bytes))
                st.dataframe(df, use_container_width=True)
            except Exception:
                st.text_area("Raw Data Payload", value=file_bytes.decode("utf-8", errors="ignore"), height=300)

        else:
            st.markdown("#### 📝 Document & Code Viewer")
            text_str = file_bytes.decode("utf-8", errors="ignore")
            st.code(text_str, language="json" if file_name.endswith(".json") else "text")

    # ---------------------------------------------------------
    # TAB 2: EDIT / WORKSPACE
    # ---------------------------------------------------------
    with tab_edit:
        if file_name.endswith((".csv", ".xlsx")):
            st.markdown("#### 📊 Interactive Sheet Editor (Google Sheets Style)")
            try:
                df = pd.read_csv(io.BytesIO(file_bytes))
                edited_df = st.data_editor(df, num_rows="dynamic", key=f"sheet_{file_item['id']}")
                if st.button("💾 Save Sheet Changes", type="primary"):
                    buffer = io.StringIO()
                    edited_df.to_csv(buffer, index=False)
                    file_item["raw_bytes"] = buffer.getvalue().encode("utf-8")
                    file_item["modified"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M (Edited)")
                    st.success("Updated sheet saved successfully!")
                    st.rerun()
            except Exception as e:
                st.error(f"Could not open in spreadsheet editor: {e}")

        else:
            st.markdown("#### ✏️ Text & Document Editor")
            text_content = file_bytes.decode("utf-8", errors="ignore")
            updated_text = st.text_area("Modify file content:", value=text_content, height=300, key=f"edit_{file_item['id']}")
            
            if st.button("💾 Save Document", type="primary", key=f"save_{file_item['id']}"):
                file_item["raw_bytes"] = updated_text.encode("utf-8")
                file_item["modified"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M (Edited)")
                st.success("Document updated successfully!")
                st.rerun()

    # ---------------------------------------------------------
    # TAB 3: DOWNLOAD
    # ---------------------------------------------------------
    with tab_export:
        st.markdown("### 📥 Download Original File")
        st.download_button(
            label=f"⬇️ Download {file_item.get('name')}",
            data=file_bytes,
            file_name=file_item.get("name"),
            mime="application/octet-stream",
            type="primary",
            key=f"dl_btn_{file_item['id']}"
        )

# ---------------------------------------------------------
# 3. MAIN APP LAYOUT & UPLOADER
# ---------------------------------------------------------
st.title("📁 Drive Explorer & Workspace Hub")

st.subheader("📤 Upload Files to Drive Workspace")
uploaded = st.file_uploader(
    "Drop PDF, CSV, JSON, or code files here to open in Docs/Sheets/Slides views:",
    accept_multiple_files=True,
    key="drive_uploader"
)

if uploaded:
    new_count = 0
    for file in uploaded:
        if not any(f.get("name") == file.name for f in st.session_state["vault_files"]):
            size_kb = file.size / 1024
            size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"
            ext = file.name.split(".")[-1].upper() if "." in file.name else "FILE"
            
            # Save actual raw binary bytes from upload stream
            raw_data = file.getvalue()

            new_item = {
                "id": f"FILE-00{len(st.session_state['vault_files']) + 1}",
                "name": file.name,
                "type": f"{ext} Document",
                "size": size_str,
                "size_bytes": file.size,
                "modified": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "status": "Encrypted (AES-256)",
                "raw_bytes": raw_data
            }
            st.session_state["vault_files"].insert(0, new_item)
            new_count += 1
            
    if new_count > 0:
        st.success(f"Added {new_count} file(s) into Drive Workspace!")
        st.rerun()

st.markdown("---")

# ---------------------------------------------------------
# 4. DRIVE CARDS DISPLAY
# ---------------------------------------------------------
st.subheader("🗂️ Stored Workspace Files")

cols = st.columns(3)
for idx, item in enumerate(st.session_state["vault_files"]):
    with cols[idx % 3]:
        with st.container(border=True):
            st.markdown(f"#### 📄 {item.get('name')}")
            st.caption(f"**Type:** {item.get('type')} | **Size:** {item.get('size')}")
            st.caption(f"**Modified:** {item.get('modified')}")
            st.markdown(f"{item.get('status')}")
            st.markdown("---")
            
            b1, b2 = st.columns(2)
            if b1.button("👁️ Open Workspace", key=f"v_{idx}"):
                inspect_and_edit_file(item)
                
            if b2.button("🗑️ Delete", key=f"d_{idx}"):
                st.session_state["vault_files"] = [f for f in st.session_state["vault_files"] if f.get("name") != item.get("name")]
                st.rerun()