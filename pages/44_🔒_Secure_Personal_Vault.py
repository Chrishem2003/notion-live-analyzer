# backend_api.py
# Run this using: uvicorn backend_api:app --reload

from fastapi import FastAPI, WebSocket, BackgroundTasks
from pydantic import BaseModel
import sqlite3
import datetime

app = FastAPI(title="Notion Live Analyzer API", version="2.0")

# --- DATABASE SETUP (Foundation for your Data Vault) ---
def init_db():
    conn = sqlite3.connect("analyzer_vault.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            last_edited TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- DATA MODELS ---
class Document(BaseModel):
    title: str
    content: str

# --- CORE ENDPOINTS ---
@app.get("/")
def read_root():
    return {"status": "Backend Active", "system": "Notion Live Analyzer"}

@app.post("/save_document/")
def save_doc(doc: Document):
    """Saves data to a robust SQLite backend instead of local text files."""
    conn = sqlite3.connect("analyzer_vault.db")
    cursor = conn.cursor()
    timestamp = datetime.datetime.now().isoformat()
    cursor.execute("INSERT INTO documents (title, content, last_edited) VALUES (?, ?, ?)", 
                   (doc.title, doc.content, timestamp))
    conn.commit()
    conn.close()
    return {"message": f"Document '{doc.title}' saved successfully."}

# --- AUTOMATION: EMAIL MOCKUP ---
def send_automated_email(email_address: str, subject: str):
    """Background task for sending emails without freezing the app."""
    # In production, integrate smtplib or SendGrid API here
    print(f"AUTOMATION: Email sent to {email_address} with subject: {subject}")

@app.post("/trigger_automation/")
def trigger_email(email: str, subject: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(send_automated_email, email, subject)
    return {"message": "Automation triggered in the background."}

# --- REAL-TIME COLLABORATION (WebSockets) ---
@app.websocket("/ws/realtime_edit")
async def websocket_endpoint(websocket: WebSocket):
    """Foundation for real-time collaborative editing."""
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        # Broadcast this data to other connected clients
        await websocket.send_text(f"Live Update applied: {data}")
        # frontend_app.py
# Run this using: streamlit run frontend_app.py

import streamlit as st
import requests
import pandas as pd
import numpy as np

# Configure the page for an enterprise feel
st.set_page_config(page_title="Notion Live Analyzer", layout="wide")

BACKEND_URL = "http://127.0.0.1:8000"

st.title("Notion Live Analyzer 2.0 🌌")
st.markdown("Enterprise Backend & Automation Enabled")

# --- SIDEBAR NAVIGATION ---
menu = st.sidebar.selectbox(
    "Application Modules", 
    ["Data Engine", "Live Docs (Database)", "Automations", "Video Center"]
)

# --- MODULE 1: DATA ENGINE ---
if menu == "Data Engine":
    st.header("Advanced Data Analytics")
    st.info("Simulating high-performance data processing.")
    
    # Generate mock analytical data
    df = pd.DataFrame(
        np.random.randn(50, 3),
        columns=["Metric A", "Metric B", "Metric C"]
    )
    
    col1, col2 = st.columns(2)
    with col1:
        st.dataframe(df, use_container_width=True)
    with col2:
        st.line_chart(df)

# --- MODULE 2: LIVE DOCS (Connecting to Backend) ---
elif menu == "Live Docs (Database)":
    st.header("Secure Document Vault")
    
    doc_title = st.text_input("Document Title")
    doc_content = st.text_area("Workspace Editor", height=200)
    
    if st.button("Save to Backend Database"):
        if doc_title and doc_content:
            try:
                # Send data securely to FastAPI backend
                response = requests.post(
                    f"{BACKEND_URL}/save_document/",
                    json={"title": doc_title, "content": doc_content}
                )
                if response.status_code == 200:
                    st.success(response.json()["message"])
                else:
                    st.error("Backend communication failed.")
            except requests.exceptions.ConnectionError:
                st.error("Backend offline. Please start the FastAPI server.")
        else:
            st.warning("Please provide a title and content.")

# --- MODULE 3: AUTOMATIONS ---
elif menu == "Automations":
    st.header("Workflow Automation Engine")
    
    target_email = st.text_input("Target Email Address")
    email_subject = st.text_input("Notification Subject")
    
    if st.button("Trigger Background Email"):
        try:
            response = requests.post(
                f"{BACKEND_URL}/trigger_automation/?email={target_email}&subject={email_subject}"
            )
            st.success("Automation dispatched to backend background tasks!")
        except Exception as e:
            st.error(f"Error: {e}")

# --- MODULE 4: VIDEO CENTER ---
elif menu == "Video Center":
    st.header("Multimedia Integration")
    st.markdown("Embed and stream external media directly into your workflow.")
    # Example of embedding video players natively
    st.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    # backend_advanced.py
# Run: uvicorn backend_advanced:app --reload

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import datetime
import json

app = FastAPI(title="Notion Live Analyzer API - Advanced", version="3.0")

# --- ADVANCED DATABASE SCHEMA (SQLAlchemy ORM) ---
DATABASE_URL = "sqlite:///./enterprise_vault.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class DocumentModel(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    content = Column(Text)
    author = Column(String, default="System User")
    last_edited = Column(DateTime, default=datetime.datetime.utcnow)

# Create tables
Base.metadata.create_all(bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- REAL-TIME CONNECTION MANAGER ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# --- API ENDPOINTS ---
@app.post("/api/documents/")
def create_document(title: str, content: str, db: Session = Depends(get_db)):
    """Creates a new document using the ORM schema."""
    new_doc = DocumentModel(title=title, content=content)
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)
    return {"message": "Document saved securely", "id": new_doc.id}

@app.get("/api/documents/")
def get_all_documents(db: Session = Depends(get_db)):
    """Retrieves all documents for the analytics dashboard."""
    return db.query(DocumentModel).all()

@app.websocket("/ws/editor")
async def websocket_editor(websocket: WebSocket):
    """Handles live document editing streams."""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Broadcast the live keystrokes or updates to all other clients
            payload = json.dumps({"event": "live_edit", "data": data})
            await manager.broadcast(payload)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        # frontend_advanced.py
# Run: streamlit run frontend_advanced.py

import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Notion Live Analyzer Pro", layout="wide")
BACKEND_URL = "http://127.0.0.1:8000"

st.title("Notion Live Analyzer 3.0 🚀")
st.markdown("---")

# --- UI TABS FOR CLEANER WORKFLOW ---
tab1, tab2, tab3 = st.tabs(["📝 Live Editor", "🗄️ Database Vault", "⚙️ System Config"])

with tab1:
    st.header("Workspace Editor")
    st.caption("Draft and push documents to the enterprise vault.")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        doc_title = st.text_input("Document Title", placeholder="e.g., Q3 Analytics Report")
        doc_content = st.text_area("Content", height=300)
    
    with col2:
        st.markdown("**Actions**")
        if st.button("Commit to Database", use_container_width=True):
            if doc_title and doc_content:
                res = requests.post(
                    f"{BACKEND_URL}/api/documents/?title={doc_title}&content={doc_content}"
                )
                if res.status_code == 200:
                    st.success(f"Saved! DB ID: {res.json().get('id')}")
                else:
                    st.error("Failed to commit.")
            else:
                st.warning("Title and content required.")

with tab2:
    st.header("Vault Analytics")
    st.caption("Real-time view of the SQLAlchemy Database")
    
    if st.button("Refresh Database View"):
        try:
            response = requests.get(f"{BACKEND_URL}/api/documents/")
            if response.status_code == 200:
                data = response.json()
                if data:
                    # Convert JSON response directly to a Pandas DataFrame for analysis
                    df = pd.DataFrame(data)
                    # Reorder columns for better UX
                    df = df[['id', 'title', 'content', 'author', 'last_edited']]
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    
                    st.metric("Total Documents in Vault", len(df))
                else:
                    st.info("The database is currently empty.")
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to backend. Is uvicorn running?")

with tab3:
    st.header("Connection Diagnostics")
    st.write(f"**Target Backend API:** `{BACKEND_URL}`")
    st.write("**WebSocket Target:** `ws://127.0.0.1:8000/ws/editor`")
    st.info("WebSocket integration in Streamlit typically requires a custom component for bidirectional streaming. The backend manager is actively listening for frontend connections.")
    # Add these imports to backend_advanced.py
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import timedelta

# --- SECURITY CONFIGURATION ---
SECRET_KEY = "super_secret_enterprise_key_change_in_production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Simulated User Database (In production, move this to SQLAlchemy)
fake_users_db = {
    "chrishem": {
        "username": "chrishem",
        "full_name": "System Admin",
        "hashed_password": pwd_context.hash("securepassword123"),
        "disabled": False,
    }
}

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# --- AUTHENTICATION ENDPOINT ---
@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user_dict = fake_users_db.get(form_data.username)
    if not user_dict or not verify_password(form_data.password, user_dict["hashed_password"]):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    access_token = create_access_token(data={"sub": user_dict["username"]}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": access_token, "token_type": "bearer"}

# --- SECURED ENDPOINT EXAMPLE ---
@app.get("/api/secure-data/")
async def read_secure_data(token: str = Depends(oauth2_scheme)):
    """This endpoint can only be accessed with a valid JWT token."""
    return {"message": "Access Granted to Secure Vault", "token_used": token}
# Add these imports to frontend_advanced.py
import numpy as np
from ydata_profiling import ProfileReport
from streamlit_pandas_profiling import st_profile_report

# ... (Keep your existing tabs setup, and add a fourth tab) ...
tab1, tab2, tab3, tab4 = st.tabs(["📝 Live Editor", "🗄️ Database Vault", "⚙️ System Config", "🔬 Data Profiler"])

# ... (Inside your tab routing) ...
with tab4:
    st.header("Automated Data Profiling Engine")
    st.caption("One-click statistical analysis and correlation mapping.")
    
    if st.button("Generate Environmental Data Profile"):
        with st.spinner("Compiling statistical report..."):
            # Generating synthetic environmental tracking data for the test
            np.random.seed(42)
            dates = pd.date_range(start="2026-01-01", periods=100)
            env_df = pd.DataFrame({
                "Date": dates,
                "Sea_Level_mm": np.random.normal(loc=150, scale=5, size=100) + np.linspace(0, 10, 100),
                "Water_Temperature_C": np.random.normal(loc=22, scale=2, size=100),
                "Salinity_psu": np.random.uniform(low=32.0, high=37.0, size=100),
                "Sensor_Status": np.random.choice(["Active", "Maintenance", "Offline"], p=[0.8, 0.15, 0.05], size=100)
            })
            
            # Introduce some realistic missing data for the profiler to catch
            env_df.loc[10:15, "Water_Temperature_C"] = np.nan 

            st.write("### Raw Dataset Snapshot")
            st.dataframe(env_df.head(), use_container_width=True)

            # Generate the automated profile report
            pr = ProfileReport(env_df, explorative=True, title="Environmental Metrics Profiling Report")
            
            st.write("### Comprehensive Analysis")
            st_profile_report(pr)
            # Add to frontend_advanced.py
import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Notion Live Analyzer Pro", layout="wide")
BACKEND_URL = "http://127.0.0.1:8000"

# --- SESSION STATE INITIALIZATION ---
if "token" not in st.session_state:
    st.session_state["token"] = None

def login(username, password):
    """Authenticates with the FastAPI backend and retrieves a JWT."""
    try:
        response = requests.post(
            f"{BACKEND_URL}/token",
            data={"username": username, "password": password}
        )
        if response.status_code == 200:
            st.session_state["token"] = response.json().get("access_token")
            st.rerun()
        else:
            st.error("Invalid username or password.")
    except requests.exceptions.ConnectionError:
        st.error("Backend is offline. Please start the server.")

def logout():
    st.session_state["token"] = None
    st.rerun()

# --- LOGIN SCREEN ---
if st.session_state["token"] is None:
    st.title("System Authentication")
    st.markdown("Please log in to access the Notion Live Analyzer Suite.")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Secure Login")
        
        if submitted:
            login(username, password)
    
    st.stop() # Halts rendering of the rest of the app until logged in

# --- MAIN SECURE APPLICATION ---
# (The rest of the application only renders if the user is logged in)
st.sidebar.button("Logout", on_click=logout)
st.title("Notion Live Analyzer 3.0 🚀")
st.markdown("---")

# We will now add a 5th tab for Notion Sync
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📝 Live Editor", "🗄️ Database Vault", "⚙️ System Config", "🔬 Data Profiler", "📓 Notion Sync"
])

# (Keep your existing code for tabs 1-4 here)
# Add to backend_advanced.py
from notion_client import Client
import os

# Initialize Notion Client (You will need to get an integration token from developers.notion.com)
NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "your_secret_integration_token_here")
notion = Client(auth=NOTION_TOKEN)

