# 🚀 Multi-Problem Solver — Setup & Execution Guide

A modular, multi-sector web application bridging **data analytics, literature
research, bioinformatics/environmental processing, and automated reporting**
into a single unified platform.

---

## 📁 Directory Structure

```
notion-live-analyzer/
├── app.py                  # Streamlit main entry point (gateway + hub)
├── portal.py               # Secure login gateway
├── main.py                 # Legacy dashboard entry
├── tasks.py                # ⚡ Async task runner (Celery + Redis / ThreadPool)
├── agents.py               # 🧠 3-persona Multi-Agent Swarm
├── rag_engine.py           # 🔎 Hybrid Graph+Vector RAG pipeline
├── fastapi_app.py          # 🔌 FastAPI microservice bridge (:8000)
├── modules/
│   ├── llm_router.py           # Gemini / Ollama hybrid fallback
│   ├── task_status_registry.py # Shared async task state (SQLite)
│   ├── self_correcting_executor.py  # LLM code self-correction loop
│   ├── mendeley_integration.py      # Real Mendeley OAuth + library
│   ├── gis_engine.py               # QGIS-grade spatial analytics
│   ├── spss_suite.py               # SPSS-grade advanced stats
│   └── ... (existing modules)
├── pages/
│   ├── 57_🗺️_GIS_Spatial_Analytics.py        # NEW
│   ├── 58_📚_Mendeley_Reference_Manager.py    # NEW
│   ├── 59_📊_SPSS_Advanced_Suite.py           # NEW
│   └── 60_🦾_Agent_Swarm_Task_Console.py      # NEW
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
├── .env.example
└── SETUP_GUIDE.md
```

---

## ⚙️ Option A — Run Locally in VSCode (Quick)

The app **runs without Redis or PostgreSQL** thanks to graceful fallbacks
(in-process ThreadPool + SQLite vector store). This is the fastest way to go.

### 1. Create a virtual environment & install deps

```bash
cd /workspaces/notion-live-analyzer
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

> Heavy optional deps for GIS/SPSS are included. If `geopandas` or
> `pyreadstat` fail to build on your platform, the GIS/SPSS pages degrade
> gracefully (basic mapping / .sav export disabled) — the rest still works.

### 2. Configure secrets (optional)

```bash
cp .env.example .env
# edit .env and add GEMINI_API_KEY, OLLAMA_BASE_URL, etc.
```

### 3. Launch Streamlit

```bash
streamlit run app.py
```

Open **http://localhost:8501** → unlock the gateway → the new pages appear in
the sidebar under **GIS Spatial Analytics**, **Mendeley Reference Manager**,
**SPSS Advanced Suite**, and **Agent Swarm & Task Console**.

### 4. (Optional) Launch the FastAPI bridge

```bash
uvicorn fastapi_app:app --host 0.0.0.0 --port 8000
```

---

## 🐳 Option B — Full Docker Stack (Production)

Spins up **PostgreSQL (pgvector) + Redis + FastAPI + Celery worker + Streamlit**.

### 1. Configure environment

```bash
cp .env.example .env
# fill in GEMINI_API_KEY, etc.
```

### 2. Build & run

```bash
docker compose up --build
```

| Service | URL |
|---------|-----|
| Streamlit UI | http://localhost:8501 |
| FastAPI API   | http://localhost:8000 |
| PG/Redis      | 5432 / 6379 |

### 3. Enable Celery (Redis) mode

Set `CELERY_MODE=1` in `.env` to route async tasks through the Redis-backed
Celery worker instead of the in-process fallback.

---

## 🔌 API Endpoints (FastAPI)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET    | `/health` | Health check |
| GET    | `/capabilities` | Loaded modules + task summary |
| POST   | `/api/tasks/dispatch` | Dispatch an async task |
| GET    | `/api/tasks/{id}` | Poll task status |
| GET    | `/api/tasks` | List tasks |
| GET    | `/api/status/summary` | Status counts |
| POST   | `/api/agents/run` | Run the agent swarm (sync or async) |
| POST   | `/api/rag/index` | Index documents into RAG store |
| POST   | `/api/rag/query` | Query hybrid Graph+Vector RAG |

---

## 🧠 New Enterprise Features

| Feature | Where | Details |
|---------|-------|---------|
| **Async Task Runner** | `tasks.py` + Page 60 | Celery+Redis with ThreadPool fallback, live progress via SQLite registry |
| **Multi-Agent Swarm** | `agents.py` + Page 60 | Research • Data Auditor • Synthesis personas |
| **Hybrid Graph+Vector RAG** | `rag_engine.py` + Page 60 | pgvector/SQLite cosine + NetworkX multi-hop |
| **LLM Hybrid Fallback** | `modules/llm_router.py` | Gemini (heavy) / Ollama (light) / deterministic |
| **Self-Correcting Executor** | `modules/self_correcting_executor.py` | LLM-driven code fix loop |
| **Mendeley Integration** | `modules/mendeley_integration.py` + Page 58 | OAuth, sync, BibTeX/RIS export |
| **QGIS-Grade GIS** | `modules/gis_engine.py` + Page 57 | Vector ops, choropleth, NDVI, exports |
| **SPSS-Grade Stats** | `modules/spss_suite.py` + Page 59 | ANCOVA, MANOVA, factor, .sav export |

---

## ✅ Verification

```bash
# Compile-check all Python files
python -m py_compile app.py tasks.py agents.py rag_engine.py fastapi_app.py \
  modules/task_status_registry.py modules/llm_router.py \
  modules/self_correcting_executor.py modules/mendeley_integration.py \
  modules/gis_engine.py modules/spss_suite.py pages/__init__.py && echo OK

# Smoke-test the agent swarm (no UI needed)
python agents.py
