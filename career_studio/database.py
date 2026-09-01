import sqlite3,json,os,datetime
from contextlib import contextmanager
DB_PATH=os.getenv("CAREER_STUDIO_DB","career_studio.db")
@contextmanager
def connect():
 c=sqlite3.connect(DB_PATH); c.row_factory=sqlite3.Row
 try:
  init_db(c); yield c; c.commit()
 finally: c.close()
def init_db(c):
 c.execute("CREATE TABLE IF NOT EXISTS career_meta(key TEXT PRIMARY KEY,value TEXT)")
 c.execute("CREATE TABLE IF NOT EXISTS career_profiles(email TEXT PRIMARY KEY,data TEXT NOT NULL,updated_at TEXT NOT NULL)")
 c.execute("CREATE TABLE IF NOT EXISTS career_documents(id INTEGER PRIMARY KEY AUTOINCREMENT,email TEXT,kind TEXT,name TEXT,content TEXT,created_at TEXT,metadata TEXT DEFAULT '{}')")
 c.execute("CREATE TABLE IF NOT EXISTS career_projects(id INTEGER PRIMARY KEY AUTOINCREMENT,email TEXT,title TEXT,role TEXT,description TEXT,skills TEXT,url TEXT,created_at TEXT)")
 c.execute("CREATE TABLE IF NOT EXISTS career_applications(id INTEGER PRIMARY KEY AUTOINCREMENT,email TEXT,company TEXT,role TEXT,status TEXT,applied_at TEXT,notes TEXT)")
 c.execute("CREATE INDEX IF NOT EXISTS idx_career_docs ON career_documents(email,kind)")
 c.execute("CREATE INDEX IF NOT EXISTS idx_career_apps ON career_applications(email)")
 c.execute("INSERT INTO career_meta(key,value) VALUES('schema_version','5') ON CONFLICT(key) DO NOTHING")
def load_profile(email):
 with connect() as c:r=c.execute("SELECT data FROM career_profiles WHERE email=?",(email,)).fetchone()
 return json.loads(r["data"]) if r else {}
def save_profile(email,data):
 with connect() as c:c.execute("INSERT INTO career_profiles VALUES(?,?,?) ON CONFLICT(email) DO UPDATE SET data=excluded.data,updated_at=excluded.updated_at",(email,json.dumps(data),datetime.datetime.now(datetime.UTC).isoformat()))
def save_document(email,kind,name,content,metadata=None):
 with connect() as c:c.execute("INSERT INTO career_documents(email,kind,name,content,created_at,metadata) VALUES(?,?,?,?,?,?)",(email,kind,name,content,datetime.datetime.now(datetime.UTC).isoformat(),json.dumps(metadata or {})))
def list_documents(email,kind=None):
 q="SELECT * FROM career_documents WHERE email=?"; a=[email]
 if kind:q+=" AND kind=?";a.append(kind)
 q+=" ORDER BY id DESC"
 with connect() as c:return [dict(x) for x in c.execute(q,a).fetchall()]
def add_project(email,title,role,description,skills,url):
 with connect() as c:c.execute("INSERT INTO career_projects(email,title,role,description,skills,url,created_at) VALUES(?,?,?,?,?,?,?)",(email,title,role,description,skills,url,datetime.datetime.now(datetime.UTC).isoformat()))
def list_projects(email):
 with connect() as c:return [dict(x) for x in c.execute("SELECT * FROM career_projects WHERE email=? ORDER BY id DESC",(email,))]
def add_application(email,company,role,status,applied_at,notes):
 with connect() as c:c.execute("INSERT INTO career_applications(email,company,role,status,applied_at,notes) VALUES(?,?,?,?,?,?)",(email,company,role,status,applied_at,notes))
def list_applications(email):
 with connect() as c:return [dict(x) for x in c.execute("SELECT * FROM career_applications WHERE email=? ORDER BY id DESC",(email,))]

# Advancement 6 persistence helpers. These are additive and preserve the v5 tables.
def save_evidence(email, items):
    import datetime, json
    with connect() as c:
        c.execute("CREATE TABLE IF NOT EXISTS career_evidence(id INTEGER PRIMARY KEY AUTOINCREMENT,email TEXT,evidence_id TEXT,kind TEXT,title TEXT,text TEXT,skills TEXT,metrics TEXT,source TEXT,created_at TEXT,UNIQUE(email,evidence_id))")
        for x in items:
            c.execute("""INSERT INTO career_evidence(email,evidence_id,kind,title,text,skills,metrics,source,created_at) VALUES(?,?,?,?,?,?,?,?,?)
            ON CONFLICT(email,evidence_id) DO UPDATE SET kind=excluded.kind,title=excluded.title,text=excluded.text,skills=excluded.skills,metrics=excluded.metrics,source=excluded.source""",
            (email,x["evidence_id"],x["kind"],x["title"],x["text"],json.dumps(x.get("skills",[])),json.dumps(x.get("metrics",[])),x.get("source","profile"),datetime.datetime.now(datetime.UTC).isoformat()))

def save_job_analysis(email,title,company,job_text,result):
    import datetime, json
    with connect() as c:
        c.execute("CREATE TABLE IF NOT EXISTS career_job_analyses(id INTEGER PRIMARY KEY AUTOINCREMENT,email TEXT,job_title TEXT,company TEXT,job_text TEXT,result TEXT,created_at TEXT)")
        c.execute("INSERT INTO career_job_analyses(email,job_title,company,job_text,result,created_at) VALUES(?,?,?,?,?,?)",(email,title,company,job_text,json.dumps(result),datetime.datetime.now(datetime.UTC).isoformat()))

def list_job_analyses(email):
    import json
    with connect() as c: rows=c.execute("SELECT * FROM career_job_analyses WHERE email=? ORDER BY id DESC",(email,)).fetchall()
    return [dict(r)|{"result":json.loads(r["result"])} for r in rows]
