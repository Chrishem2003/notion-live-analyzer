"""
agents.py — The actual multi-agent problem solver, distinct from the
deterministic "Autonomous Agent Console" already in 4___ML_Predictive_Studio.py
(that one runs a single pre-picked analysis; this one runs three specialist
agents against ONE problem statement, in parallel, and has a synthesis agent
combine their real findings).

Three nodes:
  - research_node   : real CrossRef search — same API the Literature hub and
                       tasks.harvest_literature_task use, kept lightweight
                       (this runs inline in a graph call, not queued).
  - audit_node       : real pandas/IQR data-quality audit of whatever
                       DataFrame the caller passes in (or an honest "no
                       dataset supplied" note — never a fabricated audit).
  - synthesis_node    : if GEMINI_API_KEY is configured, a real Gemini call
                       grounded in the other two agents' actual findings.
                       If not configured, this does NOT fake an AI response
                       (see portal.py's changelog on why that's a hard line
                       for this project) — it returns a structured merge of
                       the real findings and says plainly that no LLM is
                       wired up.

Every node catches its own exceptions and records them in state["errors"]
rather than crashing the whole run — a literature-API outage shouldn't take
down the audit findings too.
"""

import os
import operator
from typing import TypedDict, Annotated, Optional

import pandas as pd
import numpy as np
import requests
from langgraph.graph import StateGraph, START, END

try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


class SwarmState(TypedDict):
    problem: str
    dataset: Optional[pd.DataFrame]
    literature_findings: Optional[dict]
    audit_findings: Optional[dict]
    synthesis: Optional[str]
    errors: Annotated[list, operator.add]


# ──────────────────────────────────────────────────────────────────
# Agent 1: Research & Literature Specialist
# ──────────────────────────────────────────────────────────────────
def research_node(state: SwarmState) -> dict:
    query = state["problem"]
    try:
        resp = requests.get(
            "https://api.crossref.org/works",
            params={"query": query, "rows": 15, "sort": "relevance"},
            timeout=15,
            headers={"User-Agent": "ChrishemAgentSwarm/1.0 (mailto:research@chrishem.local)"},
        )
        resp.raise_for_status()
        items = resp.json().get("message", {}).get("items", [])

        papers = []
        for it in items:
            title_list = it.get("title")
            title = title_list[0] if title_list else "Untitled"
            year = None
            for key in ("published-print", "published-online", "issued"):
                dp = it.get(key, {}).get("date-parts")
                if dp and dp[0] and dp[0][0]:
                    year = dp[0][0]
                    break
            papers.append({
                "title": title,
                "year": year,
                "citations": it.get("is-referenced-by-count", 0),
                "doi": it.get("DOI", "n/a"),
            })

        papers.sort(key=lambda p: p["citations"], reverse=True)
        return {
            "literature_findings": {
                "query": query,
                "n_found": len(papers),
                "top_papers": papers[:10],
                "source": "CrossRef API (live)",
            }
        }
    except Exception as e:
        return {
            "literature_findings": None,
            "errors": [f"research_node: literature search failed — {e}"],
        }


# ──────────────────────────────────────────────────────────────────
# Agent 2: Data & Technical Auditor
# ──────────────────────────────────────────────────────────────────
def audit_node(state: SwarmState) -> dict:
    df = state.get("dataset")
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return {
            "audit_findings": {
                "status": "no dataset supplied",
                "note": "This agent only reports on data actually provided — no dataset means no findings, not a fabricated one.",
            }
        }
    try:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        outlier_summary = []
        for col in numeric_cols:
            clean = df[col].dropna()
            if len(clean) > 4:
                q1, q3 = np.percentile(clean, [25, 75])
                iqr = q3 - q1
                lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
                n_outliers = int(((clean < lower) | (clean > upper)).sum())
                if n_outliers > 0:
                    outlier_summary.append({"column": col, "outlier_count": n_outliers})

        return {
            "audit_findings": {
                "status": "ok",
                "n_rows": int(df.shape[0]),
                "n_cols": int(df.shape[1]),
                "missing_cells": int(df.isna().sum().sum()),
                "duplicate_rows": int(df.duplicated().sum()),
                "numeric_columns_with_outliers": outlier_summary,
                "source": "pandas/NumPy IQR analysis (live computation on supplied data)",
            }
        }
    except Exception as e:
        return {
            "audit_findings": None,
            "errors": [f"audit_node: data audit failed — {e}"],
        }


