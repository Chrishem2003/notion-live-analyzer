"""
fastapi_app.py
FastAPI microservice backend for the Multi-Problem Solver.

Runs alongside Streamlit (default :8000) and exposes REST endpoints for:
  - Health / capability discovery
  - Async task dispatch & polling (tasks.py)
  - Agent swarm execution (agents.py)
  - Graph-RAG query & indexing (rag_engine.py)

CORS is enabled so the Streamlit frontend can call these endpoints directly.
Run:  uvicorn fastapi_app:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import os
import threading
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from modules.task_status_registry import (
    get_task,
    list_tasks,
    status_summary,
)
from tasks import dispatch_task, register_default_handlers

app = FastAPI(title="Multi-Problem Solver API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register celery/threadpool task handlers (agents, rag) at startup.
register_default_handlers()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class TaskDispatchRequest(BaseModel):
    name: str
    # arbitrary kwargs
    model_config = {"extra": "allow"}


class AgentRunRequest(BaseModel):
    query: str
    sector: str = "Cross-Sector"
    country: str = ""
    papers_limit: int = 20
    priority: str = "Standard"
    indicators: List[str] = []
    sync: bool = False


class RAGIndexRequest(BaseModel):
    doc_id: str
    title: str = "Untitled"
    text: str


class RAGQueryRequest(BaseModel):
    query: str
    top_k: int = 5


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
@app.on_event("startup")
def _startup() -> None:
    register_default_handlers()


# ---------------------------------------------------------------------------
# Health & capability
# ---------------------------------------------------------------------------
@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "service": "multi-problem-solver-api"}


@app.get("/capabilities")
def capabilities() -> Dict[str, Any]:
    return {
        "modules": ["tasks", "agents", "rag", "llm_router"],
        "task_status": status_summary(),
    }


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------
@app.post("/api/tasks/dispatch")
def api_dispatch(req: TaskDispatchRequest) -> Dict[str, Any]:
    kwargs = req.model_dump(exclude={"name"})
    return dispatch_task(req.name, **kwargs)


@app.get("/api/tasks/{task_id}")
def api_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    return get_task(task_id)


@app.get("/api/tasks")
def api_list_tasks(limit: int = 50, status: Optional[str] = None) -> List[Dict[str, Any]]:
    return list_tasks(limit=limit, status=status)


@app.get("/api/status/summary")
def api_status_summary() -> Dict[str, int]:
    return status_summary()


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------
def _run_agent_sync(req: AgentRunRequest) -> Dict[str, Any]:
    from agents import run_agent_swarm

    return run_agent_swarm(
        query=req.query,
        sector=req.sector,
        country=req.country,
        papers_limit=req.papers_limit,
        priority=req.priority,
        indicators=req.indicators,
    )


@app.post("/api/agents/run")
def api_agents_run(req: AgentRunRequest) -> Dict[str, Any]:
    if req.sync:
        return _run_agent_sync(req)
    # Async: dispatch as a background task
    return dispatch_task(
        "run_agent_swarm",
        query=req.query,
        sector=req.sector,
        country=req.country,
        papers_limit=req.papers_limit,
        priority=req.priority,
    )


# ---------------------------------------------------------------------------
# RAG
# ---------------------------------------------------------------------------
@app.post("/api/rag/index")
def api_rag_index(req: RAGIndexRequest) -> Dict[str, Any]:
    from rag_engine import index_document

    n = index_document(req.doc_id, req.title, req.text)
    return {"indexed_chunks": n, "doc_id": req.doc_id}


@app.post("/api/rag/query")
def api_rag_query(req: RAGQueryRequest) -> Dict[str, Any]:
    from rag_engine import query_rag

    return query_rag(req.query, top_k=req.top_k)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))  # noqa: F821
