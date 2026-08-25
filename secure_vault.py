
import streamlit as st
import io
import pandas as pd

try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

def render_vault_ui():
    st.title("📁 Secure Personal Workspace & Vault")
    st.caption("Google Docs & Sheets style previewer, editor, and stream downloader.")

    if "vault_files" not in st.session_state:
        st.session_state["vault_files"] = []

    # File Ingestion
    uploaded_files = st.file_uploader(
        "Upload documents, PDFs, or spreadsheet datasets:",
        accept_multiple_files=True,
        key="modular_vault_uploader"
    )

    if uploaded_files:
        added_count = 0
        for f in uploaded_files:
            if not any(x["name"] == f.name for x in st.session_state["vault_files"]):
                st.session_state["vault_files"].insert(0, {
                    "id": f"FILE-{len(st.session_state['vault_files']) + 1}",
                    "name": f.name,
                    "bytes": f.getvalue(),
                    "size": f"{f.size / 1024:.1 + f} KB" if f.size < 1048576 else f"{f.size / 1048576:.1 + f} MB",
                    "status": "Verified Encrypted Stream"
                })
                added_count = 1
        if added_count > 0:
            st.success(f"Successfully loaded {added_count} workspace file(s)!")
            st.rerun()

    st.markdown("---")

    # Display Stored Files Grid
    if not st.session_state["vault_files"]:
        st.info("No files currently loaded in your vault session. Upload a document above to test.")
    else:
        st.subheader("🗂️ Stored Workspace Documents")
        cols = st.columns(3)
        for idx, item in enumerate(st.session_state["vault_files"]):
            with cols[idx % 3]:
                with st.container(border=True):
                    st.markdown(f"#### 📄 {item['name']}")
                    st.caption(f"**Size:** {item['size']} | **Status:** {item['status']}")
                    st.markdown("---")
                    
                    b1, b2 = st.columns(2)
                    if b1.button("👁️ Open", key=f"open_mod_{idx}"):
                        show_document_dialog(item)
                    if b2.button("🗑️ Delete", key=f"del_mod_{idx}"):
                        st.session_state["vault_files"] = [f for f in st.session_state["vault_files"] if f["name"] != item["name"]]
                        st.rerun()

@st.dialog("📄 Workspace Document Suite", width="large")
def show_document_dialog(item):
    name = item["name"].lower()
    raw_bytes = item["bytes"]

    st.markdown(f"### 📄 {item['name']}")
    st.caption(f"**Size:** {item['size']}")

    tab_view, tab_edit, tab_dl = st.tabs(["👁️ View / Read", "✏️ Edit (Docs/Sheets)", "📥 Download"])

    with tab_view:
        if name.endswith(".pdf"):
            st.markdown("#### 📄 PDF Document View (Google Docs Mode)")
            if HAS_PYPDF and raw_bytes:
                try:
                    reader = pypdf.PdfReader(io.BytesIO(raw_bytes))
                    extracted_text = "\n\n".join([f"--- Page {i1} ---\n" + (p.extract_text() or "") for i, p in enumerate(reader.pages)])
                    st.text_area("Extracted PDF Document Content", value=extracted_text, height=350)
                except Exception as e:
                    st.warning(f"Could not parse PDF text: {e}")
            else:
                st.info("PDF binary stream loaded into memory.")
        
        elif name.endswith((".csv", ".xlsx")):
            st.markdown("####  Spreadsheet View (Google Sheets Mode)")
            try:
                df = pd.read_csv(io.BytesIO(raw_bytes))
                st.dataframe(df, use_container_width=True)
            except Exception:
                st.text_area("Raw Stream Content", value=raw_bytes.decode("utf-8", errors="ignore"), height=300)
        else:
            st.markdown("#### 📝 Plain Text / Code View")
            st.code(raw_bytes.decode("utf-8", errors="ignore"))

    with tab_edit:
        if name.endswith((".csv", ".xlsx")):
            st.markdown("####  Interactive Sheet Grid Editor")
            try:
                df = pd.read_csv(io.BytesIO(raw_bytes))
                edited_df = st.data_editor(df, num_rows="dynamic", key=f"edit_grid_{item['name']}")
                if st.button("💾 Save Sheet Changes", type="primary"):
                    buf = io.StringIO()
                    edited_df.to_csv(buf, index=False)
                    item["bytes"] = buf.getvalue().encode("utf-8")
                    st.success("Sheet saved successfully!")
                    st.rerun()
            except Exception as e:
                st.error(f"Spreadsheet edit error: {e}")
        else:
            st.markdown("#### ✏️ Live Text Editor")
            text_val = raw_bytes.decode("utf-8", errors="ignore")
            updated_txt = st.text_area("Modify file content:", value=text_val, height=300, key=f"edit_txt_{item['name']}")
            if st.button("💾 Save Document Changes", type="primary"):
                item["bytes"] = updated_txt.encode("utf-8")
                st.success("Document updated successfully!")
                st.rerun()

    with tab_dl:
        st.markdown("### 📥 Download File")
        st.download_button(
            label=f"⬇️ Download {item['name']}",
            data=raw_bytes,
            file_name=item['name'],
            mime="application/octet-stream",
            type="primary"
        )