# ──────────────────────────────────────────────────────────────────
# Agent 3: Synthesis & Strategy Architect
# ──────────────────────────────────────────────────────────────────
def synthesis_node(state: SwarmState) -> dict:
    lit = state.get("literature_findings")
    audit = state.get("audit_findings")
    api_key = os.environ.get("GEMINI_API_KEY")

    if not (GENAI_AVAILABLE and api_key):
        # Honest fallback — a structured merge of real findings, clearly
        # labeled as not LLM-synthesized. No canned prose pretending to be
        # AI reasoning (see portal.py's changelog on the "AI Intelligence
        # Daemon" that used to fake this).
        lines = [f"## Structured Findings for: {state['problem']}",
                 "_No LLM configured (set GEMINI_API_KEY) — showing a direct merge of the two agents' real findings, not an AI-synthesized plan._", ""]
        if lit:
            lines.append(f"### Literature ({lit['n_found']} papers found via CrossRef)")
            for p in lit["top_papers"][:5]:
                lines.append(f"- {p['title']} ({p['year']}, {p['citations']} citations)")
        else:
            lines.append("### Literature\nNo findings (search failed — see errors).")
        if audit and audit.get("status") == "ok":
            lines.append(f"\n### Data Audit\n{audit['n_rows']} rows, {audit['n_cols']} cols, "
                          f"{audit['missing_cells']} missing cells, {audit['duplicate_rows']} duplicate rows.")
            if audit["numeric_columns_with_outliers"]:
                lines.append("Outliers detected in: " + ", ".join(
                    f"{c['column']} ({c['outlier_count']})" for c in audit["numeric_columns_with_outliers"]))
        else:
            lines.append("\n### Data Audit\n" + (audit.get("note", "No findings.") if audit else "No findings (audit failed)."))
        return {"synthesis": "\n".join(lines)}

    # Real Gemini call, grounded strictly in the two agents' actual outputs.
    try:
        client = genai.Client(api_key=api_key)
        prompt = (
            f"You are a strategy synthesis agent. A user posed this challenge:\n{state['problem']}\n\n"
            f"Literature agent findings (real CrossRef results, do not invent papers beyond these):\n{lit}\n\n"
            f"Data audit agent findings (real computation on the user's actual dataset, do not invent statistics beyond these):\n{audit}\n\n"
            "Write a concise, actionable synthesis: what the literature suggests, what the data quality "
            "issues mean for any analysis, and 3-5 concrete next steps. Ground every claim in the findings "
            "above — do not cite facts that aren't in them."
        )
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        return {"synthesis": response.text}
    except Exception as e:
        return {
            "synthesis": None,
            "errors": [f"synthesis_node: Gemini call failed — {e}"],
        }


# ──────────────────────────────────────────────────────────────────
# Graph assembly — research and audit run in parallel, synthesis waits on both
# ──────────────────────────────────────────────────────────────────
def build_swarm_graph():
    graph = StateGraph(SwarmState)
    graph.add_node("research", research_node)
    graph.add_node("audit", audit_node)
    graph.add_node("synthesis", synthesis_node)

    # Real fan-out/fan-in: research (network call) and audit (local computation)
    # have no dependency on each other, so they run concurrently — synthesis
    # waits for both branches to complete before it sees either result.
    graph.add_edge(START, "research")
    graph.add_edge(START, "audit")
    graph.add_edge("research", "synthesis")
    graph.add_edge("audit", "synthesis")
    graph.add_edge("synthesis", END)

    return graph.compile()


def run_swarm(problem: str, dataset: Optional[pd.DataFrame] = None) -> SwarmState:
    """Entry point for Streamlit or any other caller."""
    app = build_swarm_graph()
    result = app.invoke({
        "problem": problem,
        "dataset": dataset,
        "literature_findings": None,
        "audit_findings": None,
        "synthesis": None,
        "errors": [],
    })
    return result
