
"""
Google Sheets Integration + live read/write sync with Google Sheets.
Requires Google service account or OAuth2 credentials.
"""
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import streamlit as st
from datetime import datetime
import json
import os
import sys
import subprocess
import importlib

from modules.logging_utils import get_logger

logger = get_logger(__name__)

# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Auto-install Google Sheets dependencies Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
# This allows non-technical users to use Google Sheets without manual pip install

try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    HAS_GSPREAD = True
except ImportError:
    HAS_GSPREAD = False
    # Attempt automatic installation
    try:
        st.info("Ã°Å¸â€Â§ Installing Google Sheets dependencies (gspread, oauth2client, google-auth)...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "gspread", "oauth2client", "google-auth"],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            importlib.invalidate_caches()
            try:
                import gspread
                from oauth2client.service_account import ServiceAccountCredentials
                HAS_GSPREAD = True
                st.success("Ã¢Å“â€¦ Google Sheets dependencies installed successfully!")
                st.rerun()
            except ImportError:
                logger.warning(
                    "gspread/oauth2client still not importable after auto-install", exc_info=True
                )
                st.warning("Ã¢Å¡Â Ã¯Â¸Â Google Sheets packages installed but still not importable + restart the app.")
        else:
            logger.error("Google Sheets dependency auto-install failed: %s", result.stderr[:500])
            st.warning(f"Ã¢Å¡Â Ã¯Â¸Â Auto-install failed: {result.stderr[:200]}")
    except Exception as e:
        logger.exception("Google Sheets dependency auto-install raised an error")
        st.warning(f"Ã¢Å¡Â Ã¯Â¸Â Could not auto-install: {str(e)}")


class GoogleSheetsClient:
    """Google Sheets API client for reading and writing data."""

    SCOPE = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]

    def __init__(self, credentials: Optional[Dict] = None):
        self.client = None
        self.credentials = credentials

    def connect_with_service_account(self, credentials_dict: Dict) -> bool:
        """Connect to Google Sheets using a service account JSON."""
        if not HAS_GSPREAD:
            st.error("gspread not installed. Install with: pip install gspread oauth2client")
            return False

        try:
            creds = ServiceAccountCredentials.from_json_keyfile_dict(
                credentials_dict, self.SCOPE
            )
            self.client = gspread.authorize(creds)
            return True
        except Exception as e:
            st.error(f"Google Sheets connection error: {str(e)}")
            return False

    def connect_with_token(self, token: str) -> bool:
        """Connect using an access token (simplified)."""
        if not HAS_GSPREAD:
            st.error("gspread not installed.")
            return False
        try:
            self.client = gspread.Client(auth=lambda: token)
            self.client.login()
            return True
        except Exception as e:
            st.error(f"Connection error: {str(e)}")
            return False

    def list_sheets(self) -> List[Dict[str, str]]:
        """List all accessible spreadsheets."""
        if not self.client:
            return []
        try:
            sheets = self.client.openall()
            return [{"id": s.id, "title": s.title, "url": s.url} for s in sheets]
        except Exception as e:
            st.error(f"Error listing sheets: {str(e)}")
            return []

    def read_sheet(
        self,
        sheet_url_or_id: str,
        worksheet_name: Optional[str] = None,
        header_row: int = 1,
    ) -> Optional[pd.DataFrame]:
        """Read data from a Google Sheet into a DataFrame."""
        if not self.client:
            return None

        try:
            # Open by URL or ID
            if "docs.google.com" in sheet_url_or_id:
                sh = self.client.open_by_url(sheet_url_or_id)
            else:
                sh = self.client.open_by_key(sheet_url_or_id)

            # Get worksheet
            if worksheet_name:
                ws = sh.worksheet(worksheet_name)
            else:
                ws = sh.get_worksheet(0)

            # Get all values
            all_values = ws.get_all_values()

            if not all_values:
                return pd.DataFrame()

            # Use header row
            if header_row > 0 and len(all_values) >= header_row:
                headers = all_values[header_row - 1]
                data_rows = all_values[header_row:]
            else:
                headers = None
                data_rows = all_values

            # Remove empty trailing rows
            while data_rows and all(cell == "" for cell in data_rows[-1]):
                data_rows = data_rows[:-1]

            df = pd.DataFrame(data_rows, columns=headers)
            return df

        except Exception as e:
            st.error(f"Error reading sheet: {str(e)}")
            return None

    def write_sheet(
        self,
        df: pd.DataFrame,
        sheet_url_or_id: str,
        worksheet_name: str = "Data",
        create_if_missing: bool = True,
        overwrite: bool = False,
    ) -> bool:
        """Write a DataFrame to a Google Sheet."""
        if not self.client:
            return False

        try:
            # Open or create spreadsheet
            if "docs.google.com" in sheet_url_or_id:
                sh = self.client.open_by_url(sheet_url_or_id)
            else:
                try:
                    sh = self.client.open_by_key(sheet_url_or_id)
                except Exception:
                    if create_if_missing:
                        sh = self.client.create("Research Data Export")
                    else:
                        return False

            # Get or create worksheet
            try:
                ws = sh.worksheet(worksheet_name)
                if overwrite:
                    sh.del_worksheet(ws)
                    ws = sh.add_worksheet(title=worksheet_name, rows=len(df), cols=len(df.columns))
            except Exception:
                ws = sh.add_worksheet(title=worksheet_name, rows=len(df), cols=len(df.columns))

            # Write header  data
            cell_list = [df.columns.tolist()] + df.values.tolist()
            ws.update(cell_list)

            return True

        except Exception as e:
            st.error(f"Error writing to sheet: {str(e)}")
            return False

    def append_to_sheet(
        self,
        df: pd.DataFrame,
        sheet_url_or_id: str,
        worksheet_name: str = "Data",
    ) -> bool:
        """Append rows to an existing sheet."""
        if not self.client:
            return False

        try:
            if "docs.google.com" in sheet_url_or_id:
                sh = self.client.open_by_url(sheet_url_or_id)
            else:
                sh = self.client.open_by_key(sheet_url_or_id)

            ws = sh.worksheet(worksheet_name)
            ws.append_rows(df.values.tolist())
            return True

        except Exception as e:
            st.error(f"Error appending to sheet: {str(e)}")
            return False

    def get_worksheet_names(self, sheet_url_or_id: str) -> List[str]:
        """Get all worksheet names in a spreadsheet."""
        if not self.client:
            return []

        try:
            if "docs.google.com" in sheet_url_or_id:
                sh = self.client.open_by_url(sheet_url_or_id)
            else:
                sh = self.client.open_by_key(sheet_url_or_id)
            return [ws.title for ws in sh.worksheets()]
        except Exception as e:
            st.error(f"Error fetching worksheets: {str(e)}")
            return []


# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ UI Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

def render_google_sheets_ui(df: pd.DataFrame):
    """Render the Google Sheets integration UI."""
    st.markdown("## Ã°Å¸â€â€” Google Sheets Integration")
    st.markdown("*Connect, read from, and write to Google Sheets*")

    if not HAS_GSPREAD:
        st.warning("""
        Google Sheets libraries not installed. Install with:
        ```
        pip install gspread oauth2client google-auth
        ```
        """)
        return

    tab1, tab2 = st.tabs(["Ã°Å¸â€œÂ¥ Read from Sheets", "Ã°Å¸â€œÂ¤ Write to Sheets"])

    # Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Connect Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    st.sidebar.markdown("### Ã°Å¸â€â€˜ Google Sheets Auth")
    auth_method = st.sidebar.radio(
        "Auth method",
        options=["Service Account JSON", "Credentials File"],
        key="gs_auth_method"
    )

    client = GoogleSheetsClient()
    connected = False

    if auth_method == "Service Account JSON":
        sa_json_str = st.sidebar.text_area(
            "Paste service account JSON",
            height=150,
            key="gs_sa_json",
            help="Go to Google Cloud Console Ã¢â€ â€™ Service Accounts Ã¢â€ â€™ Create Key Ã¢â€ â€™ Download JSON"
        )
        if sa_json_str:
            try:
                sa_dict = json.loads(sa_json_str)
                connected = client.connect_with_service_account(sa_dict)
                if connected:
                    st.sidebar.success("Ã¢Å“â€¦ Connected to Google Sheets")
            except json.JSONDecodeError:
                st.sidebar.error("Invalid JSON format")
    else:
        creds_file = st.sidebar.file_uploader(
            "Upload credentials file",
            type=["json"],
            key="gs_creds_file"
        )
        if creds_file:
            try:
                sa_dict = json.loads(creds_file.read())
                connected = client.connect_with_service_account(sa_dict)
                if connected:
                    st.sidebar.success("Ã¢Å“â€¦ Connected to Google Sheets")
            except Exception as e:
                st.sidebar.error(f"Error: {str(e)}")

    if not connected:
        st.info("Ã°Å¸â€â€˜ Use the sidebar to connect your Google account or service account.")
        st.markdown("""
        ### How to set up Google Sheets access:
        1. Go to [Google Cloud Console](https://console.cloud.google.com)
        2. Create a new project or select existing
        3. Enable **Google Sheets API** and **Google Drive API**
        4. Create a **Service Account** Ã¢â€ â€™ Create Key Ã¢â€ â€™ Download JSON
        5. Share your Google Sheet with the service account email (viewer/editor)
        6. Paste the JSON in the sidebar
        """)
        return

    # Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ List available sheets Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    with st.expander("Ã°Å¸â€œâ€š Available Spreadsheets", expanded=False):
        sheets = client.list_sheets()
        if sheets:
            for s in sheets[:20]:
                st.markdown(f"- **{s['title']}** (`{s['id'][:20]}...`)")
            if len(sheets) > 20:
                st.caption(f"... and {len(sheets) - 20} more")
        else:
            st.info("No spreadsheets found. Create one first.")

    # Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ TAB 1: Read Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    with tab1:
        st.subheader("Ã°Å¸â€œÂ¥ Read Data from Google Sheets")

        sheet_input = st.text_input(
            "Sheet URL or ID",
            placeholder="https://docs.google.com/spreadsheets/d/... or the ID",
            key="gs_read_url"
        )

        if sheet_input:
            try:
                worksheet_names = client.get_worksheet_names(sheet_input)
                if worksheet_names:
                    ws_name = st.selectbox("Select worksheet", options=worksheet_names, key="gs_read_ws")
                    has_header = st.checkbox("Data has header row", value=True, key="gs_read_header")

                    if st.button("Ã°Å¸â€œÂ¥ Read from Sheet", type="primary"):
                        with st.spinner("Reading data..."):
                            read_df = client.read_sheet(sheet_input, ws_name, header_row=1 if has_header else 0)

                        if read_df is not None and not read_df.empty:
                            st.success(f"Ã¢Å“â€¦ Read {len(read_df)} rows Ãƒâ€” {len(read_df.columns)} columns")
                            st.dataframe(read_df.head(50), use_container_width=True, hide_index=True)

                            # Option to use as active data
                            if st.button(" Use This Data for Analysis", use_container_width=True):
                                st.session_state["active_df"] = read_df
                                st.session_state["data_source"] = "google_sheets"
                                st.success("Ã¢Å“â€¦ Data loaded! Go to other pages to analyze.")
                        else:
                            st.warning("No data found or unable to read sheet.")
            except Exception as e:
                st.error(f"Error accessing sheet: {str(e)}")

    # Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ TAB 2: Write Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    with tab2:
        st.subheader("Ã°Å¸â€œÂ¤ Write Data to Google Sheets")

        if df is not None and not df.empty:
            st.info(f"**Data to write**: {len(df)} rows Ãƒâ€” {len(df.columns)} columns from '{st.session_state.get('data_source', 'active dataset')}'")

            sheet_target = st.text_input(
                "Target Sheet URL or ID (or leave blank to create new)",
                placeholder="https://docs.google.com/spreadsheets/d/...",
                key="gs_write_url"
            )
            ws_target = st.text_input("Worksheet name", value="Sheet1", key="gs_write_ws")
            write_mode = st.radio("Write mode", ["Overwrite", "Append"], horizontal=True, key="gs_write_mode")

            if st.button("Ã°Å¸â€œÂ¤ Write to Sheet", type="primary"):
                with st.spinner("Writing data..."):
                    if write_mode == "Overwrite":
                        success = client.write_sheet(
                            df, sheet_target or "new", ws_target,
                            create_if_missing=True, overwrite=True
                        )
                    else:
                        success = client.append_to_sheet(df, sheet_target, ws_target)

                if success:
                    st.success("Ã¢Å“â€¦ Data written to Google Sheets successfully!")
                else:
                    st.error("Failed to write data. Check connection and permissions.")
        else:
            st.warning("No active dataset to write. Load or create data first.")