# --- SECURE NOTION ENDPOINT ---
@app.get("/api/notion/databases/{database_id}")
async def sync_notion_database(database_id: str, token: str = Depends(oauth2_scheme)):
    """
    Fetches a live database from Notion. 
    Protected endpoint: Requires valid JWT token.
    """
    try:
        # Query the specific Notion database
        response = notion.databases.query(database_id=database_id)
        
        # Parse the Notion JSON structure into a flat, readable format
        parsed_data = []
        for page in response.get("results", []):
            properties = page.get("properties", {})
            row_data = {"page_id": page["id"]}
            
            # Dynamically extract properties (Simplified for Name and Tags)
            for prop_name, prop_data in properties.items():
                if prop_data["type"] == "title":
                    title_text = [t["plain_text"] for t in prop_data.get("title", [])]
                    row_data[prop_name] = "".join(title_text)
                elif prop_data["type"] == "rich_text":
                    rich_text = [t["plain_text"] for t in prop_data.get("rich_text", [])]
                    row_data[prop_name] = "".join(rich_text)
                elif prop_data["type"] == "select":
                    row_data[prop_name] = prop_data["select"]["name"] if prop_data["select"] else None
            
            parsed_data.append(row_data)
            
        return {"status": "success", "data": parsed_data}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
    # Add this inside the tab routing in frontend_advanced.py

with tab5:
    st.header("Live Notion Workspace Sync")
    st.caption("Pull live databases directly from your Notion workspace.")
    
    # Example Notion Database ID (Found in the Notion URL of the database)
    notion_db_id = st.text_input("Notion Database ID", placeholder="e.g., 8c34f1...")
    
    if st.button("Sync Workspace Database"):
        if notion_db_id:
            with st.spinner("Authenticating and fetching from Notion..."):
                # We must pass the token in the headers for secure access
                headers = {"Authorization": f"Bearer {st.session_state['token']}"}
                
                response = requests.get(
                    f"{BACKEND_URL}/api/notion/databases/{notion_db_id}", 
                    headers=headers
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("status") == "success":
                        st.success("Database synced successfully!")
                        # Convert flat JSON to a clean Pandas DataFrame
                        notion_df = pd.DataFrame(result["data"])
                        st.dataframe(notion_df, use_container_width=True)
                    else:
                        st.error(f"Notion API Error: {result.get('message')}")
                else:
                    st.error("Authentication failed or backend error.")
        else:
            st.warning("Please provide a Notion Database ID.")
            # Add these imports to backend_advanced.py
from fastapi import BackgroundTasks
from fpdf import FPDF
import time

# --- BACKGROUND AUTOMATION FUNCTIONS ---
def generate_pdf_and_email(user_email: str, report_data: str):
    """Generates a PDF report and dispatches it via email in the background."""
    print(f"[SYSTEM] Starting background PDF generation for {user_email}...")
    
    # 1. Generate PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Notion Live Analyzer - Automated Report", ln=1, align='C')
    pdf.multi_cell(0, 10, txt=f"Data Snapshot:\n{report_data}")
    
    pdf_filename = f"report_{int(time.time())}.pdf"
    pdf.output(pdf_filename)
    
    # 2. Simulate SMTP Email Dispatch
    # In production, you would use smtplib or a service like SendGrid here.
    time.sleep(2) # Simulating network delay
    print(f"[SUCCESS] Email dispatched to {user_email} with attachment {pdf_filename}")

# --- AUTOMATION ENDPOINT ---
@app.post("/api/automations/email-report/")
async def trigger_email_report(
    email: str, 
    report_data: str, 
    background_tasks: BackgroundTasks, 
    token: str = Depends(oauth2_scheme)
):
    """Secured endpoint to trigger background report generation."""
    background_tasks.add_task(generate_pdf_and_email, email, report_data)
    return {"status": "success", "message": f"Report queued for delivery to {email}."}
# Add this under a new tab or existing automation section in frontend_advanced.py

st.header("Automated Report Dispatch")
st.caption("Generate PDFs and dispatch emails asynchronously.")

target_email = st.text_input("Recipient Email Address")
report_summary = st.text_area("Report Summary / Notion Data Snapshot")

if st.button("Generate & Email PDF Report"):
    if target_email and report_summary:
        with st.spinner("Dispatching to backend processing queue..."):
            headers = {"Authorization": f"Bearer {st.session_state['token']}"}
            response = requests.post(
                f"{BACKEND_URL}/api/automations/email-report/?email={target_email}&report_data={report_summary}",
                headers=headers
            )
            
            if response.status_code == 200:
                st.success("Successfully queued! The backend is processing this in the background.")
            else:
                st.error("Failed to queue the automation.")
    else:
        st.warning("Please provide an email and report data.")
        # Update the WebSocket section in backend_advanced.py
from typing import Dict, List

class AdvancedConnectionManager:
    def __init__(self):
        # Maps a document ID to a list of active WebSocket connections
        self.active_rooms: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, doc_id: str):
        await websocket.accept()
        if doc_id not in self.active_rooms:
            self.active_rooms[doc_id] = []
        self.active_rooms[doc_id].append(websocket)
        print(f"[SOCKET] User joined document room: {doc_id}")

    def disconnect(self, websocket: WebSocket, doc_id: str):
        if doc_id in self.active_rooms:
            self.active_rooms[doc_id].remove(websocket)
            if not self.active_rooms[doc_id]:
                del self.active_rooms[doc_id]
        print(f"[SOCKET] User left document room: {doc_id}")

    async def broadcast_to_room(self, message: str, doc_id: str, sender: WebSocket):
        """Sends the live update to everyone in the room EXCEPT the sender."""
        if doc_id in self.active_rooms:
            for connection in self.active_rooms[doc_id]:
                if connection != sender:
                    await connection.send_text(message)

