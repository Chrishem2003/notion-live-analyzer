"""
tasks.py â€” Long-running jobs that used to block the Streamlit thread.

Each task reports real progress via `self.update_state(meta={...})` at each
genuine unit of work completed (a page of results fetched, a column
profiled) â€” not a fabricated percentage on a timer. `modules/task_client.py`
polls this same state to drive a progress bar in the UI.
"""

import time
import io
import numpy as np
import pandas as pd
import requests
from celery import Task
from celery.exceptions import SoftTimeLimitExceeded

from celery_app import celery_app

CROSSREF_PAGE_SIZE = 100  # CrossRef's practical max rows-per-request before latency degrades badly


class ProgressTask(Task):
    """Base task that always leaves a terminal state behind, even on failure,
    so the UI never polls a job id forever."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        self.update_state(
            state="FAILURE",
            meta={"error": str(exc), "current": 0, "total": 0, "stage": "failed"},
        )


@celery_app.task(
    bind=True,
    base=ProgressTask,
    name="tasks.harvest_literature_task",
    autoretry_for=(requests.exceptions.RequestException,),
    retry_backoff=5,          # 5s, 10s, 20s...
    retry_backoff_max=60,
    max_retries=4,
    retry_jitter=True,
)
def harvest_literature_task(self, query: str, target_count: int, contact_email: str, sort_by: str = "Relevance"):
    """
    Paginate CrossRef beyond the ~20-100 results a synchronous request can
    reasonably fetch. Reports progress after every page so a 500-paper
    harvest shows real, incrementing feedback instead of a spinner.
    """
    target_count = max(1, min(target_count, 2000))  # hard ceiling â€” this is a queue job, not a scraper
    headers = {"User-Agent": f"ChrishemPlatform/2.0 (mailto:{contact_email}})"}
    sort_params = {
        "Citation Count": ("is-referenced-by-count", "desc"),
        "Publication Date": ("published", "desc"),
        "Relevance": ("score", "desc"),
    }.get(sort_by, ("score", "desc"))

    records = []
    offset = 0

    try:
        while len(records) < target_count:
            page_size = min(CROSSREF_PAGE_SIZE, target_count - len(records))
            params = {
                "query": query,
                "rows": page_size,
                "offset": offset,
                "sort": sort_params[0],
                "order": sort_params[1],
            }
            resp = requests.get(
                "https://api.crossref.org/works",
                params=params,
                timeout=20,
                headers=headers,
            )
            resp.raise_for_status()
            items = resp.json().get("message", {}).get("items", [])
            if not items:
                break  # exhausted CrossRef's matches â€” stop early rather than loop forever

            for it in items:
                title_list = it.get("title")
                title = title_list[0] if title_list else "Untitled"
                authors = it.get("author", [])
                if authors:
                    fam = authors[0].get("family", "Unknown")
                    giv = authors[0].get("given", "")
                    first_author = f"{fam}}, {giv[0]}}." if giv else fam
                    if len(authors) > 1:
                        first_author += " et al."
                else:
                    first_author = "Unknown"

                year = None
                for key in ("published-print", "published-online", "issued"):
                    dp = it.get(key, {}).get("date-parts")
                    if dp and dp[0] and dp[0][0]:
                        year = dp[0][0]
                        break

                container = it.get("container-title")
                records.append({
                    "Title": title,
                    "First Author": first_author,
                    "Year": year if year else "n/a",
                    "Citations": it.get("is-referenced-by-count", 0),
                    "Journal": container[0] if container else "â€”",
                    "DOI": it.get("DOI", "n/a"),
                    "Type": it.get("type", "journal-article"),
                })

            offset += page_size

            self.update_state(
                state="PROGRESS",
                meta={
                    "current": len(records),
                    "total": target_count,
                    "stage": f"fetched {len(records)}} / {target_count}} records from CrossRef",
                },
            )

            # CrossRef's polite pool asks for a short gap between requests when
            # you're paginating in a tight loop, not a single one-off call.
            time.sleep(0.5)

    except SoftTimeLimitExceeded:
        # Return what we harvested rather than throwing it all away â€”
        # a partial 340-paper result is more useful than nothing.
        return {
            "records": records,
            "requested": target_count,
            "returned": len(records),
            "truncated": True,
            "reason": "soft time limit reached",
        }

    return {
        "records": records,
        "requested": target_count,
        "returned": len(records),
        "truncated": len(records) < target_count,
    }


@celery_app.task(
    bind=True,
    base=ProgressTask,
    name="tasks.bulk_dataset_audit_task",
)
def bulk_dataset_audit_task(self, csv_bytes: bytes, filename: str):
    """
    Real per-column data-quality audit for large datasets: dtype inference,
    missingness, duplicate rows, IQR-based outlier counts for numeric
    columns, and top-value distribution for categorical columns. Progress
    is reported per column, which is the real unit of work here (not a
    time-based fake progress bar).
    """
    df = pd.read_csv(io.BytesIO(csv_bytes))
    n_rows, n_cols = df.shape

    report = {
        "filename": filename,
        "n_rows": n_rows,
        "n_cols": n_cols,
        "duplicate_rows": int(df.duplicated().sum()),
        "columns": [],
    }

    for i, col in enumerate(df.columns):
        series = df[col]
        col_report = {
            "name": col,
            "dtype": str(series.dtype),
            "missing_count": int(series.isna().sum()),
            "missing_pct": round(float(series.isna().mean()) * 100, 2),
            "n_unique": int(series.nunique(dropna=True)),
        }

        if pd.api.types.is_numeric_dtype(series):
            clean = series.dropna()
            if len(clean) > 4:
                q1, q3 = np.percentile(clean, [25, 75])
                iqr = q3 - q1
                lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
                outliers = clean[(clean < lower) | (clean > upper)]
                col_report.update({
                    "mean": round(float(clean.mean()), 4),
                    "std": round(float(clean.std()), 4),
                    "min": round(float(clean.min()), 4),
                    "max": round(float(clean.max()), 4),
                    "outlier_count": int(len(outliers)),
                    "outlier_pct": round(len(outliers) / len(clean) * 100, 2),
                })
        else:
            top_values = series.value_counts(dropna=True).head(5)
            col_report["top_values"] = {str(k): int(v) for k, v in top_values.items()}

        report["columns"].append(col_report)

        self.update_state(
            state="PROGRESS",
            meta={
                "current": i + 1,
                "total": n_cols,
                "stage": f"profiled column {i + 1}}/{n_cols}}: {col}}",
            },
        )

    return report


@celery_app.task(
    bind=True,
    base=ProgressTask,
    name="tasks.run_swarm_task",
)
def run_swarm_task(self, problem: str, dataset_records: list = None):
    """
    Celery wrapper around agents.run_swarm(). Celery messages are JSON, and
    a pandas DataFrame isn't JSON-serializable, so the caller passes
    `dataset_records` as a list of row-dicts (df.to_dict("records")) and
    this reconstructs the DataFrame worker-side. This is what turns the
    agent swarm from "call it inline and block" into "submit and poll" â€”
    the same pattern task_client.py already uses for the other two tasks.
    """
    from agents import build_swarm_graph  # imported here, not at module load,
                                            # so a worker without langgraph
                                            # installed can still run the
                                            # other queues without crashing on import.

    df = pd.DataFrame(dataset_records) if dataset_records else None
    graph = build_swarm_graph()

    self.update_state(state="PROGRESS", meta={"current": 0, "total": 3, "stage": "dispatching research + audit agents"})

    final_state = {}
    completed = 0
    for step in graph.stream({
        "problem": problem,
        "dataset": df,
        "literature_findings": None,
        "audit_findings": None,
        "synthesis": None,
        "errors": [],
    }):
        node_name, node_output = next(iter(step.items()))
        final_state.update(node_output)
        completed += 1
        self.update_state(
            state="PROGRESS",
            meta={"current": completed, "total": 3, "stage": f"{node_name}} agent complete"},
        )

    # Strip the DataFrame back out before returning â€” Celery results are
    # JSON too, and we already have its findings in audit_findings.
    final_state.pop("dataset", None)
    return final_state
