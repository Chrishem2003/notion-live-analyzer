
import streamlit as st
import streamlit.components.v1 as components
import requests

def render_3dmol_html(pdb_data: str, style_type: str = "cartoon", color_scheme: str = "spectrum", show_surface: bool = False, height: int = 500) -> str:
    """Generates dynamic HTML/JS string to render PDB data with 3Dmol.js."""
    escaped_pdb = pdb_data.replace("`", "\\`").replace("$", "\\$")
    
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://3Dmol.csb.pitt.edu/build/3Dmol-min.js"></script>
        <style>
    /* --- GLOBAL SIDEBAR DARK THEMING OVERRIDE --- */
    [data-testid="stSidebar"], section[data-testid="stSidebar"] {
        background-color: #090d16 !important;
        border-right: 1px solid #1e293b !important;
    }
    
    /* Force all sidebar text, links, and headers to high-contrast off-white */
    [data-testid="stSidebar"] *, section[data-testid="stSidebar"] * {
        color: #f8fafc !important;
    }

    /* Target navigation links and text explicitly */
    [data-testid="stSidebarNav"] span, 
    [data-testid="stSidebarNav"] a,
    [data-testid="stSidebarNavLink"],
    [data-testid="stSidebarHeader"] {
        color: #f8fafc !important;
        font-weight: 600 !important;
    }

    /* Navigation item hover state */
    [data-testid="stSidebarNavLink"]:hover,
    [data-testid="stSidebarNav"] a:hover {
        background-color: #1e293b !important;
        border-radius: 8px !important;
    }

    /* Currently selected navigation item active state */
    [data-testid="stSidebarNavLink"][aria-current="page"],
    [data-testid="stSidebarNav"] a[aria-selected="true"] {
        background-color: #0284c7 !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
    }

    /* Custom form inputs inside sidebar */
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] .stMultiSelect label {
        color: #38bdf8 !important;
        font-weight: 700 !important;
    }
            body {{ margin: 0; padding: 0; overflow: hidden; background-color: #0e1117; }}
            #mol-container {{ width: 100vw; height: {height}px; position: relative; }}
        </style>
    </head>
    <body>
        <div id="mol-container"></div>
        <script>
            let viewer = null;
            document.addEventListener("DOMContentLoaded", function() {{
                let element = document.getElementById('mol-container');
                let config = {{ backgroundColor: '#0e1117' }};
                viewer = $3Dmol.createViewer(element, config);
                
                let pdbData = `{escaped_pdb}`;
                viewer.addModel(pdbData, "pdb");
                
                let styleObj = {{}};
                let styleType = "{style_type}";
                let colorScheme = "{color_scheme}";
                
                if (styleType === "cartoon") {{
                    styleObj = {{ cartoon: {{ color: colorScheme }} }};
                }} else if (styleType === "stick") {{
                    styleObj = {{ stick: {{ colorscheme: colorScheme }} }};
                }} else if (styleType === "sphere") {{
                    styleObj = {{ sphere: {{ colorscheme: colorScheme }} }};
                }} else {{
                    styleObj = {{ cartoon: {{ color: colorScheme }}, stick: {{}} }};
                }}
                
                viewer.setStyle({{}}, styleObj);
                
                if ("{str(show_surface).lower()}" === "true") {{
                    viewer.addSurface($3Dmol.SurfaceType.VDW, {{ opacity: 0.4, color: 'white' }});
                }}
                
                viewer.zoomTo();
                viewer.render();
            }});
        </script>
    </body>
    </html>
    """
    return html_code

def render_structure_viewer_tab():
    st.subheader("ðŸ” 3D Macromolecular Structure WebGL Viewer")
    st.caption("Interactive WebGL viewport powered by 3Dmol.js for structural proteomics.")

    col1, col2 = st.columns([1, 2.5])

    with col1:
        st.markdown("### Data Input")
        source = st.radio("Select Structure Source", ["RCSB PDB ID", "Upload .PDB File"], index=0)
        
        pdb_content = None
        
        if source == "RCSB PDB ID":
            pdb_id = st.text_input("Enter 4-letter PDB Code", value="1TUP", max_chars=4).upper().strip()
            if pdb_id:
                with st.spinner(f"Fetching `{pdb_id}` from RCSB..."):
                    url = f"https://files.rcsb.org/download/{pdb_id}.pdb"
                    resp = requests.get(url, timeout=10)
                    if resp.status_code == 200:
                        pdb_content = resp.text
                        st.success(f"Loaded PDB: `{pdb_id}` ({len(pdb_content):,} bytes)")
                    else:
                        st.error(f"Failed to fetch `{pdb_id}` from RCSB.")
        else:
            uploaded_file = st.file_uploader("Upload PDB file", type=["pdb"])
            if uploaded_file is not None:
                pdb_content = uploaded_file.getvalue().decode("utf-8")
                st.success("File uploaded successfully.")

        st.markdown("---")
        st.markdown("### Display Controls")
        render_style = st.selectbox("Render Style", ["cartoon", "stick", "sphere", "cartoon  stick"], index=0)
        color_scheme = st.selectbox("Color Palette", ["spectrum", "chain", "secondary structure", "residue"], index=0)
        
        scheme_map = {
            "spectrum": "spectrum",
            "chain": "chain",
            "secondary structure": "ssPyMol",
            "residue": "amino"
        }
        
        show_surface = st.checkbox("Render Van der Waals Surface", value=False)
        viewer_height = st.slider("Canvas Height (px)", min_value=350, max_value=800, value=500, step=50)

    with col2:
        if pdb_content:
            st.markdown("### Interactive 3D Viewport")
            html_content = render_3dmol_html(
                pdb_data=pdb_content,
                style_type=render_style,
                color_scheme=scheme_map[color_scheme],
                show_surface=show_surface,
                height=viewer_height
            )
            components.html(html_content, height=viewer_height  20)
            st.info("ðŸ” **Controls:** Click  Drag to rotate | Scroll to zoom | Right-Click  Drag to pan")
        else:
            st.warning("Enter a valid PDB ID or upload a structure file to render.")