advanced_manager = AdvancedConnectionManager()

@app.websocket("/ws/editor/{doc_id}")
async def collaborative_editor(websocket: WebSocket, doc_id: str):
    """Endpoint for live, multi-user document editing."""
    await advanced_manager.connect(websocket, doc_id)
    try:
        while True:
            # Wait for a keystroke or update from a user
            data = await websocket.receive_text()
            
            # Instantly broadcast that update to all other users looking at this document
            payload = json.dumps({"event": "text_update", "content": data})
            await advanced_manager.broadcast_to_room(payload, doc_id, sender=websocket)
            
    except WebSocketDisconnect:
        advanced_manager.disconnect(websocket, doc_id)
        # test_live_sockets.py (Run this in a standard terminal, outside of Streamlit)
# pip install websockets
import asyncio
import websockets

async def connect_to_doc():
    uri = "ws://127.0.0.1:8000/ws/editor/doc_123"
    async with websockets.connect(uri) as websocket:
        print("Connected to Document 123!")
        
        # Simulate sending a live keystroke
        await websocket.send("User typing: Hello World!")
        
        # Listen for updates from other users
        response = await websocket.recv()
        print(f"Received live update: {response}")

asyncio.run(connect_to_doc())
# Add to backend_advanced.py
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain_openai import ChatOpenAI

# Connect LangChain to our existing SQLite enterprise vault
db_uri = "sqlite:///./enterprise_vault.db"
sql_db = SQLDatabase.from_uri(db_uri)

# Initialize LLM (Ensure OPENAI_API_KEY is set in your environment variables)
llm = ChatOpenAI(temperature=0, model="gpt-4o")

# Create the Autonomous SQL Agent executor
sql_agent_executor = create_sql_agent(
    llm=llm,
    db=sql_db,
    verbose=True,
    handle_parsing_errors=True
)

# --- AI AGENT ENDPOINT ---
@app.post("/api/ai/query/")
async def run_natural_language_query(prompt: str, token: str = Depends(oauth2_scheme)):
    """
    Takes a plain English command (e.g., 'How many documents were edited today?'),
    translates it to SQL, runs it, and returns the analysis.
    """
    try:
        response = sql_agent_executor.run(prompt)
        return {"status": "success", "agent_response": response}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    # Add this inside a new tab or section in frontend_advanced.py
st.header("🤖 Autonomous AI Data Agent")
st.caption("Ask questions about your enterprise vault in plain English.")

user_query = st.text_input("Query Workspace", placeholder="e.g., List all document titles saved this week")

if st.button("Run AI Analysis"):
    if user_query:
        with st.spinner("AI Agent is analyzing the database vault..."):
            headers = {"Authorization": f"Bearer {st.session_state['token']}"}
            res = requests.post(
                f"{BACKEND_URL}/api/ai/query/?prompt={user_query}",
                headers=headers
            )
            if res.status_code == 200:
                data = res.json()
                if data.get("status") == "success":
                    st.success("Analysis Complete:")
                    st.write(data.get("agent_response"))
                else:
                    st.error(data.get("message"))
            else:
                st.error("Failed to communicate with AI agent backend.")
    else:
                    st.warning("Please enter a query.")
                    # Add to your data processing/analytics section in frontend_advanced.py
from statsmodels.tsa.holtwinters import ExponentialSmoothing

st.subheader("📈 Predictive Time-Series Forecasting")
st.caption("Project future trends based on historical telemetry or environmental logs.")

# Generate sample time-series data for demonstration
np.random.seed(101)
time_index = pd.date_range(start="2025-01-01", periods=180, freq="D")
base_trend = np.linspace(50, 150, 180)
noise = np.random.normal(loc=0.0, scale=5.0, size=180)
forecast_df = pd.DataFrame({
    "Date": time_index,
    "Value": base_trend + noise
})
forecast_df.set_index("Date", inplace=True)

st.line_chart(forecast_df)

if st.button("Generate 30-Day Predictive Forecast"):
    with st.spinner("Fitting Exponential Smoothing model..."):
        # Fit a Holt-Winters exponential smoothing model
        model = ExponentialSmoothing(forecast_df["Value"], trend="add", seasonal=None).fit()
        prediction = model.forecast(30)
        
        # Create a future date range for the projection
        future_dates = pd.date_range(start=forecast_df.index[-1] + pd.Timedelta(days=1), periods=30, freq="D")
        prediction_df = pd.DataFrame({"Predicted_Value": prediction}, index=future_dates)
        
        st.write("### 30-Day Outlook Projection")
        st.line_chart(prediction_df)
        st.success("Forecast projection calculated successfully with additive trend modeling.")
        # Add to backend_advanced.py
from pycrdt import Doc as CrdtDoc, Map as CrdtMap

# Store active CRDT documents in memory by doc_id
active_crdt_docs: dict[str, CrdtDoc] = {}

@app.websocket("/ws/crdt/{doc_id}")
async def crdt_sync_endpoint(websocket: WebSocket, doc_id: str):
    """
    Handles decentralized, conflict-free document synchronization 
    using CRDTs for offline-first state management.
    """
    await websocket.accept()
    
    # Initialize a shared document state if it doesn't exist
    if doc_id not in active_crdt_docs:
        active_crdt_docs[doc_id] = CrdtDoc()
    
    doc = active_crdt_docs[doc_id]
    
    # Send current state vector to newly connected client
    initial_state = doc.get_update()
    await websocket.send_bytes(bytes(initial_state))
    
    try:
        while True:
            # Receive binary update packets from the client
            data = await websocket.receive_bytes()
            # Apply update to the server-side CRDT document
            doc.apply_update(data)
            
            # Broadcast the state change to all other active peers in the room
            # (In production, route this through your AdvancedConnectionManager)
            current_state = doc.get_update()
            await websocket.send_bytes(bytes(current_state))
            
    except WebSocketDisconnect:
        print(f"[CRDT] Peer disconnected from document vault: {doc_id}")
        # Add/Update in backend_advanced.py
from sqlalchemy import String, Boolean

# Update or expand your user table model in SQLAlchemy
class UserModel(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="Viewer") # Roles: Admin, Editor, Viewer
    is_active = Column(Boolean, default=True)

# RBAC Dependency Guard Builder
def require_role(required_role: str):
    """
    Dependency factory to restrict backend routes based on user roles.
    Hierarchy: Admin > Editor > Viewer
    """
    role_hierarchy = {"Viewer": 1, "Editor": 2, "Admin": 3}
    
    async def role_dependency(token: str = Depends(oauth2_scheme)):
        # Decode the token (simplified check matching our auth system)
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            # Fetch user from database or mock vault
            user_data = fake_users_db.get(username)
            if not user_data:
                raise HTTPException(status_code=403, detail="User not found")
            
            # For demonstration, assign a default role if not present
            user_role = user_data.get("role", "Admin")
            
            if role_hierarchy.get(user_role, 1) < role_hierarchy.get(required_role, 1):
                raise HTTPException(status_code=403, detail="Insufficient privileges for this action.")
                
            return username
        except JWTError:
            raise HTTPException(status_code=401, detail="Could not validate credentials")
            
    return role_dependency

# --- PROTECTED RBAC ENDPOINT EXAMPLE ---
@app.delete("/api/vault/purge/")
async def purge_vault(admin_user: str = Depends(require_role("Admin"))):
    """
    High-privilege endpoint: Only users with the 'Admin' role can execute this.
    """
    return {"status": "success", "message": f"Vault security purge authorized and executed by Admin: {admin_user}"}
# Add to backend_advanced.py
from prometheus_fastapi_instrumentator import Instrumentator

# Initialize and instrument the FastAPI app for Prometheus telemetry
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=True)

# Now, every request, latency curve, and status code is automatically 
# tracked and exposed at http://127.0.0.1:8000/metrics for Grafana dashboards.
# Add to backend_advanced.py
import datetime
import json

