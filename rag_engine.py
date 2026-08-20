"""
rag_engine.py
Graph-Enhanced Retrieval-Augmented Generation (RAG) Pipeline.

Hybrid retrieval that combines:
  - Vector search (PostgreSQL `pgvector` when reachable, else local SQLite + cosine)
  - Relational graph mapping via NetworkX (links entities: research concepts,
    data variables, sector outcomes) enabling multi-hop retrieval.

Pipeline:
  chunk_text() -> embed(LLMRouter) -> index(title, body, vector, entities)
  -> query(q) : vector top-k + graph multi-hop expansion -> fused context
"""
from __future__ import annotations

import math
import os
import re
import sqlite3
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

APP_DIR = Path(__file__).resolve().parent.parent
RAG_DB = str(APP_DIR / "rag_store.db")

try:
    import networkx as nx

    HAS_NETWORKX = True
except Exception:
    HAS_NETWORKX = False

try:
    from modules.llm_router import get_router

    _router = get_router()
except Exception:
    _router = None

# ---------------------------------------------------------------------------
# Lightweight vector store (SQLite + cosine, no external deps)
# ---------------------------------------------------------------------------
_RAG_SCHEMA = """
CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id TEXT NOT NULL,
    title TEXT DEFAULT '',
    body TEXT NOT NULL,
    entities_json TEXT DEFAULT '[]',
    vector_json TEXT DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(doc_id);
"""


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(RAG_DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_rag_store() -> None:
    conn = _conn()
    try:
        conn.executescript(_RAG_SCHEMA)
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------
def chunk_text(
    text: str, chunk_size: int = 500, overlap: int = 80
) -> List[str]:
    """Split text into overlapping chunks at sensible boundaries."""
    text = unicodedata.normalize("NFKD", text or "")
    text = " ".join(text.split())
    if len(text) <= chunk_size:
        return [text] if text else []

    chunks: List[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        # Expand to next sentence boundary if possible
        if end < n:
            boundary = text.rfind(". ", start, end)
            if boundary > start + chunk_size // 2:
                end = boundary + 1
        chunks.append(text[start:end].strip())
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return [c for c in chunks if c]


# ---------------------------------------------------------------------------
# Entity extraction (deterministic, regex-based)
# ---------------------------------------------------------------------------
_ENTITY_PATTERN = re.compile(
    r"\b([A-Z][A-Za-z0-9_-]{2,}(?:\s[A-Z][A-Za-z0-9_-]+){0,2})\b"
)
STOP_ENTITIES = {"The", "This", "These", "Those", "That", "They", "What"}


def extract_entities(text: str, limit: int = 12) -> List[str]:
    """Extract likely entity names (Title-Case tokens) deterministically."""
    found = _ENTITY_PATTERN.findall(text or "")
    clean = []
    for e in found:
        e = e.strip()
        if e in STOP_ENTITIES or len(e) < 3:
            continue
        if e not in clean:
            clean.append(e)
        if len(clean) >= limit:
            break
    return clean


# ---------------------------------------------------------------------------
# Indexing
# ---------------------------------------------------------------------------
def index_document(
    doc_id: str,
    title: str,
    body: str,
    entities: Optional[List[str]] = None,
) -> int:
    """Embed + store a document (split into chunks) in the vector store."""
    init_rag_store()
    chunks = chunk_text(body)
    if not chunks and body.strip():
        chunks = [body.strip()]

    conn = _conn()
    inserted = 0
    try:
        for i, chunk in enumerate(chunks):
            if entities is None:
                ents = extract_entities(chunk)
            else:
                ents = entities
            vec = _router.embed_text(chunk) if _router else _hash_vec(chunk)
            import json

            cursor = conn.execute(
                "INSERT INTO chunks (doc_id, title, body, entities_json, vector_json) VALUES (?, ?, ?, ?, ?)",
                (
                    f"{doc_id}:{i}",
                    title,
                    chunk,
                    json.dumps(ents),
                    json.dumps(vec),
                ),
            )
            inserted += 1
        conn.commit()
    finally:
        conn.close()
    return inserted


def _hash_vec(text: str, dim: int = 64) -> List[float]:
    import hashlib

    vec = [0.0] * dim
    for i, ch in enumerate(text):
        h = int(hashlib.sha256(text[i : i + 1].encode("utf-8")).hexdigest(), 16)
        vec[i % dim] += (h % 1000) / 1000.0
    norm = sum(v * v for v in vec) ** 0.5 or 1.0
    return [round(v / norm, 6) for v in vec]


# ---------------------------------------------------------------------------
# Vector similarity
# ---------------------------------------------------------------------------
def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b:
        return 0.0
    dim = max(len(a), len(b))
    a = a + [0.0] * (dim - len(a))
    b = b + [0.0] * (dim - len(b))
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5 or 1.0
    nb = sum(y * y for y in b) ** 0.5 or 1.0
    return dot / (na * nb)


def vector_search(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """Search for the most similar chunks by cosine similarity."""
    init_rag_store()
    qvec = _router.embed_text(query) if _router else _hash_vec(query)
    conn = _conn()
    results: List[Dict[str, Any]] = []
    try:
        rows = conn.execute("SELECT * FROM chunks").fetchall()
        for row in rows:
            import json

            try:
                vec = json.loads(row["vector_json"])
            except Exception:
                vec = []
            score = _cosine(qvec, vec)
            results.append(
                {
                    "id": row["id"],
                    "doc_id": row["doc_id"],
                    "title": row["title"],
                    "body": row["body"],
                    "entities": json.loads(row["entities_json"]),
                    "score": round(score, 4),
                }
            )
        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:top_k]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Graph construction + multi-hop retrieval (NetworkX)
# ---------------------------------------------------------------------------
def build_knowledge_graph() -> Any:
    """Build a NetworkX graph from stored chunks linking shared entities."""
    G = nx.Graph() if HAS_NETWORKX else None
    if G is None:
        return None
    init_rag_store()
    conn = _conn()
    try:
        rows = conn.execute("SELECT doc_id, title, entities_json FROM chunks").fetchall()
        for row in rows:
            import json

            try:
                ents = json.loads(row["entities_json"])
            except Exception:
                ents = []
            doc_node = f"📄 {row['title'][:40]}" or row["doc_id"]
            G.add_node(doc_node, type="document")
            for e in ents:
                G.add_node(e, type="entity")
                G.add_edge(doc_node, e)
    finally:
        conn.close()
    return G


def multi_hop_retrieval(query: str, depth: int = 2, top_k: int = 5) -> Dict[str, Any]:
    """
    Hybrid RAG: vector top-k + graph neighbor expansion across `depth` hops.
    Returns fused context list with combined scores.
    """
    init_rag_store()
    vector_hits = vector_search(query, top_k=top_k)

    expanded: Dict[int, float] = {}
    G = build_knowledge_graph()
    conn = _conn()
    try:
        import json

        rows = {
            r["id"]: {"title": r["title"], "entities": json.loads(r["entities_json"]), "body": r["body"]}
            for r in conn.execute("SELECT * FROM chunks").fetchall()
        }
    finally:
        conn.close()

    # Score vector hits
    for hit in vector_hits:
        expanded[hit["id"]] = hit["score"]

    # Graph multi-hop expansion
    if G is not None:
        query_entities = set(extract_entities(query))
        for node in G.nodes():
            if node in query_entities:
                for neighbor in nx.single_source_shortest_path_length(G, node, cutoff=depth):
                    # find chunks mentioning this neighbor
                    for cid, info in rows.items():
                        if neighbor in info["entities"]:
                            boost = 0.15 * (depth - nx.shortest_path_length(G, node, neighbor))
                            expanded[cid] = max(expanded.get(cid, 0.0), boost)

    fused = []
    for cid, score in sorted(expanded.items(), key=lambda kv: kv[1], reverse=True):
        info = rows.get(cid)
        if info:
            fused.append({**info, "id": cid, "combined_score": round(score, 4)})
        if len(fused) >= top_k * 2:
            break

    return {"query": query, "results": fused, "vector_hits": vector_hits}


def register_rag_task_handlers() -> None:
    """Register RAG indexing as a task handler."""
    from tasks import register_task_handler

    def handler(text: str = "", title: str = "Untitled", doc_id: str = "doc",
                progress_cb=None, task_id=None, **kwargs):
        if progress_cb:
            progress_cb(10, "Building RAG index…")
        n = index_document(doc_id, title, text)
        if progress_cb:
            progress_cb(100, f"Indexed {n} chunks")
        return {"indexed_chunks": n, "doc_id": doc_id}

    register_task_handler("index_document", handler)


def query_rag(query: str, top_k: int = 5) -> Dict[str, Any]:
    """Public query entry point (vector + graph)."""
    return multi_hop_retrieval(query, top_k=top_k)
