import pytest
import os
import sqlite3
from security.waf import sanitize_payload
from modules.database import init_db, log_backend_event

def test_waf_sanitization():
    """Test Web Application Firewall payload sanitization against script injection."""
    unsafe_input = "<script>alert('xss')</script>SELECT * FROM users;"
    safe_output = sanitize_payload(unsafe_input)
    assert "<script>" not in safe_output
    assert "&lt;script&gt;" in safe_output

def test_database_initialization():
    """Test that SQLite database initializes tables correctly."""
    init_db()
    assert os.path.exists("chrishem_engine.db")
    
    conn = sqlite3.connect("chrishem_engine.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='system_logs';")
    table_exists = cursor.fetchone()
    conn.close()
    
    assert table_exists is not None

def test_logging_mechanism():
    """Test writing and retrieving backend audit logs."""
    init_db()
    log_backend_event("TEST", "Automated test suite execution event.")
    
    conn = sqlite3.connect("chrishem_engine.db")
    cursor = conn.cursor()
    cursor.execute("SELECT level, message FROM system_logs ORDER BY id DESC LIMIT 1;")
    level, message = cursor.fetchone()
    conn.close()
    
    assert level == "TEST"
    assert message == "Automated test suite execution event."
