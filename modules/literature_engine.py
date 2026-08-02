
"""
Global Literature Aggregator & Auto-Drafting Engine
Zero-loss SQLite persistence, factual paper harvesting from Semantic Scholar,
mechanical reference formatting (citeproc-py, NO AI), and human-authored drafting.

Core Principles:
- NO AI-generated citations or text  everything is factual or user-written
- Every action persists instantly to SQLite (research_workspace.db)
- Papers are REAL, fetched from live academic APIs (Semantic Scholar, CrossRef)
- References are formatted mechanically using citeproc-py or regex  zero hallucination
- User findings merge seamlessly into final downloadable reports
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import time
import io
import base64
import html
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

import pandas as pd
import requests
import streamlit as st

from modules.logging_utils import get_logger

logger = get_logger(__name__)

# ''' Paths ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
APP_DIR = Path(__file__).resolve().parent.parent
DB_PATH = APP_DIR / "research_workspace.db"


# '''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
# 1. DATABASE LAYER  Zero-Loss Local Persistence
# '''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
class LiteratureDatabase:
    """
    SQLite persistence layer for the Literature Aggregator.
    Every operation commits immediately  no data ever lost.
    Survives crashes, reloads, and network drops.
    """

    def __init__(self, db_path: str | Path = DB_PATH):
        self.db_path = Path(db_path)
        self._init_tables()

    def _get_conn(self) -> sqlite3.Connection:
        """Get a connection with row factory for dict-like access."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_tables(self):
        """Create all tables if they don't exist. Auto-migrates if needed."""
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL DEFAULT 'Untitled Project',
                    topic TEXT DEFAULT '',
                    country TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active'
                );

                CREATE TABLE IF NOT EXISTS fetched_papers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    title TEXT NOT NULL DEFAULT '',
                    authors TEXT DEFAULT '',
                    year INTEGER DEFAULT NULL,
                    journal TEXT DEFAULT '',
                    citations INTEGER DEFAULT 0,
                    doi TEXT DEFAULT '',
                    url TEXT DEFAULT '',
                    abstract TEXT DEFAULT '',
                    is_checked INTEGER DEFAULT 0,
                    is_cited INTEGER DEFAULT 0,
                    user_notes TEXT DEFAULT '',
                    user_findings TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS saved_drafts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    section TEXT NOT NULL,
                    content TEXT DEFAULT '',
                    citations_ids TEXT DEFAULT '[]',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS report_sections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    section_order INTEGER DEFAULT 0,
                    section_title TEXT NOT NULL,
                    content TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_fetched_papers_project 
                    ON fetched_papers(project_id);
                CREATE INDEX IF NOT EXISTS idx_saved_drafts_project 
                    ON saved_drafts(project_id);
                CREATE INDEX IF NOT EXISTS idx_report_sections_project 
                    ON report_sections(project_id);
            """)
            conn.commit()

            # Auto-migrate: add is_cited column if missing (for databases created before v2)
            try:
                conn.execute("ALTER TABLE fetched_papers ADD COLUMN is_cited INTEGER DEFAULT 0")
                conn.commit()
            except sqlite3.OperationalError as exc:
                if "duplicate column name" not in str(exc).lower():
                    logger.error("fetched_papers migration failed: %s", exc)
                    raise

        finally:
            conn.close()

    # ''' Project Operations ''''''''''''''''''''''''''''''''''''''''''

    def create_project(self, name: str = "Untitled Project", topic: str = "", country: str = "") -> int:
        """Create a new research project. Returns project_id."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "INSERT INTO projects (name, topic, country) VALUES (?, ?, ?)",
                (name, topic, country),
            )
            project_id = cursor.lastrowid
            default_sections = [
                ("Introduction", 0),
                ("Literature Review", 1),
                ("Methodology", 2),
                ("Findings & Discussion", 3),
                ("Conclusion", 4),
            ]
            for title, order in default_sections:
                conn.execute(
                    "INSERT INTO report_sections (project_id, section_order, section_title, content) VALUES (?, ?, ?, '')",
                    (project_id, order, title),
                )
            conn.commit()
            return project_id
        finally:
            conn.close()

    def update_project(self, project_id: int, **kwargs) -> bool:
        """Update project fields (name, topic, country, status)."""
        allowed = {"name", "topic", "country", "status"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False
        updates["updated_at"] = datetime.now().isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values())  [project_id]
        conn = self._get_conn()
        try:
            conn.execute(f"UPDATE projects SET {set_clause} WHERE id = ?", values)
            conn.commit()
            return True
        finally:
            conn.close()

    def get_projects(self) -> List[Dict]:
        """Get all projects."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM projects ORDER BY updated_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_project(self, project_id: int) -> Optional[Dict]:
        """Get a single project by ID."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def delete_project(self, project_id: int) -> bool:
        """Delete a project and all associated data."""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM fetched_papers WHERE project_id = ?", (project_id,))
            conn.execute("DELETE FROM saved_drafts WHERE project_id = ?", (project_id,))
            conn.execute("DELETE FROM report_sections WHERE project_id = ?", (project_id,))
            conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            conn.commit()
            return True
        finally:
            conn.close()

    # ''' Paper Operations ''''''''''''''''''''''''''''''''''''''''''''

    def save_papers(self, project_id: int, papers: List[Dict]) -> int:
        """Batch save fetched papers. Returns count of new papers saved."""
        conn = self._get_conn()
        saved = 0
        try:
            for paper in papers:
                doi = paper.get("doi", "") or ""
                title = (paper.get("title", "") or "")[:500]
                authors = paper.get("authors", "") or ""
                year = paper.get("year")
                journal = (paper.get("journal", "") or "")[:300]
                citations = paper.get("citations", 0) or 0
                url = paper.get("url", "") or ""
                abstract = (paper.get("abstract", "") or "")[:2000]

                existing = conn.execute(
                    "SELECT id FROM fetched_papers WHERE project_id = ? AND doi = ?",
                    (project_id, doi),
                ).fetchone()

                if not existing:
                    conn.execute(
                        """INSERT INTO fetched_papers 
                        (project_id, title, authors, year, journal, citations, doi, url, abstract)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (project_id, title, authors, year, journal, citations, doi, url, abstract),
                    )
                    saved = 1
            conn.commit()
        finally:
            conn.close()
        return saved

    def toggle_paper_check(self, paper_id: int, is_checked: bool) -> bool:
        """Toggle the checked status of a paper. Persists immediately."""
        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE fetched_papers SET is_checked = ? WHERE id = ?",
                (1 if is_checked else 0, paper_id),
            )
            conn.commit()
            return True
        finally:
            conn.close()

    def mark_paper_cited(self, paper_id: int, is_cited: bool = True) -> bool:
        """Mark a paper as having been cited in the report."""
        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE fetched_papers SET is_cited = ? WHERE id = ?",
                (1 if is_cited else 0, paper_id),
            )
            conn.commit()
            return True
        finally:
            conn.close()

    def update_paper_notes(self, paper_id: int, notes: str) -> bool:
        """Update user notes for a paper."""
        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE fetched_papers SET user_notes = ? WHERE id = ?",
                (notes, paper_id),
            )
            conn.commit()
            return True
        finally:
            conn.close()

    def update_paper_findings(self, paper_id: int, findings: str) -> bool:
        """Update user findings for a paper."""
        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE fetched_papers SET user_findings = ? WHERE id = ?",
                (findings, paper_id),
            )
            conn.commit()
            return True
        finally:
            conn.close()

    def get_papers(self, project_id: int, checked_only: bool = False, page: int = 0, per_page: int = 20) -> Tuple[List[Dict], int]:
        """Get papers for a project with pagination. Returns (papers, total_count)."""
        conn = self._get_conn()
        try:
            where = "project_id = ?"
            params = [project_id]
            if checked_only:
                where = " AND is_checked = 1"

            count_row = conn.execute(
                f"SELECT COUNT(*) as cnt FROM fetched_papers WHERE {where}", params
            ).fetchone()
            total = count_row["cnt"] if count_row else 0

            offset = page * per_page
            rows = conn.execute(
                f"SELECT * FROM fetched_papers WHERE {where} ORDER BY is_cited DESC, citations DESC, year DESC LIMIT ? OFFSET ?",
                params  [per_page, offset],
            ).fetchall()
            return [dict(r) for r in rows], total
        finally:
            conn.close()

    def get_bibliography(self, project_id: int) -> List[Dict]:
        """Get all checked papers (working bibliography)."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM fetched_papers WHERE project_id = ? AND is_checked = 1 ORDER BY is_cited DESC, citations DESC, year DESC",
                (project_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_paper(self, paper_id: int) -> Optional[Dict]:
        """Get a single paper by ID."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM fetched_papers WHERE id = ?", (paper_id,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    # ''' Draft Operations ''''''''''''''''''''''''''''''''''''''''''''

    def save_draft(self, project_id: int, section: str, content: str, citations_ids: List[int] = None) -> bool:
        """Save or update a draft section."""
        citations_json = json.dumps(citations_ids or [])
        conn = self._get_conn()
        try:
            existing = conn.execute(
                "SELECT id FROM saved_drafts WHERE project_id = ? AND section = ?",
                (project_id, section),
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE saved_drafts SET content = ?, citations_ids = ?, updated_at = ? WHERE id = ?",
                    (content, citations_json, datetime.now().isoformat(), existing["id"]),
                )
            else:
                conn.execute(
                    "INSERT INTO saved_drafts (project_id, section, content, citations_ids) VALUES (?, ?, ?, ?)",
                    (project_id, section, content, citations_json),
                )
            conn.commit()
            return True
        finally:
            conn.close()

    def load_draft(self, project_id: int, section: str) -> Optional[Dict]:
        """Load a draft section."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM saved_drafts WHERE project_id = ? AND section = ?",
                (project_id, section),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    # ''' Report Section Operations '''''''''''''''''''''''''''''''''''

    def update_report_section(self, section_id: int, content: str) -> bool:
        """Update a report section's content."""
        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE report_sections SET content = ?, updated_at = ? WHERE id = ?",
                (content, datetime.now().isoformat(), section_id),
            )
            conn.commit()
            return True
        finally:
            conn.close()

    def get_report_sections(self, project_id: int) -> List[Dict]:
        """Get all report sections for a project, ordered."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM report_sections WHERE project_id = ? ORDER BY section_order",
                (project_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def add_report_section(self, project_id: int, title: str, after_order: int = None) -> Optional[int]:
        """Add a custom report section."""
        conn = self._get_conn()
        try:
            if after_order is not None:
                conn.execute(
                    "UPDATE report_sections SET section_order = section_order  1 WHERE project_id = ? AND section_order > ?",
                    (project_id, after_order),
                )
                new_order = after_order  1
            else:
                max_row = conn.execute(
                    "SELECT MAX(section_order) as mx FROM report_sections WHERE project_id = ?",
                    (project_id,),
                ).fetchone()
                new_order = (max_row["mx"] or -1)  1
            cursor = conn.execute(
                "INSERT INTO report_sections (project_id, section_order, section_title, content) VALUES (?, ?, ?, '')",
                (project_id, new_order, title),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def delete_report_section(self, section_id: int) -> bool:
        """Delete a report section."""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM report_sections WHERE id = ?", (section_id,))
            conn.commit()
            return True
        finally:
            conn.close()

    # ''' Statistics ''''''''''''''''''''''''''''''''''''''''''''''''''

    def get_statistics(self, project_id: int) -> Dict:
        """Get summary statistics for a project."""
        conn = self._get_conn()
        try:
            total = conn.execute(
                "SELECT COUNT(*) as cnt FROM fetched_papers WHERE project_id = ?",
                (project_id,),
            ).fetchone()["cnt"]
            checked = conn.execute(
                "SELECT COUNT(*) as cnt FROM fetched_papers WHERE project_id = ? AND is_checked = 1",
                (project_id,),
            ).fetchone()["cnt"]
            cited = conn.execute(
                "SELECT COUNT(*) as cnt FROM fetched_papers WHERE project_id = ? AND is_cited = 1",
                (project_id,),
            ).fetchone()["cnt"]
            max_cited = conn.execute(
                "SELECT MAX(citations) as mx FROM fetched_papers WHERE project_id = ?",
                (project_id,),
            ).fetchone()["mx"] or 0
            recent_year = conn.execute(
                "SELECT MAX(year) as mx FROM fetched_papers WHERE project_id = ?",
                (project_id,),
            ).fetchone()["mx"] or 0
            earliest_year = conn.execute(
                "SELECT MIN(year) as mx FROM fetched_papers WHERE project_id = ? AND year IS NOT NULL",
                (project_id,),
            ).fetchone()["mx"] or 0
            return {
                "total_papers": total,
                "checked_papers": checked,
                "cited_papers": cited,
                "max_citations": max_cited,
                "year_range": f"{earliest_year}-{recent_year}" if earliest_year and recent_year else "N/A",
            }
        finally:
            conn.close()


# '''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
# 2. PAPER HARVESTER  Real academic APIs, zero hallucination
# '''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
class PaperHarvester:
    """
    Fetches REAL papers from Semantic Scholar and CrossRef.
    No AI generation  every paper returned is a real publication.
    Supports unlimited fetching using offset-based pagination.
    """

    SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1"
    CROSSREF_URL = "https://api.crossref.org/works"

    def __init__(self, timeout: int = 60):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "CHRISHEM-LiteratureEngine/2.0 (mailto:research@example.com)",
        })

    def search_semantic_scholar(
        self, query: str, limit: int = 100, fields: str = None, progress_callback=None
    ) -> List[Dict]:
        """
        Search Semantic Scholar for papers matching the query.
        Supports unlimited papers via pagination (API max 100 per request).
        Returns real papers with metadata  no hallucination possible.
        """
        if fields is None:
            fields = "title,authors,year,journal,citationCount,externalIds,url,abstract"

        papers = []
        batch_size = 100  # API max
        offset = 0
        max_pages = (limit // batch_size)  2

        try:
            for page_num in range(max_pages):
                if len(papers) >= limit:
                    break

                current_batch = min(batch_size, limit - len(papers))
                if current_batch <= 0:
                    break

                url = f"{self.SEMANTIC_SCHOLAR_URL}/paper/search"
                params = {
                    "query": query,
                    "limit": current_batch,
                    "offset": offset,
                    "fields": fields,
                }
                resp = self.session.get(url, params=params, timeout=self.timeout)
                if resp.status_code != 200:
                    break

                data = resp.json()
                results = data.get("data", [])
                if not results:
                    break

                for paper in results:
                    entry = self._parse_semantic_paper(paper)
                    if entry and entry.get("title"):
                        papers.append(entry)

                offset = len(results)
                if progress_callback:
                    progress_callback(len(papers), limit)

                if len(results) < current_batch:
                    break

                time.sleep(0.35)  # Rate limiting

        except requests.exceptions.Timeout:
            logger.warning("Semantic Scholar search timed out for query %r", query)
            st.warning("'' Semantic Scholar API timed out. Try a more specific query.")
        except requests.exceptions.ConnectionError:
            logger.warning("Could not connect to Semantic Scholar for query %r", query)
            st.warning("' Could not connect to Semantic Scholar API. Check your internet."),
        except Exception as e:
            logger.exception("Semantic Scholar search failed for query %r", query)
            st.warning(f"'' Semantic Scholar search error: {str(e)[:100]}")

        return papers[:limit]

    def _parse_semantic_paper(self, paper: dict) -> Optional[Dict]:
        """Parse a Semantic Scholar paper response into our standard format."""
        try:
            title = (paper.get("title") or "").strip()
            if not title:
                return None

            authors_raw = paper.get("authors", [])
            authors_list = []
            for a in authors_raw:
                if isinstance(a, dict):
                    name = a.get("name", "")
                    if name:
                        authors_list.append(name)
            authors_str = ", ".join(authors_list[:10])
            if len(authors_list) > 10:
                authors_str = " et al."

            external_ids = paper.get("externalIds", {}) or {}
            doi = external_ids.get("DOI", "")

            year = paper.get("year")
            if year and isinstance(year, (int, float)):
                year = int(year)
            else:
                year = None

            journal_data = paper.get("journal", {})
            journal = ""
            if isinstance(journal_data, dict):
                journal = journal_data.get("name", "") or ""

            url = paper.get("url", "")
            if not url and doi:
                url = f"https://doi.org/{doi}"

            return {
                "title": title,
                "authors": authors_str,
                "year": year,
                "journal": journal,
                "citations": paper.get("citationCount", 0) or 0,
                "doi": doi,
                "url": url,
                "abstract": (paper.get("abstract") or "")[:2000],
            }
        except Exception:
            logger.warning("Could not normalise Semantic Scholar paper record", exc_info=True)
            return None

    def search_crossref(self, query: str, limit: int = 50, offset: int = 0) -> List[Dict]:
        """Search CrossRef for papers. Good fallback if Semantic Scholar is down."""
        papers = []
        try:
            params = {
                "query": query,
                "rows": min(limit, 50),
                "offset": offset,
                "sort": "relevance",
                "order": "desc",
            }
            resp = self.session.get(self.CROSSREF_URL, params=params, timeout=self.timeout)
            if resp.status_code != 200:
                logger.error(
                    "CrossRef search for %r failed: %s  %s",
                    query, resp.status_code, resp.text[:200],
                )
                st.warning(f"'' CrossRef returned HTTP {resp.status_code}  no results from this source.")
                return papers

            data = resp.json()
            items = data.get("message", {}).get("items", [])

            for item in items:
                entry = self._parse_crossref_item(item)
                if entry and entry.get("title"):
                    papers.append(entry)

        except requests.exceptions.Timeout:
            logger.warning("CrossRef search timed out for query %r", query)
            st.warning("'' CrossRef API timed out.")
        except requests.exceptions.ConnectionError:
            logger.warning("Could not connect to CrossRef for query %r", query)
            st.warning("Could not connect to CrossRef API.")
        except Exception as e:
            logger.exception("CrossRef search failed for query %r", query)
            st.warning(f"'' CrossRef search error: {str(e)[:100]}")

        return papers[:limit]

    def _parse_crossref_item(self, item: dict) -> Optional[Dict]:
        try:
            title_list = item.get("title", [])
            title = title_list[0] if title_list else ""
            if not title:
                return None

            authors_raw = item.get("author", [])
            authors_list = []
            for a in authors_raw:
                given = a.get("given", "")
                family = a.get("family", "")
                if given and family:
                    authors_list.append(f"{family}, {given}")
                elif family:
                    authors_list.append(family)
            authors_str = ", ".join(authors_list[:10])
            if len(authors_list) > 10:
                authors_str = " et al."

            date_parts = item.get("issued", {}).get("date-parts", [[]])
            year = date_parts[0][0] if date_parts and date_parts[0] else None

            journal = item.get("container-title", [""])
            journal = journal[0] if journal else ""

            doi = item.get("DOI", "")
            url = f"https://doi.org/{doi}" if doi else item.get("URL", "")

            return {
                "title": title,
                "authors": authors_str,
                "year": year,
                "journal": journal,
                "citations": 0,
                "doi": doi,
                "url": url,
                "abstract": "",
            }
        except Exception:
            logger.warning("Could not normalise CrossRef paper record", exc_info=True)
            return None

    def search_combined(
        self, query: str, country: str = "", limit: int = 100
    ) -> List[Dict]:
        """
        Search Semantic Scholar (primary) and CrossRef (fallback).
        Supports unlimited paper count  paginates through API results.
        Prioritizes papers relevant to the country of study if provided.
        """
        all_papers = []

        ss_papers = self.search_semantic_scholar(query, limit=limit)
        all_papers.extend(ss_papers)

        if len(all_papers) < limit:
            remaining = limit - len(all_papers)
            cr_papers = self.search_crossref(query, limit=min(remaining, 50))
            all_papers.extend(cr_papers)

        # Deduplicate by DOI
        seen_dois = set()
        deduped = []
        for p in all_papers:
            doi = p.get("doi", "") or p.get("title", "")
            if doi not in seen_dois:
                seen_dois.add(doi)
                deduped.append(p)

        # Country boost
        if country and len(deduped) > 5:
            country_query = f"{query} {country.strip()}"
            country_papers = self.search_semantic_scholar(country_query, limit=30)
            if country_papers:
                country_dois = {p.get("doi", "") for p in country_papers if p.get("doi")}
                deduped = [p for p in country_papers if p.get("doi") not in country_dois]  deduped

        return deduped[:limit]


# '''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
# 3. REFERENCE FORMATTER  Mechanical, zero-AI citation formatting
# '''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
class ReferenceFormatter:
    """Formats references mechanically using citeproc-py or regex."""

    SUPPORTED_STYLES = ["apa", "harvard", "chicago", "mla", "vancouver"]

    def __init__(self):
        self._citeproc_available = self._check_citeproc()

    def _check_citeproc(self) -> bool:
        try:
            import citeproc  # noqa
            return True
        except ImportError:
            return False

    def format_references(self, papers: List[Dict], style: str = "apa") -> str:
        """Format a complete reference list in the specified style."""
        if not papers:
            return "No references to format."

        if self._citeproc_available and style in self.SUPPORTED_STYLES:
            try:
                return self._format_with_citeproc(papers, style)
            except Exception:
                logger.warning(
                    "citeproc formatting failed for style %r  falling back to manual formatting",
                    style, exc_info=True,
                )
        return self._format_manual(papers, style)

    def format_citation(self, paper: Dict, style: str = "apa", inline: bool = True) -> str:
        """Format a single in-text citation."""
        authors = paper.get("authors", "")
        year = paper.get("year")
        if not authors:
            return f"({year})" if year else "(Unknown)"

        first_author = authors.split(",")[0].strip()
        if "et al" in first_author:
            first_author = authors.split("et al")[0].strip().rstrip(",")
        last_name = first_author.split()[-1] if first_author else "Unknown"

        styles = {
            "apa": (f"{last_name} ({year})" if year else last_name,
                    f"({last_name}, {year})" if year else f"({last_name})"),
            "harvard": (f"{last_name} ({year})" if year else last_name,
                        f"({last_name}, {year})" if year else f"({last_name})"),
            "chicago": (f"{last_name} {year}" if year else last_name,
                        f"({last_name} {year})" if year else f"({last_name})"),
            "mla": (f"({last_name} {year})" if year else f"({last_name})",
                    f"({last_name} {year})" if year else f"({last_name})"),
            "vancouver": (f"[{paper.get('id', '?')}]", f"[{paper.get('id', '?')}]"),
        }
        result = styles.get(style, styles["apa"])
        return result[0] if inline else result[1]

    def _format_with_citeproc(self, papers: List[Dict], style: str) -> str:
        from citeproc import CitationStylesBibliography, CitationStylesStyle, Citation, CitationItem
        from citeproc.source.json import CiteProcJSON

        csl_items = []
        for i, paper in enumerate(papers):
            csl_item = self._paper_to_csl_json(paper, i  1)
            if csl_item:
                csl_items.append(csl_item)

        style_name = style.lower().replace("harvard", "apa")
        try:
            bib_style = CitationStylesStyle(style_name)
            bibliography = CitationStylesBibliography(bib_style, CiteProcJSON(csl_items))
            for item in csl_items:
                bibliography.register(Citation([CitationItem(item["id"])]))
            bibliography.sort()
            formatted = []
            for item in bibliography.items:
                formatted.append(str(item))
            return "\n\n".join(formatted) if formatted else self._format_manual(papers, style)
        except Exception:
            logger.warning(
                "citeproc rendering failed for style %r  falling back to manual formatting",
                style, exc_info=True,
            )
            return self._format_manual(papers, style)

    def _paper_to_csl_json(self, paper: Dict, index: int) -> Optional[Dict]:
        try:
            csl = {"id": f"ref-{index}", "type": "article-journal", "title": paper.get("title", "")}
            authors_str = paper.get("authors", "")
            if authors_str:
                csl["author"] = []
                for author_name in authors_str.split(", "):
                    name_parts = author_name.strip().split()
                    if len(name_parts) >= 2:
                        csl["author"].append({"family": name_parts[-1], "given": " ".join(name_parts[:-1])})
                    elif len(name_parts) == 1:
                        csl["author"].append({"family": name_parts[0], "given": ""})
            if paper.get("year"):
                csl["issued"] = {"date-parts": [[paper["year"]]]}
            if paper.get("journal"):
                csl["container-title"] = paper["journal"]
            if paper.get("doi"):
                csl["DOI"] = paper["doi"]
            if paper.get("url"):
                csl["URL"] = paper["url"]
            return csl
        except Exception:
            logger.warning("Could not build CSL record for paper %r", paper.get("title"), exc_info=True)
            return None

    def _format_manual(self, papers: List[Dict], style: str) -> str:
        references = []
        for i, paper in enumerate(papers):
            ref = self._format_one_manual(paper, style, i  1)
            if ref:
                references.append(ref)
        return "\n\n".join(references) if references else "No references to format."

    def _format_one_manual(self, paper: Dict, style: str, index: int) -> str:
        title = paper.get("title", "").strip()
        if not title:
            return ""
        authors = paper.get("authors", "Unknown")
        year = paper.get("year")
        journal = paper.get("journal", "")
        doi = paper.get("doi", "")
        url = paper.get("url", "")
        year_str = f"({year})" if year else "(n.d.)"

        if style == "apa":
            ref = f"{authors} {year_str}. {title}."
            if journal:
                ref = f" *{journal}*."
            if doi:
                ref = f" https://doi.org/{doi}"
            elif url:
                ref = f" {url}"
        elif style == "harvard":
            ref = f"{authors} {year_str}, '{title}-,"
            if journal:
                ref = f" *{journal}*,"
            if doi:
                ref = f" doi:{doi}"
            elif url:
                ref = f" Available at: {url}"
        elif style == "chicago":
            ref = f"{authors}. {year_str}. \"{title}.\""
            if journal:
                ref = f" *{journal}*."
            if doi:
                ref = f" https://doi.org/{doi}"
            elif url:
                ref = f" {url}"
        elif style == "mla":
            ref = f"{authors}. \"{title}.\""
            if journal:
                ref = f" *{journal}*,"
            ref = f" {year_str}."
            if doi:
                ref = f" doi:{doi}"
        elif style == "vancouver":
            ref = f"{index}. {authors}. {title}."
            if journal:
                ref = f" {journal}."
            ref = f" {year_str}."
            if doi:
                ref = f" DOI: {doi}"
        else:
            ref = f"{authors} {year_str}. {title}."
            if journal:
                ref = f" {journal}."
            if doi:
                ref = f" doi:{doi}"
        return ref.strip()

    def generate_bibtex(self, papers: List[Dict]) -> str:
        lines = [
            "% BibTeX file generated by CHRISHEM Literature Engine",
            f"% Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"% Total entries: {len(papers)}",
            "% ZERO AI-hallucinated content. Metadata sourced from real academic APIs.",
            "",
        ]
        for i, paper in enumerate(papers):
            doi = paper.get("doi", "")
            cite_key = self._generate_cite_key(paper, doi, i  1)
            title = paper.get("title", "").strip()
            authors = paper.get("authors", "")
            year = paper.get("year")
            journal = paper.get("journal", "")
            url = paper.get("url", "")

            bib = [f"@article{{{cite_key},", f"  title = {{{title}}},"]
            if authors:
                bib_authors = self._authors_to_bibtex(authors)
                bib.append(f"  author = {{{bib_authors}}},")
            if year:
                bib.append(f"  year = {{{year}}},")
            if journal:
                bib.append(f"  journal = {{{journal}}},")
            if doi:
                bib.append(f"  doi = {{{doi}}},")
            if url:
                bib.append(f"  url = {{{url}}},")
            bib.append("}")
            lines.append("\n".join(bib))
            lines.append("")
        return "\n".join(lines)

    def _generate_cite_key(self, paper: Dict, doi: str, index: int) -> str:
        if doi:
            key = doi.split("/")[-1] if "/" in doi else doi
            return re.sub(r'[^a-zA-Z0-9_]', '_', key)
        first_author = paper.get("authors", "Unknown").split(",")[0].strip()
        last_name = first_author.split()[-1] if first_author else "Unknown"
        year = paper.get("year", "0000")
        title_words = paper.get("title", "").split()[:3]
        title_part = "_".join(w.lower().strip(".,;:!?") for w in title_words)
        return f"{last_name}{year}_{title_part}" if title_part else f"{last_name}{year}_{index}"

    def _authors_to_bibtex(self, authors_str: str) -> str:
        authors_list = []
        for author in authors_str.split(", "):
            name_parts = author.strip().split()
            if len(name_parts) >= 2:
                authors_list.append(f"{name_parts[-1]}, {' '.join(name_parts[:-1])}")
            else:
                authors_list.append(author.strip())
        return " and ".join(authors_list)


# '''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
# 4. EXPORT ENGINE  Multi-format export utilities
# '''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
class ExportEngine:
    """
    Handles exporting reports and references in multiple formats.
    Supports: Markdown, HTML, Plain Text, BibTeX (.bib), Notion Push, Google Drive.
    """

    @staticmethod
    def get_markdown_download_link(content: str, filename: str, label: str = "Download") -> str:
        """Generate a base64 download link for markdown content."""
        b64 = base64.b64encode(content.encode()).decode()
        return f'<a href="data:text/markdown;base64,{b64}" download="{filename}" style="display:inline-block;padding:10px 20px;background:#1d4ed8;color:white;border-radius:8px;text-decoration:none;font-weight:600;">🔍 {label}</a>'

    @staticmethod
    def get_html_download_link(content_md: str, filename: str, label: str = "Download HTML") -> str:
        """Convert markdown to simple HTML and generate download link."""
        # Basic markdown to HTML conversion
        html_content = content_md.replace("&", "&amp;").replace("<", "<").replace(">", ">")
        html_lines = ["<!DOCTYPE html><html><head><meta charset='utf-8'>",
                      f"<title>{filename}</title>",]
        html_lines.append("</head><body>")
        for line in html_content.split("\n"):
            if line.startswith("# "):
                html_lines.append(f"<h1>{line[2:]}</h1>")
            elif line.startswith("## "):
                html_lines.append(f"<h2>{line[3:]}</h2>")
            elif line.startswith("### "):
                html_lines.append(f"<h3>{line[4:]}</h3>")
            else:
                html_lines.append(f"<p>{line}</p>")
        html_lines.append("</body></html>")
        full_html = "\n".join(html_lines)
        b64 = base64.b64encode(full_html.encode()).decode()
        return f'<a href="data:text/html;base64,{b64}" download="{filename}" style="display:inline-block;padding:10px 20px;background:#1d4ed8;color:white;border-radius:8px;text-decoration:none;font-weight:600;">🔍 {label}</a>'

    @staticmethod
    def render_sidebar_styles():
        st.markdown("""<style>
        /* --- GLOBAL SIDEBAR DARK THEMING OVERRIDE --- */
        [data-testid="stSidebar"], section[data-testid="stSidebar"] {
            background-color: #090d16 !important;
            border-right: 1px solid #1e293b !important;
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
        </style>""", unsafe_allow_html=True)
    def get_txt_download_link(content: str, filename: str, label: str = "Download TXT") -> str:
        """Generate a base64 download link for plain text."""
        b64 = base64.b64encode(content.encode()).decode()
        return f'<a href="data:text/plain;base64,{b64}" download="{filename}" style="display:inline-block;padding:10px 20px;background:#059669;color:white;border-radius:8px;text-decoration:none;font-weight:600;">🔍 Download .BIB</a>'

    @staticmethod
    def get_bib_download_link(bib_content: str, filename: str) -> str:
        """Generate a download link for .bib file."""
        b64 = base64.b64encode(bib_content.encode()).decode()
        return f'<a href="data:text/plain;base64,{b64}" download="{filename}" style="display:inline-block;padding:10px 20px;background:#059669;color:white;border-radius:8px;text-decoration:none;font-weight:600;">🔍 Download .BIB</a>'

    @staticmethod
    def get_copy_js(text: str, button_label: str = "' Copy to Clipboard") -> str:
        """Generate a JavaScript-powered copy button."""
        escaped = html.escape(text.replace("`", "\\`").replace("${", "\\${"))
        return f"""
    html_code = f'''<button onclick="navigator.clipboard.writeText(`{escaped}`).then(() => {{this.innerHTML='Copied!';setTimeout(()=>this.innerHTML='{button_label}',2000)}})" style="padding:8px 16px;background:#0284c7;color:white;border:none;border-radius:6px;cursor:pointer;">{button_label}</button>'''
                style="padding:10px 20px;background:#1d4ed8;color:white;border:none;border-radius:8px;cursor:pointer;font-weight:600;">
            {button_label}
        </button>
        """

    @staticmethod
    def get_notion_push_html(report_text: str, style: str = "apa") -> str:
        """
        Generate HTML that opens Notion with pre-filled content.
        Users can paste this into a Notion page.
        """
        escaped = html.escape(report_text[:5000])  # Limit to 5000 chars for performance
        return f"""
        <div style="padding:12px;background:#f0f4ff;border-radius:8px;border:1px solid #dbeafe;">
    <p style="margin:0 0 8px 0;font-weight:600;">🔍 Push to Notion</p>
            <p style="font-size:0.85rem;color:#475569;">Copy this content and paste it into a new Notion page:</p>
            <pre style="background:white;padding:12px;border-radius:6px;font-size:0.8rem;max-height:200px;overflow:auto;white-space:pre-wrap;">{escaped}</pre>
            {ExportEngine.get_copy_js(report_text, "' Copy for Notion")}'
        </div>
        """

    @staticmethod
    def get_google_drive_button() -> str:
        """Generate a styled link to open Google Drive for manual upload."""
        return """
        <a href="https://drive.google.com/drive/u/0/my-drive" target="_blank" 
           style="display:inline-block;padding:10px 20px;background:#4285F4;color:white;border-radius:8px;text-decoration:none;font-weight:600;"🔍 Open Google Drive
        </a>
        <p style="font-size:0.8rem;color:#64748b;margin-top:4px;">Download the file above, then upload it to your Drive</p>
        """


# '''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
# 5. EFFECT SIZE EXTRACTOR  Bridge to Hypothesis Generator
# '''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
class EffectSizeExtractor:
    """
    Extracts reported effect sizes from paper metadata and user annotations.
    Provides a standardized format for the Hypothesis Generator\'s'
    compare_against_literature() method.
    
    Supports:
      - Regex extraction from abstracts (Cohen's d, r, OR, RR, eta-squared)'
      - Manual user input via structured form
      - Database persistence of extracted effect sizes
      - Export in hypothesis-compatible format
    """

    # Regex patterns for common effect size reporting formats
    EFFECT_PATTERNS = {
        "cohens_d": [
            r"(?:Cohens?\s*[dD]|[dD]\s*=)\s*([-]?\d\.?\d*)",
            r"[dD]\s*=\s*([-]?\d\.?\d*)",
            r"effect\ssize\s*(?:of\s*)?([-]?\d\.?\d*)",
        ],
        "pearson_r": [
            r"(?:Pearson\s*)?[rR]\s*=\s*([-]?\d\.?\d*)",
            r"correlation\s*(?:of\s*)?([-]?\d\.?\d*)",
            r"[rR]\s*=\s*([-]?\d\.?\d*)",
        ],
        "odds_ratio": [
            r"(?:odds\s*ratio|OR)\s*(?:=\s*)?([-]?\d\.?\d*)",
            r"OR\s*=\s*([-]?\d\.?\d*)",
        ],
        "eta_squared": [
            r"(?:eta[\s-]*squared|''|\u03b7')\s*(?:=\s*)?([-]?\d\.?\d*)",
            r"\u03b7\s*=\s*([-]?\d\.?\d*)",
        ],
        "f_statistic": [
            r"[Ff]\s*\([^)]\)\s*=\s*([-]?\d\.?\d*)",
        ],
        "t_statistic": [
            r"[Tt]\s*\([^)]\)\s*=\s*([-]?\d\.?\d*)",
        ],
        "beta_coeff": [
            r"['\u03b2]\s*=\s*([-]?\d\.?\d*)",
            r"beta\s*=\s*([-]?\d\.?\d*)",
        ],
        "sample_size": [
            r"[Nn]\s*=\s*(\d)",
            r"[nN]\s*=\s*(\d)",
            r"(?:total|overall)\s*[Nn]\s*=\s*(\d)",
        ],
    }

    # Mapping from extracted stat type to hypothesis effect type
    STAT_TO_EFFECT_MAP = {
        "cohens_d": "cohens_d",
        "pearson_r": "r",
        "eta_squared": "eta_squared",
        "odds_ratio": "or",
    }

    def __init__(self, db: Optional[LiteratureDatabase] = None):
        self.db = db or LiteratureDatabase()
        self._ensure_effect_sizes_table()

    def _ensure_effect_sizes_table(self):
        """Create the effect_sizes table if it doesn't exist."""
        conn = self.db._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS paper_effect_sizes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    paper_id INTEGER NOT NULL,
                    project_id INTEGER NOT NULL,
                    variable_pair TEXT NOT NULL DEFAULT '',
                    effect_type TEXT NOT NULL DEFAULT 'cohens_d',
                    effect_size REAL NOT NULL DEFAULT 0,
                    ci_lower REAL,
                    ci_upper REAL,
                    sample_size INTEGER,
                    source TEXT DEFAULT '',
                    notes TEXT DEFAULT '',
                    extracted_by TEXT DEFAULT 'manual',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (paper_id) REFERENCES fetched_papers(id) ON DELETE CASCADE,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_effect_sizes_paper 
                    ON paper_effect_sizes(paper_id);
                CREATE INDEX IF NOT EXISTS idx_effect_sizes_project 
                    ON paper_effect_sizes(project_id);
            """)
            conn.commit()
        finally:
            conn.close()

    def extract_from_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Scan text (abstract, findings) for reported effect sizes.
        Returns list of extracted effect dicts.
        """
        extracted = []

        for stat_type, patterns in self.EFFECT_PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    try:
                        value = float(match)
                        # Map to effect type
                        effect_type = self.STAT_TO_EFFECT_MAP.get(stat_type, stat_type)
                        extracted.append({
                            "effect_type": effect_type,
                            "effect_size": value,
                            "stat_type": stat_type,
                            "raw_match": match,
                            "extracted_by": "regex",
                        })
                    except (ValueError, TypeError):
                        continue

        # Deduplicate by effect_type, keeping the first occurrence
        seen_types = set()
        deduped = []
        for e in extracted:
            if e["effect_type"] not in seen_types:
                seen_types.add(e["effect_type"])
                deduped.append(e)

        return deduped

    def extract_from_paper(self, paper: Dict) -> List[Dict[str, Any]]:
        """
        Extract effect sizes from a paper's abstract and findings.'
        Returns list of dicts compatible with hypothesis_generator.
        """
        extracted = []

        # Try abstract
        abstract = paper.get("abstract", "") or ""
        if abstract:
            extracted.extend(self.extract_from_text(abstract))

        # Try user findings
        findings = paper.get("user_findings", "") or ""
        if findings:
            extracted.extend(self.extract_from_text(findings))

        return extracted

    def save_effect_size(
        self,
        paper_id: int,
        project_id: int,
        variable_pair: str,
        effect_type: str = "cohens_d",
        effect_size: float = 0.0,
        ci_lower: Optional[float] = None,
        ci_upper: Optional[float] = None,
        sample_size: Optional[int] = None,
        source: str = "",
        notes: str = "",
        extracted_by: str = "manual",
    ) -> int:
        """Save a manually entered or extracted effect size. Returns record ID."""
        conn = self.db._get_conn()
        try:
            cursor = conn.execute(
                """INSERT INTO paper_effect_sizes 
                   (paper_id, project_id, variable_pair, effect_type, effect_size,
                    ci_lower, ci_upper, sample_size, source, notes, extracted_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (paper_id, project_id, variable_pair, effect_type, effect_size,
                 ci_lower, ci_upper, sample_size, source[:200], notes, extracted_by),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_project_effect_sizes(self, project_id: int) -> List[Dict]:
        """
        Get all effect sizes for a project.
        Returns list of dicts in hypothesis_generator format.
        """
        conn = self.db._get_conn()
        try:
            rows = conn.execute(
                """SELECT es.*, p.title as paper_title, p.authors as paper_authors
                   FROM paper_effect_sizes es
                   JOIN fetched_papers p ON es.paper_id = p.id
                   WHERE es.project_id = ?
                   ORDER BY es.created_at DESC""",
                (project_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def export_for_hypothesis_generator(self, project_id: int) -> List[Dict]:
        """
        Export effect sizes in the format expected by
        HypothesisGenerator.compare_against_literature().
        """
        raw_sizes = self.get_project_effect_sizes(project_id)
        formatted = []
        for es in raw_sizes:
            formatted.append({
                "variable_pair": es.get("variable_pair", ""),
                "effect_size": es.get("effect_size", 0),
                "ci_lower": es.get("ci_lower", es.get("effect_size", 0) * 0.8),
                "ci_upper": es.get("ci_upper", es.get("effect_size", 0) * 1.2),
                "n": es.get("sample_size", 30),
                "source": es.get("paper_title", es.get("source", "unknown")),
                "effect_type": es.get("effect_type", "cohens_d"),
                "paper_id": es.get("paper_id", 0),
            })
        return formatted

    def delete_effect_size(self, effect_id: int) -> bool:
        """Delete an effect size record."""
        conn = self.db._get_conn()
        try:
            conn.execute("DELETE FROM paper_effect_sizes WHERE id = ?", (effect_id,))
            conn.commit()
            return True
        finally:
            conn.close()


# '''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
# 6. DRAFTING ENGINE  Human-authored, machine-structured
# '''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
class DraftingEngine:
    """Helps users structure their research writing. NO AI text generation."""

    REPORT_SECTIONS = ["Introduction", "Literature Review", "Methodology", "Findings & Discussion", "Conclusion"]

    @staticmethod
    def build_final_report(sections, bibliography, style="apa", include_abstract=False, author_name=""):
        parts = []
        project_name = "Research Paper"
        if sections:
            project_name = sections[0].get("project_name", "Research Paper")
        parts.append(f"# {project_name}\n")
        if author_name:
            parts.append(f"**Author:** {author_name}\n")
        parts.append(f"**Date:** {datetime.now().strftime('%B %d, %Y')}\n")
        parts.append("---\n")

        if include_abstract:
            parts.append("## Abstract\n*Write your abstract here.*\n\n---\n")

        formatter = ReferenceFormatter()
        for section in sections:
            title = section.get("section_title", "Section")
            content = section.get("content", "").strip()
            if content:
                parts.append(f"## {title}\n\n{content}\n\n---\n")

        if bibliography:
            parts.append("## References\n\n")
            ref_text = formatter.format_references(bibliography, style)
            parts.append(ref_text  "\n")

        parts.append("\n---\n## Appendices\n*Add supplementary materials here.*")
        return "\n".join(parts)


# '''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
# 6. UI HELPERS
# '''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

def render_paper_table_row(paper: Dict, db: LiteratureDatabase, style: str = "apa") -> None:
    """Render a single paper row in the harvest/bibliography views."""
    col1, col2 = st.columns([0.05, 0.95])

    with col1:
        checked = st.checkbox(
            "",
            value=bool(paper["is_checked"]),
            key=f"check_{paper['id']}",
            label_visibility="collapsed",
            on_change=lambda pid=paper["id"], c=not paper["is_checked"]: db.toggle_paper_check(pid, c),
        )

        with col2:
            # Show cited badge if this paper has been used in the report
            cited_badge = " 🔍 Cited" if paper.get("is_cited") else ""
            meta_parts = []
            if paper.get("authors"):
                meta_parts.append(f"🔍 {paper['authors']}")
            if paper.get("year"):
                meta_parts.append(f"🔍 {paper['year']}")
            if paper.get("citations"):
                meta_parts.append(f"🔍 {paper['citations']:,} citations")
            if paper.get("journal"):
                meta_parts.append(f"🔍 {paper['journal']}")
            if paper.get("doi"):
            meta_parts.append(f"' DOI: {paper['doi']}")'

        st.caption(" | ".join(meta_parts))

        with st.expander("'" View details & add notes/findings"):"
            tab_a, tab_b, tab_c = st.tabs(["Abstract", "My Notes", "My Findings"])

            with tab_a:
                if paper["abstract"]:
                    st.markdown(paper["abstract"])
                else:
                    st.info("No abstract available for this paper.")
                if paper["url"]:
                    st.markdown(f"[' Open paper ']({paper['url']})")

            with tab_b:
                current_notes = paper.get("user_notes", "") or ""
                new_notes = st.text_area("Your personal notes", value=current_notes,
                    key=f"notes_{paper['id']}", height=80,
                    placeholder="Add your observations, critiques, or key takeaways...",
                    label_visibility="collapsed")
                if new_notes != current_notes:
                    db.update_paper_notes(paper["id"], new_notes)
                    st.success("'" Notes saved!", icon="'")"

            with tab_c:
                current_finding = paper.get("user_findings", "") or ""
                new_finding = st.text_area("Your finding / contribution", value=current_finding,
                    key=f"finding_{paper['id']}", height=100,
                    placeholder="What key finding does this paper contribute to YOUR research?",
                    label_visibility="collapsed")
                if new_finding != current_finding:
                    db.update_paper_findings(paper["id"], new_finding)
                    st.success("'" Finding saved!", icon="'")"

                formatter = ReferenceFormatter()
                citation = formatter.format_citation(paper, style, inline=False)
                if citation:
                    st.code(citation, language="text")


def render_report_builder(sections, bibliography, db, project_id):
    """Render the full report builder with export options."""
    formatter = ReferenceFormatter()
    exporter = ExportEngine()
    style = st.selectbox("Citation Style", options=["apa", "harvard", "chicago", "mla", "vancouver"],
                         format_func=lambda s: s.upper(), key="report_style")

    st.markdown("---")

    section_contents = {s["id"]: s["content"] or "" for s in sections}

    for section in sections:
        sid = section["id"]
        title = section["section_title"]
        with st.expander(f"' {title}", expanded=(title == "Introduction")):'
            content = st.text_area(f"Write your {title}", value=section_contents.get(sid, ""),
                key=f"report_{sid}", height=200, placeholder=f"Write your {title} content here...",
                label_visibility="collapsed")
            if content != section_contents.get(sid, ""):
                db.update_report_section(sid, content)
                st.success(f"'" {title} saved!", icon="'")"

            # Citation insertion helper
            if bibliography and content:
                st.markdown("**Insert citation:**")
                bib_options = {f"{p['title'][:60]}... ({p.get('year', 'n.d.')})": p for p in bibliography}
                if bib_options:
                    selected = st.selectbox("Select a paper to cite", options=list(bib_options.keys()),
                        key=f"cite_{sid}", label_visibility="collapsed")
                    if selected:
                        paper = bib_options[selected]
                        citation = formatter.format_citation(paper, style, inline=False)
                        # Mark paper as cited
                        db.mark_paper_cited(paper["id"], True)
                        st.code(citation, language="text")
                        st.markdown(f"""
    html_code = f'''<button onclick="navigator.clipboard.writeText(`{escaped}`).then(() => {{this.innerHTML='Copied!';setTimeout(()=>this.innerHTML='{button_label}',2000)}})" style="padding:8px 16px;background:#0284c7;color:white;border:none;border-radius:6px;cursor:pointer;">{button_label}</button>'''
                                style="padding:6px 16px;border-radius:6px;border:1px solid #1d4ed8;"
                                background:#eff6ff;color:#1d4ed8;cursor:pointer;font-weight:600;">"
                            ' Copy Citation'
                        </button>""", unsafe_allow_html=True)

    # Add custom section
    st.markdown("---")
    col1, col2 = st.columns([3, 1])
    with col1:
        new_section_title = st.text_input("Add a custom section", placeholder="e.g., Data Collection Procedure")
    with col2:
        if st.button("' Add Section", use_container_width=True) and new_section_title.strip():'
            db.add_report_section(project_id, new_section_title.strip())
            st.rerun()

    # ''' EXPORT SECTION  Enhanced Multi-Format Exports ''''
    st.markdown("---")
    st.subheader("' Export Your Report")'
    st.caption("Download in multiple formats, push to Notion, or save to Google Drive.")

    col1, col2, col3 = st.columns(3)
    with col1:
        author_name = st.text_input("Author name (optional)", placeholder="Dr. Jane Smith", key="export_author")
    with col2:
        include_abstract = st.checkbox("Include Abstract section", value=False)
    with col3:
        report_title = st.text_input("Report title", value="Research Paper", key="export_title")

    if st.button("' Generate Complete Report", type="primary", use_container_width=True):'
        updated_sections = db.get_report_sections(project_id)
        bibliography = db.get_bibliography(project_id)
        for s in updated_sections:
            s["project_name"] = report_title

        report_text = DraftingEngine.build_final_report(
            sections=updated_sections, bibliography=bibliography,
            style=style, include_abstract=include_abstract, author_name=author_name,
        )
        st.session_state["_generated_report"] = report_text
        st.session_state["_generated_report_style"] = style
        st.success("'" Report generated! Choose your export format below.")"

    if st.session_state.get("_generated_report"):
        report_text = st.session_state["_generated_report"]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        bib_papers = db.get_bibliography(project_id)
        bib_content = formatter.generate_bibtex(bib_papers)

        # Format downloads
        st.markdown("#### ' Download Options")'
        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            st.markdown(exporter.get_markdown_download_link(report_text, f"report_{timestamp}.md", "Download MD"), unsafe_allow_html=True)
        with col_b:
            st.markdown(exporter.get_html_download_link(report_text, f"report_{timestamp}.html", "Download HTML"), unsafe_allow_html=True)
        with col_c:
            st.markdown(exporter.get_txt_download_link(report_text, f"report_{timestamp}.txt", "Download TXT"), unsafe_allow_html=True)
        with col_d:
            st.markdown(exporter.get_bib_download_link(bib_content, f"references_{timestamp}.bib"), unsafe_allow_html=True)

        # Copy to clipboard
        st.markdown("#### ' Copy to Clipboard")'
        st.markdown(exporter.get_copy_js(report_text, "' Copy Report to Clipboard"), unsafe_allow_html=True)'

        # Notion push
    <p style="margin:0 0 8px 0;font-weight:600;">🔍 Push to Notion</p>
        st.markdown(exporter.get_notion_push_html(report_text, style), unsafe_allow_html=True)

        # Google Drive
        st.markdown("#### '' Save to Google Drive")
        st.markdown(exporter.get_google_drive_button(), unsafe_allow_html=True)

        # Preview
        with st.expander("'" Preview Report", expanded=False):"
            st.markdown(report_text)

\"\"\""