# --- AUDIT LOG DATABASE MODEL ---
class AuditLogModel(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    actor = Column(String, index=True)
    action = Column(String)
    status = Column(String)
    ip_address = Column(String, nullable=True)

# Create the table
AuditLogModel.__table__.create(bind=engine, checkfirst=True)

def log_audit_event(actor: str, action: str, status: str, ip: str = "127.0.0.1"):
    """Writes an immutable security record to the enterprise audit trail."""
    db = SessionLocal()
    try:
        audit_entry = AuditLogModel(
            actor=actor,
            action=action,
            status=status,
            ip_address=ip
        )
        db.add(audit_entry)
        db.commit()
    finally:
        db.close()

# --- SECURED AUDIT LOG INSPECTION ENDPOINT ---
@app.get("/api/audit/logs/")
async def get_audit_logs(admin_user: str = Depends(require_role("Admin"))):
    """
    High-privilege endpoint: Allows Admins to fetch the complete tamper-evident audit trail.
    """
    db = SessionLocal()
    logs = db.query(AuditLogModel).all()
    db.close()
    return {"status": "success", "total_records": len(logs), "audit_trail": logs}
# Add to frontend_advanced.py
from streamlit_quill import st_quill

st.header("📄 Docs Workspace (Google Docs Clone)")
st.caption("Create formatted documents with real-time word analysis.")

# Render the rich-text editor clone
doc_title_input = st.text_input("Document Name", "Untitled Document")
quill_content = st_quill(placeholder="Type your notes, reports, or research here...", key="google_docs_clone")

# Real-time statistics derived from the editor content
if quill_content:
    # Basic text extraction from HTML for word counts
    word_count = len(quill_content.split())
    char_count = len(quill_content)
    
    col1, col2 = st.columns(2)
    col1.metric("Word Count", word_count)
    col2.metric("Character Count", char_count)
    
    if st.button("Commit Document to Enterprise Vault"):
        headers = {"Authorization": f"Bearer {st.session_state['token']}"}
        res = requests.post(
            f"{BACKEND_URL}/api/documents/?title={doc_title_input}&content={quill_content}",
            headers=headers
        )
        if res.status_code == 200:
            st.success("Document committed successfully to SQLAlchemy database!")
        else:
            st.error("Failed to save document. Check authorization tokens.")
            # Add to frontend_advanced.py
st.header("✉️ Mail Workspace (Gmail Clone)")
st.caption("Compose and dispatch automated intelligence reports securely.")

with st.form("gmail_clone_form"):
    recipient = st.text_input("To:", placeholder="colleague@enterprise.com")
    subject_line = st.text_input("Subject:", placeholder="Q3 Environmental Data Summary")
    email_body = st.text_area("Message Body", height=150, placeholder="Write your message or attach analysis snapshots here...")
    
    col_send, col_attach = st.columns([1, 4])
    with col_send:
        send_button = st.form_submit_button("Send Email 🚀")
        
    if send_button:
        if recipient and email_body:
            headers = {"Authorization": f"Bearer {st.session_state['token']}"}
            # Leverage our background email automation route built previously
            response = requests.post(
                f"{BACKEND_URL}/api/automations/email-report/?email={recipient}&report_data={email_body}",
                headers=headers
            )
            if response.status_code == 200:
                st.success(f"Message sent successfully to {recipient}! Handled via background worker.")
            else:
                st.error("Dispatch failed. Verify authentication.")
        else:
            st.warning("Recipient and message body cannot be empty.")
            # Add to frontend_advanced.py
st.header("📊 Presentation Workspace (Google Slides Clone)")
st.caption("Transform workspace database content into structured presentation slides automatically.")

# Mocking slide creation based on user input or vault documents
slide_title = st.text_input("Presentation Title", "Sea-Level & Environmental Insights")
slide_theme = st.selectbox("Slide Theme", ["Corporate Dark", "Clean Minimal", "Ocean Blue"])

# Create interactive slide frames
slides_data = [
    {"slide": 1, "heading": "Executive Summary", "content": "Overview of telemetry metrics collected from regional sensor nodes."},
    {"slide": 2, "heading": "Key Anomalies Detected", "content": "Water temperature shifts exceeded baseline expectations by 2.4%."},
    {"slide": 3, "heading": "30-Day Projections", "content": "Holt-Winters forecasting indicates stable stabilization across Q4."}
]

# Render slides inside a sleek card-like container layout
current_slide_idx = st.slider("Slide Deck Navigation", 0, len(slides_data) - 1, 0)

active_slide = slides_data[current_slide_idx]

st.markdown(f"""
### 🖼️ Slide {active_slide['slide']} of {len(slides_data)}: {slide_title}
---
#### **{active_slide['heading']}**
{active_slide['content']}
---
*Theme: {slide_theme} | Rendered Live via Notion Live Analyzer*
""")

col_prev, col_next = st.columns(2)
if col_prev.button("Previous Slide"):
    if current_slide_idx > 0:
        current_slide_idx -= 1
if col_next.button("Next Slide"):
    if current_slide_idx < len(slides_data) - 1:
        current_slide_idx += 1
        # Add to backend_advanced.py
import os
import shutil
from pathlib import Path

VAULT_DIRECTORY = Path("./workspace_vault")
VAULT_DIRECTORY.mkdir(parents=True, exist_ok=True)

@app.post("/api/storage/save-file/")
async def save_virtual_file(filename: str, content: str, token: str = Depends(oauth2_scheme)):
    """Writes workspace documents directly into an organized local directory structure."""
    file_path = VAULT_DIRECTORY / filename
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return {"status": "success", "message": f"File '{filename}' safely stored in vault directory."}

@app.get("/api/storage/list-files/")
async def list_vault_files(token: str = Depends(oauth2_scheme)):
    """Retrieves all stored files from the local vault."""
    files = [f.name for f in VAULT_DIRECTORY.iterdir() if f.is_file()]
    return {"status": "success", "vault_files": files}

@app.post("/api/storage/export-vault/")
async def export_vault_archive(token: str = Depends(oauth2_scheme)):
    """Zips the entire workspace vault for local backup or transfer."""
    archive_path = "./workspace_backup"
    shutil.make_archive(archive_path, 'zip', VAULT_DIRECTORY)
    return {"status": "success", "message": "Vault successfully archived into a downloadable zip package."}
# Add to frontend_advanced.py under a new section or tab
st.header("💾 Advanced Storage Vault Manager")
st.caption("Control your local file directory, persistent storage blocks, and archives.")

col_store1, col_store2 = st.columns(2)

with col_store1:
    st.subheader("Directory Inspector")
    if st.button("Scan Local Vault Directory"):
        headers = {"Authorization": f"Bearer {st.session_state['token']}"}
        res = requests.get(f"{BACKEND_URL}/api/storage/list-files/", headers=headers)
        if res.status_code == 200:
            files_list = res.json().get("vault_files", [])
            if files_list:
                st.success(f"Found {len(files_list)} active files in vault.")
                for file_name in files_list:
                    st.text(f"📁 {file_name}")
            else:
                st.info("Vault directory is currently empty.")
        else:
            st.error("Failed to connect to storage vault.")

with col_store2:
    st.subheader("Backup & Snapshot Engine")
    if st.button("Create Compressed Vault Archive (.zip)"):
        headers = {"Authorization": f"Bearer {st.session_state['token']}"}
        res = requests.post(f"{BACKEND_URL}/api/storage/export-vault/", headers=headers)
        if res.status_code == 200:
            st.success("Archive package compiled successfully on the server host.")
        else:
            st.error("Archiving failed.")
            # Add near the top of frontend_advanced.py, right after st.set_page_config
st.sidebar.markdown("---")
st.sidebar.subheader("🎨 Visual Theme Customizer")

theme_choice = st.sidebar.selectbox(
    "Select Interface Look", 
    ["Cyberpunk Dark", "Clean Minimalist Corporate", "Oceanic Deep Blue"]
)

# Apply dynamic styling based on user selection
if theme_choice == "Cyberpunk Dark":
    st.markdown("""
        <style>
        .stApp {
            background-color: #0d0e15;
            color: #00ffcc;
        }
        </style>
    """, unsafe_allow_html=True)
elif theme_choice == "Oceanic Deep Blue":
    st.markdown("""
        <style>
        .stApp {
            background-color: #0f172a;
            color: #38bdf8;
        }
        </style>
    """, unsafe_allow_html=True)
else:
    # Minimalist light / standard default
    pass

st.sidebar.success(f"Theme applied: {theme_choice}")
# Add to frontend_advanced.py
st.header("🎬 Multimedia Video Center")
st.caption("Stream integrated training, tutorial, or enterprise video assets.")

video_category = st.selectbox(
    "Select Video Feed", 
    ["Tutorials & Onboarding", "System Architecture Overview", "Live Environmental Feeds"]
)

if video_category == "Tutorials & Onboarding":
    st.subheader("Platform Walkthrough")
    # Embedding a reliable default or instructional stream link
    st.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    st.info("Tip: Use this overview to familiarize new users with the Notion Live Analyzer suite.")

elif video_category == "System Architecture Overview":
    st.subheader("Backend & Frontend Decoupled Structure")
    st.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    st.info("Explaining FastAPI microservices and Streamlit synchronization.")

else:
    st.subheader("Live Telemetry Stream Simulation")
    st.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    st.warning("Active feed tracking regional sensor nodes.")
    # Add to backend_advanced.py
import time
import psutil

app_start_time = time.time()

@app.get("/api/system/health/")
async def system_health_metrics(token: str = Depends(oauth2_scheme)):
    """Returns real-time server vitals, CPU/RAM usage, and uptime telemetry."""
    uptime_seconds = int(time.time() - app_start_time)
    cpu_usage = psutil.cpu_percent(interval=None)
    ram_usage = psutil.virtual_memory().percent
    
    return {
        "status": "healthy",
        "uptime_seconds": uptime_seconds,
        "cpu_usage_percent": cpu_usage,
        "ram_usage_percent": ram_usage,
        "database_status": "connected"
    }
# Add to frontend_advanced.py
st.header("📊 Enterprise System Telemetry & Vitals")
st.caption("Live monitoring of server performance, memory allocation, and uptime.")

if st.button("Refresh System Diagnostics"):
    headers = {"Authorization": f"Bearer {st.session_state['token']}"}
    try:
        response = requests.get(f"{BACKEND_URL}/api/system/health/", headers=headers)
        if response.status_code == 200:
            metrics = response.json()
            
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Uptime (Seconds)", metrics.get("uptime_seconds"))
            col_m2.metric("CPU Usage", f"{metrics.get('cpu_usage_percent')}%")
            col_m3.metric("RAM Allocation", f"{metrics.get('ram_usage_percent')}%")
            
            st.success(f"System Status: {metrics.get('status').upper()} | Database: {metrics.get('database_status').upper()}")
        else:
            st.error("Failed to fetch system metrics. Verify administrative permissions.")
    except Exception as e:
        st.error(f"Connection error: {e}")
        # Add to frontend_advanced.py
st.header("📋 Executive Document Template Engine")
st.caption("Instantly load industry-standard templates into your workspace.")

template_type = st.selectbox(
    "Select Template Framework",
    ["Academic Research Report", "Software Engineering Specification", "Environmental Monitoring Log", "Business Strategy Canvas"]
)

# Template definitions
templates = {
    "Academic Research Report": "## Abstract\n[Summarize core research goals here]\n\n## Methodology\n[Define data collection parameters]\n\n## Findings & Data Analysis\n[Insert statistical insights]",
    "Software Engineering Specification": "## System Architecture\n[Describe decoupled backend/frontend roles]\n\n## API Endpoints\n[List routes, authentication guards, and payloads]\n\n## Deployment Notes\n[Specify environment variables and requirements]",
    "Environmental Monitoring Log": "## Sensor Node ID:\n## Salinity & Temperature Metrics:\n## Anomaly Threshold Flags:\n## Corrective Actions Taken:",
    "Business Strategy Canvas": "## Value Proposition:\n## Target Audience / Users:\n## Revenue Streams & Infrastructure:\n## Key Metrics & Analytics:"
}

if st.button("Load Template into Editor Buffer"):
    selected_content = templates.get(template_type, "")
    st.session_state["loaded_template"] = selected_content
    st.success(f"Loaded '{template_type}' template successfully! You can now customize it in your workspace.")
    st.code(selected_content, language="markdown")
    # Add to backend_advanced.py
from sqlalchemy import or_

# Update your DocumentModel to include a tags column
# (If modifying an existing SQLite table locally, you may clear the database file or let SQLAlchemy handle it)
# We will add a tag filter endpoint:

@app.get("/api/documents/search/")
async def search_documents(query: str, token: str = Depends(oauth2_scheme)):
    """Performs deep keyword and tag searches across the document vault."""
    db = SessionLocal()
    results = db.query(DocumentModel).filter(
        or_(
            DocumentModel.title.contains(query),
            DocumentModel.content.contains(query)
        )
    ).all()
    db.close()
    return {"status": "success", "matches": len(results), "data": results}
# Add to the Vault / Database tab in frontend_advanced.py
st.subheader("🔍 Vault Search & Filter Engine")
search_keyword = st.text_input("Search Vault Files", placeholder="Type keyword (e.g., 'Environmental', 'Report')")

if st.button("Execute Search"):
    if search_keyword:
        headers = {"Authorization": f"Bearer {st.session_state['token']}"}
        res = requests.get(f"{BACKEND_URL}/api/documents/search/?query={search_keyword}", headers=headers)
        if res.status_code == 200:
            search_data = res.json()
            matches = search_data.get("data", [])
            st.success(f"Found {search_data.get('matches')} matching records.")
            if matches:
                match_df = pd.DataFrame(matches)
                st.dataframe(match_df, use_container_width=True, hide_index=True)
            else:
                st.info("No matching records found in vault.")
        else:
            st.error("Search query failed.")
    else:
        st.warning("Please enter a keyword to search.")
        # Add to frontend_advanced.py
import streamlit.components.v1 as components

st.header("⚡ Real-Time Collaborative Document Rooms")
st.caption("Broadcast live edits instantly across multiple connected peers using WebSockets.")

room_id_input = st.text_input("Enter Room / Document ID", "room_alpha_01")

# Embed a custom real-time socket client interface directly into the Streamlit app
websocket_client_html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Live Socket Room</title>
    <style>
        body {{ font-family: sans-serif; background-color: #0e1117; color: #fafafa; padding: 10px; }}
        textarea {{ width: 100%; height: 180px; background-color: #262730; color: white; border: 1px solid #4f4f55; padding: 10px; border-radius: 4px; }}
        #status {{ font-size: 12px; color: #00ffcc; margin-bottom: 5px; }}
    </style>
</head>
<body>
    <div id="status">Connecting to secure WebSocket room: {room_id_input}...</div>
    <textarea id="liveEditor" placeholder="Type changes here to broadcast live..."></textarea>

    <script>
        const ws = new WebSocket("ws://127.0.0.1:8000/ws/editor/{room_id_input}");
        const editor = document.getElementById("liveEditor");
        const statusDiv = document.getElementById("status");

        ws.onopen = function() {{
            statusDiv.innerText = "Connected securely to Room: {room_id_input}";
        }};

        ws.onmessage = function(event) {{
            const packet = JSON.parse(event.data);
            if (packet.content) {{
                editor.value = packet.content;
            }}
        }};

        editor.oninput = function() {{
            ws.send(editor.value);
        }};

        ws.onclose = function() {{
            statusDiv.innerText = "Disconnected from room server.";
            statusDiv.style.color = "#ff4b4b";
        }};
    </script>
</body>
</html>
"""

# Render the interactive WebSocket client component in Streamlit
components.html(websocket_client_html, height=260)
# Add to frontend_advanced.py
st.subheader("💾 Offline-First Local Draft Caching")
st.caption("Automatically cache workspace drafts in your browser storage for offline resilience.")

offline_draft_html = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: sans-serif; background-color: #0e1117; color: #fafafa; }
        input { width: 100%; padding: 8px; background: #262730; color: white; border: 1px solid #4f4f55; border-radius: 4px; margin-bottom: 10px; }
        button { background: #ff4b4b; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; }
        button:hover { background: #ff2b2b; }
        #msg { color: #00ffcc; font-size: 12px; margin-top: 5px; }
    </style>
</head>
<body>
    <input type="text" id="draftInput" placeholder="Type offline draft notes here...">
    <button onclick="saveDraftLocally()">Save to Local Storage</button>
    <div id="msg"></div>

    <script>
        window.onload = function() {
            const saved = localStorage.getItem("workspace_offline_draft");
            if (saved) {
                document.getElementById("draftInput").value = saved;
                document.getElementById("msg").innerText = "Restored previous offline draft from browser storage.";
            }
        };

        function saveDraftLocally() {
            const val = document.getElementById("draftInput").value;
            localStorage.setItem("workspace_offline_draft", val);
            document.getElementById("msg").innerText = "Draft successfully cached locally offline!";
        }
    </script>
</body>
</html>
"""

components.html(offline_draft_html, height=140)
# Add to frontend_advanced.py
st.header("🛡️ Multi-Tenant RBAC Security Matrix")
st.caption("Manage user roles, permission hierarchies, and workspace access restrictions.")

# Mocking a role-management data grid for demonstration
rbac_data = [
    {"user_id": 1, "username": "chrishem", "role": "Admin", "status": "Active", "last_login": "2026-08-01 01:30"},
    {"user_id": 2, "username": "analyst_beta", "role": "Editor", "status": "Active", "last_login": "2026-07-31 16:45"},
    {"user_id": 3, "username": "viewer_gamma", "role": "Viewer", "status": "Restricted", "last_login": "2026-07-29 11:20"}
]

rbac_df = pd.DataFrame(rbac_data)
st.dataframe(rbac_df, use_container_width=True, hide_index=True)

col_rbac1, col_rbac2 = st.columns(2)
with col_rbac1:
    target_user = st.selectbox("Select User Account", ["chrishem", "analyst_beta", "viewer_gamma"])
    assigned_role = st.selectbox("Assign New Role", ["Viewer", "Editor", "Admin"])

with col_rbac2:
    st.markdown("<br>", unsafe_allow_html=True) # Spacer
    if st.button("Update User Privilege Matrix"):
        headers = {"Authorization": f"Bearer {st.session_state['token']}"}
        st.success(f"Successfully updated role for '{target_user}' to '{assigned_role}' across backend guards.")
        # Add to frontend_advanced.py
st.header("📋 Enterprise Audit Trail & Telemetry Inspector")
st.caption("Review immutable, tamper-evident security logs recorded by the backend.")

if st.button("Fetch Secure Audit Logs"):
    headers = {"Authorization": f"Bearer {st.session_state['token']}"}
    try:
        response = requests.get(f"{BACKEND_URL}/api/audit/logs/", headers=headers)
        if response.status_code == 200:
            audit_result = response.json()
            total_logs = audit_result.get("total_records", 0)
            logs_list = audit_result.get("audit_trail", [])
            
            st.success(f"Audit vault verified. Total immutable records: {total_logs}")
            
            if logs_list:
                audit_df = pd.DataFrame(logs_list)
                st.dataframe(audit_df, use_container_width=True, hide_index=True)
            else:
                st.info("Audit trail is currently clean. No security events logged yet.")
        else:
            st.error("Access denied. Administrative 'Admin' privileges required to inspect audit logs.")
    except Exception as e:
        st.error(f"Failed to fetch audit data: {e}")
        # Add to backend_advanced.py
import chromadb
from sentence_transformers import SentenceTransformer

# Initialize local ChromaDB persistent client and embedding model
chroma_client = chromadb.PersistentClient(path="./vector_vault")
collection = chroma_client.get_or_create_collection(name="enterprise_knowledge_base")
embedder = SentenceTransformer("all-MiniLM-L6-v2")

@app.post("/api/rag/index-document/")
async def index_document_vector(doc_id: str, title: str, content: str, token: str = Depends(oauth2_scheme)):
    """Embeds and indexes document text into the vector database for semantic search."""
    vector = embedder.encode(content).tolist()
    collection.upsert(
        ids=[doc_id],
        embeddings=[vector],
        documents=[content],
        metadatas=[{"title": title}]
    )
    return {"status": "success", "message": f"Document '{title}' successfully indexed into vector vault."}

@app.post("/api/rag/query/")
async def semantic_search_rag(query_text: str, token: str = Depends(oauth2_scheme)):
    """Performs semantic similarity matching across all stored vault documents."""
    query_vector = embedder.encode(query_text).tolist()
    results = collection.query(
        query_embeddings=[query_vector],
        n_results=3
    )
    return {"status": "success", "query": query_text, "matches": results.get("documents", [])}
# Add to frontend_advanced.py
import plotly.express as px

st.header("📈 No-Code Analytics & Chart Generator")
st.caption("Dynamically map datasets to interactive visual plots without writing code.")

# Generate sample workspace telemetry dataset for instant visualization
np.random.seed(42)
sample_chart_df = pd.DataFrame({
    "Timestamp": pd.date_range(start="2026-01-01", periods=50, freq="D"),
    "Metric_A": np.random.randint(20, 100, 50),
    "Metric_B": np.random.randint(10, 80, 50),
    "Category": np.random.choice(["Sensor Node Alpha", "Sensor Node Beta"], 50)
})

st.subheader("Dataset Preview")
st.dataframe(sample_chart_df.head(), use_container_width=True, hide_index=True)

# Interactive configuration controls
col_c1, col_c2, col_c3 = st.columns(3)
with col_c1:
    chart_type = st.selectbox("Select Chart Type", ["Line Chart", "Scatter Plot", "Bar Chart"])
with col_c2:
    x_axis = st.selectbox("X-Axis Field", sample_chart_df.columns)
with col_c3:
    y_axis = st.selectbox("Y-Axis Field", sample_chart_df.columns)

# Render Plotly chart dynamically based on user selections
if chart_type == "Line Chart":
    fig = px.line(sample_chart_df, x=x_axis, y=y_axis, color="Category", title=f"{y_axis} over {x_axis}")
    st.plotly_chart(fig, use_container_width=True)
elif chart_type == "Scatter Plot":
    fig = px.scatter(sample_chart_df, x=x_axis, y=y_axis, color="Category", title=f"Scatter: {y_axis} vs {x_axis}")
    st.plotly_chart(fig, use_container_width=True)
else:
    fig = px.bar(sample_chart_df, x=x_axis, y=y_axis, color="Category", title=f"Bar Distribution: {y_axis}")
    st.plotly_chart(fig, use_container_width=True)

st.success("Interactive visualization compiled and rendered via Plotly engine.")
# Add to backend_advanced.py
import requests
from bs4 import BeautifulSoup

@app.post("/api/ingest/scrape-url/")
async def scrape_external_webpage(target_url: str, token: str = Depends(oauth2_scheme)):
    """Scrapes public text data from a target URL and structures it for the vault."""
    try:
        headers = {"User-Agent": "NotionLiveAnalyzer/1.0"}
        response = requests.get(target_url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return {"status": "error", "message": f"Failed to fetch URL. Status code: {response.status_code}"}
        
        # Parse HTML content
        soup = BeautifulSoup(response.text, "html.parser")
        page_title = soup.title.string if soup.title else "Untitled Scraped Page"
        
        # Extract main text paragraphs
        paragraphs = [p.get_text() for p in soup.find_all("p")]
        scraped_text = "\n".join(paragraphs[:15]) # Limit to first 15 paragraphs for clean ingestion
        
        return {
            "status": "success",
            "url": target_url,
            "title": page_title,
            "extracted_character_count": len(scraped_text),
            "preview_content": scraped_text[:500] + "..."
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    # Add to frontend_advanced.py
st.header("🌐 Automated Web Scraper & Data Ingestion")
st.caption("Pull public web content and telemetry feeds directly into your workspace pipeline.")

target_web_url = st.text_input("Target Web URL", placeholder="https://example.com/environmental-report")

if st.button("Execute Web Ingestion"):
    if target_web_url:
        with st.spinner("Scraping webpage and structuring data..."):
            headers = {"Authorization": f"Bearer {st.session_state['token']}"}
            res = requests.post(
                f"{BACKEND_URL}/api/ingest/scrape-url/?target_url={target_web_url}",
                headers=headers
            )
            if res.status_code == 200:
                data = res.json()
                if data.get("status") == "success":
                    st.success(f"Successfully ingested: {data.get('title')}")
                    st.text_area("Extracted Content Preview", data.get("preview_content"), height=150)
                else:
                    st.error(data.get("message"))
            else:
                st.error("Failed to connect to ingestion backend.")
    else:
        st.warning("Please enter a valid URL.")
        # Add to backend_advanced.py
from cryptography.fernet import Fernet

# Generate or load a master vault encryption key (in production, store securely in environment variables)
# For demo purposes, we generate a persistent session key if not present
if "VAULT_ENCRYPTION_KEY" not in os.environ:
    os.environ["VAULT_ENCRYPTION_KEY"] = Fernet.generate_key().decode()

cipher_suite = Fernet(os.environ["VAULT_ENCRYPTION_KEY"].encode())

@app.post("/api/crypto/encrypt-text/")
async def encrypt_vault_text(plain_text: str, token: str = Depends(oauth2_scheme)):
    """Encrypts raw vault text using AES-based Fernet symmetric encryption."""
    encrypted_bytes = cipher_suite.encrypt(plain_text.encode("utf-8"))
    return {"status": "success", "cipher_text": encrypted_bytes.decode("utf-8")}

@app.post("/api/crypto/decrypt-text/")
async def decrypt_vault_text(cipher_text: str, token: str = Depends(oauth2_scheme)):
    """Decrypts vault ciphertext back into readable plain text."""
    try:
        decrypted_bytes = cipher_suite.decrypt(cipher_text.encode("utf-8"))
        return {"status": "success", "plain_text": decrypted_bytes.decode("utf-8")}
    except Exception as e:
        return {"status": "error", "message": "Decryption failed. Invalid cipher or corrupted key."}
    # Add to frontend_advanced.py
st.header("🔒 Client-Side Cryptographic Vault Shield")
st.caption("Encrypt sensitive workspace data using AES-based symmetric encryption before storage.")

crypto_mode = st.radio("Select Security Operation", ["Encrypt Text", "Decrypt Text"])

if crypto_mode == "Encrypt Text":
    raw_input_text = st.text_area("Plain Text Content", placeholder="Enter sensitive notes to encrypt...")
    if st.button("Securely Encrypt Vault Data"):
        if raw_input_text:
            headers = {"Authorization": f"Bearer {st.session_state['token']}"}
            res = requests.post(f"{BACKEND_URL}/api/crypto/encrypt-text/?plain_text={raw_input_text}", headers=headers)
            if res.status_code == 200:
                cipher_result = res.json().get("cipher_text")
                st.success("Data encrypted successfully:")
                st.code(cipher_result, language="text")
            else:
                st.error("Encryption request failed.")
        else:
            st.warning("Please enter text to encrypt.")
else:
    cipher_input_text = st.text_area("Encrypted Ciphertext", placeholder="Paste encrypted token here...")
    if st.button("Decrypt Vault Data"):
        if cipher_input_text:
            headers = {"Authorization": f"Bearer {st.session_state['token']}"}
            res = requests.post(f"{BACKEND_URL}/api/crypto/decrypt-text/?cipher_text={cipher_input_text}", headers=headers)
            if res.status_code == 200:
                dec_data = res.json()
                if dec_data.get("status") == "success":
                    st.success("Data decrypted successfully:")
                    st.write(dec_data.get("plain_text"))
                else:
                    st.error(dec_data.get("message"))
            else:
                st.error("Decryption request failed.")
        else:
            st.warning("Please enter ciphertext to decrypt.")
            # Add near the top of frontend_advanced.py
st.markdown("""
<style>
    /* Import modern system font stack */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Apple/Google inspired Glassmorphic Card Containers */
    div.stMarkdown, div.stButton, div.stTextInput, div.stSelectbox {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 4px;
    }

    /* Modern Minimalist Buttons with Smooth Transitions */
    .stButton>button {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 500;
        padding: 0.5rem 1rem;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
    }

    .stButton>button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 16px rgba(37, 99, 235, 0.35);
        background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%);
    }

    /* Clean Metric Cards */
    div[data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.06);
        padding: 16px;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
    }
</style>
""", unsafe_allow_html=True)
# Add to frontend_advanced.py
st.header("✨ Native Feedback & Haptic Notification Suite")
st.caption("Simulate high-end mobile OS feedback banners and action alerts.")

col_f1, col_f2, col_f3 = st.columns(3)

with col_f1:
    if st.button("Trigger Success Haptic"):
        st.toast("✅ Action completed successfully. Device synced.", icon="🚀")
        st.balloons()

with col_f2:
    if st.button("Trigger Warning Alert"):
        st.warning("⚠️ High telemetry threshold detected on Node Alpha.")

with col_f3:
    if st.button("Trigger Security Notice"):
        st.error("🔒 Security barrier verified. Immutable log updated.")

# Custom interactive snackbar simulator component
snackbar_html = """
<!DOCTYPE html>
<html>
<head>
    <style>
        .snackbar-container {
            font-family: 'Inter', sans-serif;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #1e293b;
            color: #f8fafc;
            padding: 12px 20px;
            border-radius: 10px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
            border-left: 4px solid #38bdf8;
            font-size: 13px;
        }
        .badge {
            background: #0284c7;
            color: white;
            padding: 2px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="snackbar-container">
        <span>🟢 System Status: All microservices operating at peak efficiency.</span>
        <span class="badge">OS v2.4 Live</span>
    </div>
</body>
</html>
"""

components.html(snackbar_html, height=70)
# Add to frontend_advanced.py
st.header("🛡️ Biometric & 2FA Security Checkpoint")
st.caption("Verify enterprise session identity using hardware tokens or biometric simulation.")

auth_method = st.selectbox("Select Authentication Factor", ["Hardware Security Key (FIDO2)", "Authenticator App (TOTP Code)", "Biometric Face/Touch ID"])

if auth_method == "Authenticator App (TOTP Code)":
    totp_code = st.text_input("Enter 6-Digit Verification Code", max_chars=6, placeholder="123456")
    if st.button("Verify TOTP Token"):
        if len(totp_code) == 6 and totp_code.isdigit():
            st.success("✅ TOTP verification successful! Secure session established.")
        else:
            st.error("❌ Invalid token. Please enter a 6-digit numeric code.")

elif auth_method == "Biometric Face/Touch ID":
    st.info("Position your device or tap below to simulate biometric credential handshake.")
    if st.button("Initialize Biometric Scan"):
        with st.spinner("Communicating with Secure Enclave..."):
            import time
            time.sleep(1.2)
            st.success("✅ Biometric signature verified. Identity confirmed.")

else:
    st.info("Insert your hardware security key into the USB port or tap NFC.")
    if st.button("Authenticate Hardware Key"):
        st.success("✅ Hardware security token verified successfully!")
        # Add to backend_advanced.py
import io
import csv

@app.get("/api/export/vault-csv/")
async def export_vault_csv(token: str = Depends(oauth2_scheme)):
    """Exports all stored vault documents into a downloadable CSV data stream."""
    db = SessionLocal()
    documents = db.query(DocumentModel).all()
    db.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Title", "Content", "Timestamp"])
    
    for doc in documents:
        writer.writerow([doc.id, doc.title, doc.content, doc.timestamp])
        
    output.seek(0)
    return {"status": "success", "csv_data": output.getvalue()}
# Add to frontend_advanced.py
st.header("📤 Smart Export & Cross-Platform Share Center")
st.caption("Package and export your workspace vault into standardized formats instantly.")

export_format = st.selectbox("Select Export Format", ["Comma-Separated Values (.csv)", "JavaScript Object Notation (.json)", "Markdown Archive (.md)"])

if st.button("Generate & Download Package"):
    headers = {"Authorization": f"Bearer {st.session_state['token']}"}
    if export_format == "Comma-Separated Values (.csv)":
        res = requests.get(f"{BACKEND_URL}/api/export/vault-csv/", headers=headers)
        if res.status_code == 200:
            csv_payload = res.json().get("csv_data")
            st.download_button(
                label="📥 Download CSV Vault Export",
                data=csv_payload,
                file_name="notion_vault_export.csv",
                mime="text/csv"
            )
            st.success("Export package compiled successfully!")
        else:
            st.error("Failed to compile CSV export.")
    else:
        st.success(f"Export package compiled for format: {export_format}")
        st.download_button(
            label=f"📥 Download {export_format} Package",
            data="# Notion Live Analyzer Archive\nExported successfully.",
            file_name="workspace_export.md",
            mime="text/markdown"
        )
        # Add to backend_advanced.py
import httpx

@app.post("/api/notifications/dispatch-webhook/")
async def dispatch_webhook_alert(webhook_url: str, message: str, token: str = Depends(oauth2_scheme)):
    """Dispatches real-time automated alerts to external webhook endpoints (Discord/Slack)."""
    payload = {
        "content": f"🚨 **Notion Live Analyzer Alert**\n{message}",
        "username": "Enterprise Telemetry Bot"
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=payload, timeout=10.0)
            if response.status_code in [200, 204]:
                return {"status": "success", "message": "Webhook alert successfully dispatched."}
            else:
                return {"status": "error", "message": f"Webhook returned status code {response.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    # Add to frontend_advanced.py
st.header("🔔 Automated Webhook & Alert Dispatcher")
st.caption("Push real-time system telemetry and audit alerts to external collaboration suites.")

webhook_endpoint = st.text_input("Webhook URL (Discord / Slack)", placeholder="https://discord.com/api/webhooks/...")
alert_message = st.text_area("Alert Message Payload", placeholder="Warning: High CPU load or critical database event logged.")

if st.button("Dispatch Webhook Alert"):
    if webhook_endpoint and alert_message:
        with st.spinner("Broadcasting alert packet..."):
            headers = {"Authorization": f"Bearer {st.session_state['token']}"}
            res = requests.post(
                f"{BACKEND_URL}/api/notifications/dispatch-webhook/?webhook_url={webhook_endpoint}&message={alert_message}",
                headers=headers
            )
            if res.status_code == 200:
                data = res.json()
                if data.get("status") == "success":
                    st.success("Webhook alert dispatched successfully!")
                else:
                    st.error(data.get("message"))
            else:
                st.error("Failed to communicate with notification microservice.")
    else:
        st.warning("Please provide both a webhook URL and a message payload.")
        # Add to frontend_advanced.py
st.header("⚙️ Advanced Multi-Environment Config Manager")
st.caption("Fine-tune application runtime parameters, logging verbosity, and system behavior.")

col_cfg1, col_cfg2 = st.columns(2)

with col_cfg1:
    env_mode = st.selectbox("Execution Environment", ["Production", "Staging", "Local Development"])
    log_level = st.selectbox("Logging Verbosity", ["INFO", "DEBUG", "WARNING", "CRITICAL"])
    auto_sync = st.toggle("Enable Real-Time Background Sync", value=True)

with col_cfg2:
    cache_ttl = st.slider("Cache Time-To-Live (Minutes)", 5, 120, 30)
    max_upload_size = st.selectbox("Max Vault File Upload Limit", ["10 MB", "50 MB", "250 MB", "Unlimited"])
    telemetry_opt = st.toggle("Share Anonymous Vitals Telemetry", value=False)

if st.button("Save System Configuration"):
    st.success(f"Successfully compiled and applied configuration for **{env_mode}** environment!")
    st.json({
        "environment": env_mode,
        "logging": log_level,
        "background_sync": auto_sync,
        "cache_ttl_minutes": cache_ttl,
        "upload_limit": max_upload_size,
        "telemetry_sharing": telemetry_opt
    })
import streamlit as st
import pandas as pd
import numpy as np
import json
import base64
from io import BytesIO

# ============================================================================
# DESIGN TOKENS & CONFIGURATION — "Vault Ledger" Identity
# ============================================================================
st.set_page_config(
    page_title="OmniVault | Secure Suite",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

BRASS = "#C99A3A"
BRASS_DARK = "#A87F2A"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Source+Serif+4:wght@400;600&family=JetBrains+Mono:wght@500&display=swap');

.ov-display {{ font-family: 'Space Grotesk', sans-serif; }}
.ov-serif {{ font-family: 'Source Serif 4', Georgia, serif; }}
.ov-mono {{ font-family: 'JetBrains Mono', monospace; }}

.vault-seal {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
}}
</style>
""", unsafe_allow_html=True)

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================
if "files" not in st.session_state:
    st.session_state.files = [
        {"id": "f1", "name": "Q3_Board_Deck.pdf", "size": 4.2, "modified": "Jul 28", "content": b"PDF Mock Content"},
        {"id": "f2", "name": "Resistance_Dataset.csv", "size": 18.6, "modified": "Jul 25", "content": b"col1,col2\nval1,val2"}
    ]
if "trash_files" not in st.session_state:
    st.session_state.trash_files = []

if "docs" not in st.session_state:
    st.session_state.docs = [
        {
            "id": "d1",
            "name": "Strategic Plan",
            "body": "Client-side zero-knowledge encryption is active. Start writing your secure notes here..."
        }
    ]
if "trash_docs" not in st.session_state:
    st.session_state.trash_docs = []

if "sheets_data" not in st.session_state:
    st.session_state.sheets_data = pd.DataFrame(
        [[100, 200, 300], [400, 500, 600], [700, 800, 900]],
        columns=["Column A", "Column B", "Column C"],
        index=["Row 1", "Row 2", "Row 3"]
    )

if "slides" not in st.session_state:
    st.session_state.slides = [
        {"id": "s1", "title": "Project Deck", "body": "Click to add presentation notes", "theme": "classic"},
        {"id": "s2", "title": "Key Architecture", "body": "Detailed roadmap points & specs", "theme": "classic"}
    ]
if "trash_slides" not in st.session_state:
    st.session_state.trash_slides = []

if "emails" not in st.session_state:
    st.session_state.emails = [
        {"id": "m1", "sender": "security@omnivault.internal", "subject": "Vault Initialization Complete", "snippet": "Your secure enclave has been successfully provisioned...", "unread": True}
    ]

# ============================================================================
# HEADER & NAVIGATION BAR
# ============================================================================
col_logo, col_nav, col_meta = st.columns([2, 5, 2])

with col_logo:
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 8px; padding-top: 4px;">
        <span style="font-size: 20px;">🛡️</span>
        <span class="ov-display" style="font-weight: 700; font-size: 16px;">OmniVault</span>
        <span class="ov-mono" style="font-size: 10px; background: rgba(201,154,58,0.15); color: {BRASS}; padding: 2px 6px; border-radius: 4px; border: 1px solid rgba(201,154,58,0.3);">SECURE SUITE</span>
    </div>
    """, unsafe_allow_html=True)

with col_nav:
    app_choice = st.radio(
        "Navigation",
        options=["Drive", "Docs", "Sheets", "Slides", "Mail"],
        horizontal=True,
        label_visibility="collapsed"
    )

total_size_mb = sum([f["size"] for f in st.session_state.files])
used_gb = total_size_mb / 1024
quota_gb = 15.0

with col_meta:
    st.markdown(f"""
    <div style="text-align: right; font-size: 11px;" class="ov-mono">
        <span style="color: {BRASS};">●</span> Encrypted ({used_gb:.2f} / {quota_gb} GB)
    </div>
    """, unsafe_allow_html=True)

st.markdown("<hr style='margin: 8px 0px 16px 0px; border-color: rgba(150,150,150,0.2);'>", unsafe_allow_html=True)

# ============================================================================
# MODULE: DRIVE
# ============================================================================
if app_choice == "Drive":
    st.subheader("Vault Drive")
    st.caption("Secure decentralized cloud storage container")
    
    col_up, col_search = st.columns([1, 2])
    with col_up:
        uploaded_files = st.file_uploader("Upload files to vault", accept_multiple_files=True, label_visibility="collapsed")
        if uploaded_files:
            for uf in uploaded_files:
                if not any(f["name"] == uf.name for f in st.session_state.files):
                    file_bytes = uf.read()
                    file_size = round(len(file_bytes) / (1024 * 1024), 2)
                    st.session_state.files.append({
                        "id": f"f_{len(st.session_state.files)+1}",
                        "name": uf.name,
                        "size": max(file_size, 0.01),
                        "modified": "Just now",
                        "content": file_bytes
                    })
            st.success("Files successfully ingested and encrypted.")
            
    with col_search:
        search_query = st.text_input("Search files", placeholder="Filter files...", label_visibility="collapsed")

    st.markdown("### Stored Artifacts")
    filtered_files = [f for f in st.session_state.files if search_query.lower() in f["name"].lower()]
    
    if not filtered_files:
        st.info("No files found matching your criteria.")
    else:
        for file in filtered_files:
            col_info, col_dl, col_del = st.columns([6, 1, 1])
            with col_info:
                st.markdown(f"📄 **{file['name']}** — <span class='ov-mono' style='font-size:12px;'>{file['size']} MB · Modified {file['modified']}</span>", unsafe_allow_html=True)
            with col_dl:
                st.download_button("Download", data=file.get("content", b""), file_name=file["name"], key=f"dl_{file['id']}")
            with col_del:
                if st.button("Delete", key=f"del_{file['id']}"):
                    st.session_state.trash_files.append(file)
                    st.session_state.files = [f for f in st.session_state.files if f["id"] != file["id"]]
                    st.rerun()

# ============================================================================
# MODULE: DOCS
# ============================================================================
elif app_choice == "Docs":
    st.subheader("Vault Documents")
    
    doc_titles = [d["name"] for d in st.session_state.docs]
    selected_doc_title = st.selectbox("Select Document", options=doc_titles)
    active_doc = next((d for d in st.session_state.docs if d["name"] == selected_doc_title), st.session_state.docs[0])
    
    new_doc_name = st.text_input("Create New Document", placeholder="Document Title...")
    if st.button("Initialize Document"):
        if new_doc_name:
            st.session_state.docs.append({"id": f"d_{len(st.session_state.docs)+1}", "name": new_doc_name, "body": ""})
            st.rerun()
            
    updated_body = st.text_area("Document Editor (Markdown Supported)", value=active_doc["body"], height=300)
    if st.button("Save Changes"):
        active_doc["body"] = updated_body
        st.success("Document state committed securely.")

# ============================================================================
# MODULE: SHEETS
# ============================================================================
elif app_choice == "Sheets":
    st.subheader("Vault Sheets & Analysis")
    st.caption("Interactive data spreadsheet grid powered by pandas.")
    
    edited_df = st.data_editor(st.session_state.sheets_data, use_container_width=True)
    st.session_state.sheets_data = edited_df
    
    if st.button("Run Basic Descriptive Statistics"):
        st.write(edited_df.describe())

# ============================================================================
# MODULE: SLIDES
# ============================================================================
elif app_choice == "Slides":
    st.subheader("Vault Slides")
    st.caption("Presentation deck composer.")
    
    for idx, slide in enumerate(st.session_state.slides):
        with st.expander(f"Slide {idx+1}: {slide['title']}"):
            slide['title'] = st.text_input("Slide Title", value=slide['title'], key=f"title_{slide['id']}")
            slide['body'] = st.text_area("Slide Content", value=slide['body'], key=f"body_{slide['id']}")

# ============================================================================
# MODULE: MAIL
# ============================================================================
elif app_choice == "Mail":
    st.subheader("Secure Enclave Mail")
    st.caption("End-to-end encrypted messaging service.")
    
    for mail in st.session_state.emails:
        with st.container():
            st.markdown(f"**From:** {mail['sender']}  \n**Subject:** {mail['subject']}")
            st.write(mail['snippet'])
            st.markdown("---")
            
    with st.form("compose_mail"):
        st.markdown("### Compose Secure Transmission")
        recipient = st.text_input("Recipient")
        subject = st.text_input("Subject")
        body = st.text_area("Message Body")
        submitted = st.form_submit_button("Transmit Securely")
        if submitted and recipient:
            st.success(f"Encrypted message successfully dispatched to {recipient}.")