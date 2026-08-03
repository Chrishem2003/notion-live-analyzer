import security_guard
import security_guard

from fastapi import FastAPI, HTTPException
import sqlite3
import pandas as pd

app = FastAPI(
    title="CHRISHEM Enterprise API Gateway",
    description="Programmatic REST API for telemetry, logs, and secure data access.",
    version="1.0.0"
)

@app.get("/health")
def health_check():
    return {"status": "online", "engine": "CHRISHEM Enterprise Intelligence Engine"}

@app.get("/logs")
def get_system_logs(limit: int = 50):
    try:
        conn = sqlite3.connect("chrishem_engine.db")
        df = pd.read_sql_query(f"SELECT * FROM system_logs ORDER BY id DESC LIMIT {limit}", conn)
        conn.close()
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessions")
def get_user_sessions():
    try:
        conn = sqlite3.connect("chrishem_engine.db")
        df = pd.read_sql_query("SELECT * FROM user_sessions", conn)
        conn.close()
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
