"""Runtime memory helpers for hosted deployments.

Streamlit Community Cloud gives a container ~1 GB of RAM that is shared by every
browser session hitting the same process, so an OOM kill is usually caused by
retained objects rather than by one expensive computation. The helpers here
target the three retention sources in this app: oversized uploads, wide float64
frames, and unbounded session/history lists.
"""
from __future__ import annotations

import gc
import os
import sys
from typing import Any, Iterable, List, Optional, Tuple

import pandas as pd

# ─── Limits ───────────────────────────────────────────────────────────
MAX_UPLOAD_MB = 50           # mirrors .streamlit/config.toml server.maxUploadSize
MAX_ROWS_IN_MEMORY = 200_000  # rows kept from a single upload
CSV_CHUNK_ROWS = 50_000      # rows per chunk when streaming a CSV
CACHE_MAX_ENTRIES = 8        # per-cache entry cap; keeps st.cache_data bounded
HISTORY_MAX_ENTRIES = 100    # cap for append-only session_state history lists
AUTO_REPORT_MAX_ROWS = 5_000  # above this, profiling reports must be requested explicitly


def memory_usage_mb() -> float:
    """Resident set size of this process in MB (0.0 if it cannot be read)."""
    try:
        import psutil

        return psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
    except Exception:
        pass
    try:
        # Current RSS on Linux (which is what hosted containers run).
        with open("/proc/self/statm", "r") as handle:
            pages = int(handle.read().split()[1])
        return pages * os.sysconf("SC_PAGE_SIZE") / 1024 / 1024
    except Exception:
        pass
    try:
        import resource

        # Peak RSS, so this over-reports after a spike; last resort only.
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # Linux reports kilobytes, macOS reports bytes.
        divisor = 1024 * 1024 if sys.platform == "darwin" else 1024
        return rss / divisor
    except Exception:
        return 0.0


def dataframe_memory_mb(df: Optional[pd.DataFrame]) -> float:
    """Deep memory footprint of a DataFrame in MB."""
    if df is None or not isinstance(df, pd.DataFrame):
        return 0.0
    return float(df.memory_usage(deep=True).sum()) / 1024 / 1024


def release() -> float:
    """Force a collection after a heavy operation. Returns MB reclaimed."""
    before = memory_usage_mb()
    gc.collect()
    return max(0.0, before - memory_usage_mb())


def shrink_dataframe(df: pd.DataFrame, category_threshold: float = 0.0) -> pd.DataFrame:
    """Downcast numeric columns to the narrowest dtype that holds their values.

    pandas defaults every integer to int64 and every float to float64, so a
    parsed CSV is routinely 2-4x larger than it needs to be.

    ``category_threshold`` optionally converts text columns whose unique-value
    ratio is at or below it into categories. It is disabled by default: the
    analysis modules branch on text dtypes (see ``modules.pandas_compat``) and
    call ``pd.to_numeric`` on them, neither of which handles CategoricalDtype.
    """
    if df is None or df.empty:
        return df

    out = df.copy()
    for col in out.columns:
        series = out[col]
        if pd.api.types.is_integer_dtype(series):
            out[col] = pd.to_numeric(series, downcast="integer")
        elif pd.api.types.is_float_dtype(series):
            out[col] = pd.to_numeric(series, downcast="float")
        elif pd.api.types.is_bool_dtype(series) or isinstance(series.dtype, pd.CategoricalDtype):
            continue
        elif category_threshold > 0:
            non_null = series.dropna()
            if len(non_null) and non_null.nunique() / len(non_null) <= category_threshold:
                out[col] = series.astype("category")
    return out


def check_upload_size(uploaded_file, max_mb: Optional[float] = None) -> Tuple[bool, str]:
    """Validate an uploaded file against the size budget.

    Returns ``(ok, message)``; ``message`` is empty when the file is acceptable.
    """
    max_mb = MAX_UPLOAD_MB if max_mb is None else max_mb
    if uploaded_file is None:
        return False, "No file provided."

    size = getattr(uploaded_file, "size", None)
    if size is None:
        return True, ""

    size_mb = size / 1024 / 1024
    if size_mb > max_mb:
        return False, (
            f"File is {size_mb:.1f} MB, above the {max_mb:.0f} MB limit. "
            "Split it or filter rows before uploading."
        )
    return True, ""


def read_csv_chunked(
    file_obj,
    max_rows: Optional[int] = None,
    chunk_rows: Optional[int] = None,
    **read_kwargs,
) -> Tuple[pd.DataFrame, bool]:
    """Read a CSV in chunks, stopping at ``max_rows``.

    Returns ``(df, truncated)``. Chunks are shrunk before concatenation so peak
    memory stays close to the final frame size instead of 2-3x it.
    """
    max_rows = MAX_ROWS_IN_MEMORY if max_rows is None else max_rows
    chunk_rows = CSV_CHUNK_ROWS if chunk_rows is None else chunk_rows

    chunks: List[pd.DataFrame] = []
    rows = 0
    truncated = False

    reader = pd.read_csv(file_obj, chunksize=chunk_rows, **read_kwargs)
    for chunk in reader:
        remaining = max_rows - rows
        if remaining <= 0:
            truncated = True
            break
        if len(chunk) > remaining:
            chunk = chunk.iloc[:remaining]
            truncated = True
        rows += len(chunk)
        chunks.append(shrink_dataframe(chunk))
        if truncated:
            break

    if not chunks:
        return pd.DataFrame(), False

    df = pd.concat(chunks, ignore_index=True) if len(chunks) > 1 else chunks[0]
    del chunks
    gc.collect()
    return df, truncated


def trim_history(items: Iterable[Any], max_entries: int = HISTORY_MAX_ENTRIES) -> List[Any]:
    """Keep only the most recent ``max_entries`` items of an append-only list."""
    items = list(items)
    if max_entries <= 0:
        return []
    return items[-max_entries:]


def resolve_app_url() -> Optional[str]:
    """Public URL of this deployment, or None when it cannot be determined.

    Self-pinging ``http://localhost:8501`` keeps nothing awake on a hosted
    platform — it only burns a thread — so callers must handle None by skipping
    the server-side keep-alive.
    """
    for var in ("APP_URL", "RENDER_EXTERNAL_URL", "STREAMLIT_APP_URL", "SPACE_HOST"):
        value = os.environ.get(var)
        if value:
            value = value.strip()
            if not value.startswith("http"):
                value = f"https://{value}"
            return value.rstrip("/")
    return None
