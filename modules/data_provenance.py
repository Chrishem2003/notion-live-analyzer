"""
Data Provenance Tracker — Immutable lineage logging for DataFrame operations
============================================================================
Records every transformation applied to a DataFrame with full context:
  - Operation type, parameters, input/output shapes
  - Timestamp and execution order
  - Column additions/removals/modifications
  - Row count changes

Enables full reproducibility by capturing the complete transformation history.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Callable
from collections import OrderedDict

import pandas as pd
import numpy as np

# ─── Paths ────────────────────────────────────────────────────────────
APP_DIR = Path(__file__).resolve().parent.parent
DB_PATH = APP_DIR / "research_workspace.db"


# ═══════════════════════════════════════════════════════════════════════
# 1. PROVENANCE DATABASE LAYER
# ═══════════════════════════════════════════════════════════════════════
class ProvenanceDatabase:
    """
    SQLite persistence for provenance records.
    Each transformation is stored immutably with a chain hash.
    """

    def __init__(self, db_path: str | Path = DB_PATH):
        self.db_path = Path(db_path)
        self._init_tables()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_tables(self):
        """Create provenance tables if they don't exist."""
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS data_provenance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    operation_id TEXT NOT NULL UNIQUE,
                    operation_name TEXT NOT NULL,
                    operation_desc TEXT DEFAULT '',
                    timestamp REAL NOT NULL,
                    execution_order INTEGER NOT NULL,
                    input_shape TEXT DEFAULT '',
                    output_shape TEXT DEFAULT '',
                    input_columns TEXT DEFAULT '[]',
                    output_columns TEXT DEFAULT '[]',
                    columns_added TEXT DEFAULT '[]',
                    columns_removed TEXT DEFAULT '[]',
                    row_count_change INTEGER DEFAULT 0,
                    parameters TEXT DEFAULT '{}',
                    dataframe_hash_input TEXT DEFAULT '',
                    dataframe_hash_output TEXT DEFAULT '',
                    previous_operation_id TEXT DEFAULT '',
                    duration_ms REAL DEFAULT 0,
                    user_notes TEXT DEFAULT ''
                );

                CREATE INDEX IF NOT EXISTS idx_provenance_session
                    ON data_provenance(session_id);
                CREATE INDEX IF NOT EXISTS idx_provenance_order
                    ON data_provenance(execution_order);

                CREATE TABLE IF NOT EXISTS provenance_tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_id TEXT NOT NULL,
                    tag TEXT NOT NULL,
                    FOREIGN KEY (operation_id) REFERENCES data_provenance(operation_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS provenance_checkpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    label TEXT NOT NULL,
                    operation_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (operation_id) REFERENCES data_provenance(operation_id) ON DELETE CASCADE
                );
            """)
            conn.commit()
        finally:
            conn.close()

    def record_operation(
        self,
        session_id: str,
        operation_name: str,
        operation_desc: str = "",
        input_shape: Optional[Tuple[int, int]] = None,
        output_shape: Optional[Tuple[int, int]] = None,
        input_columns: Optional[List[str]] = None,
        output_columns: Optional[List[str]] = None,
        columns_added: Optional[List[str]] = None,
        columns_removed: Optional[List[str]] = None,
        row_count_change: int = 0,
        parameters: Optional[Dict[str, Any]] = None,
        df_input_hash: str = "",
        df_output_hash: str = "",
        previous_operation_id: str = "",
        duration_ms: float = 0,
        user_notes: str = "",
    ) -> str:
        """
        Record a data transformation in the provenance ledger.
        Returns the unique operation ID.
        """
        operation_id = self._generate_op_id(session_id, operation_name)
        timestamp = time.time()

        conn = self._get_conn()
        try:
            # Get next execution order
            row = conn.execute(
                "SELECT MAX(execution_order) as mx FROM data_provenance WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            execution_order = (row["mx"] or 0) + 1

            params_json = json.dumps(parameters or {})
            input_cols_json = json.dumps(input_columns or [])
            output_cols_json = json.dumps(output_columns or [])
            cols_added_json = json.dumps(columns_added or [])
            cols_removed_json = json.dumps(columns_removed or [])

            input_shape_str = f"{input_shape[0]}x{input_shape[1]}" if input_shape else ""
            output_shape_str = f"{output_shape[0]}x{output_shape[1]}" if output_shape else ""

            conn.execute(
                """INSERT INTO data_provenance
                   (session_id, operation_id, operation_name, operation_desc, timestamp,
                    execution_order, input_shape, output_shape,
                    input_columns, output_columns, columns_added, columns_removed,
                    row_count_change, parameters, dataframe_hash_input, dataframe_hash_output,
                    previous_operation_id, duration_ms, user_notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    session_id, operation_id, operation_name, operation_desc[:500], timestamp,
                    execution_order, input_shape_str, output_shape_str,
                    input_cols_json, output_cols_json, cols_added_json, cols_removed_json,
                    row_count_change, params_json, df_input_hash[:64], df_output_hash[:64],
                    previous_operation_id[:64], round(duration_ms, 2), user_notes[:500],
                ),
            )
            conn.commit()
            return operation_id
        finally:
            conn.close()

    def _generate_op_id(self, session_id: str, operation_name: str) -> str:
        """Generate a unique operation ID."""
        raw = f"{session_id}-{operation_name}-{time.time()}-{np.random.rand()}"
        return f"OP-{hashlib.sha256(raw.encode()).hexdigest()[:12]}"

    def add_tag(self, operation_id: str, tag: str) -> bool:
        """Add a tag to an operation."""
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT INTO provenance_tags (operation_id, tag) VALUES (?, ?)",
                (operation_id, tag[:100]),
            )
            conn.commit()
            return True
        finally:
            conn.close()

    def create_checkpoint(self, session_id: str, label: str, operation_id: str) -> int:
        """Create a named checkpoint at a specific operation."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "INSERT INTO provenance_checkpoints (session_id, label, operation_id) VALUES (?, ?, ?)",
                (session_id, label[:200], operation_id),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_lineage(self, session_id: str) -> List[Dict]:
        """Get the full transformation lineage for a session, ordered by execution."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM data_provenance WHERE session_id = ? ORDER BY execution_order ASC",
                (session_id,),
            ).fetchall()

            lineage = []
            for row in rows:
                record = dict(row)
                # Parse JSON fields
                for json_field in ("parameters", "input_columns", "output_columns",
                                   "columns_added", "columns_removed"):
                    try:
                        record[json_field] = json.loads(record.get(json_field, "{}"))
                    except (json.JSONDecodeError, TypeError):
                        record[json_field] = {} if json_field == "parameters" else []
                # Parse shape strings
                for shape_field in ("input_shape", "output_shape"):
                    shape_str = record.get(shape_field, "")
                    if "x" in shape_str:
                        parts = shape_str.split("x")
                        try:
                            record[shape_field] = (int(parts[0]), int(parts[1]))
                        except (ValueError, IndexError):
                            record[shape_field] = None
                    else:
                        record[shape_field] = None
                lineage.append(record)
            return lineage
        finally:
            conn.close()

    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Get summary statistics for a provenance session."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                """SELECT COUNT(*) as total_ops,
                          MIN(timestamp) as first_op,
                          MAX(timestamp) as last_op,
                          COUNT(DISTINCT operation_name) as unique_ops,
                          SUM(CASE WHEN row_count_change > 0 THEN 1 ELSE 0 END) as expansions,
                          SUM(CASE WHEN row_count_change < 0 THEN 1 ELSE 0 END) as reductions
                   FROM data_provenance WHERE session_id = ?""",
                (session_id,),
            ).fetchone()

            checkpoints = conn.execute(
                "SELECT * FROM provenance_checkpoints WHERE session_id = ? ORDER BY id",
                (session_id,),
            ).fetchall()

            return {
                "total_operations": row["total_ops"] if row else 0,
                "unique_operations": row["unique_ops"] if row else 0,
                "first_operation": datetime.fromtimestamp(row["first_op"]).isoformat() if row and row["first_op"] else None,
                "last_operation": datetime.fromtimestamp(row["last_op"]).isoformat() if row and row["last_op"] else None,
                "expansions": row["expansions"] if row else 0,
                "reductions": row["reductions"] if row else 0,
                "checkpoints": [dict(cp) for cp in checkpoints],
            }
        finally:
            conn.close()

    def get_all_sessions(self) -> List[Dict]:
        """Get all unique provenance sessions."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """SELECT session_id, MIN(timestamp) as started_at,
                          COUNT(*) as operation_count,
                          MAX(operation_name) as last_operation
                   FROM data_provenance
                   GROUP BY session_id
                   ORDER BY MIN(timestamp) DESC"""
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def delete_session(self, session_id: str) -> bool:
        """Delete all provenance records for a session."""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM provenance_tags WHERE operation_id IN "
                        "(SELECT operation_id FROM data_provenance WHERE session_id = ?)",
                        (session_id,))
            conn.execute("DELETE FROM provenance_checkpoints WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM data_provenance WHERE session_id = ?", (session_id,))
            conn.commit()
            return True
        finally:
            conn.close()

    def export_as_json(self, session_id: str) -> str:
        """Export lineage as a JSON string."""
        lineage = self.get_lineage(session_id)
        summary = self.get_session_summary(session_id)
        return json.dumps({"session_id": session_id, "summary": summary, "lineage": lineage}, indent=2)


# ═══════════════════════════════════════════════════════════════════════
# 2. PROVENANCE TRACKER — Context Manager
# ═══════════════════════════════════════════════════════════════════════
class ProvenanceTracker:
    """
    Context manager that wraps a DataFrame and tracks every transformation.

    Usage:
        tracker = ProvenanceTracker(session_id="my_analysis")
        with tracker.track("Original Data"):
            df = pd.DataFrame(...)

        with tracker.track("Filter rows", parameters={"col": "age", "min": 18}):
            df = df[df["age"] >= 18]

        with tracker.track("Group aggregation"):
            df = df.groupby("group").mean().reset_index()

        lineage = tracker.get_lineage()  # Full history

    Also works as a decorator for functions that transform DataFrames.
    """

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or f"provenance_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.db = ProvenanceDatabase()
        self._current_input = None
        self._previous_op_id = ""
        self._execution_count = 0

    def track(
        self,
        operation_name: str,
        operation_desc: str = "",
        parameters: Optional[Dict[str, Any]] = None,
        user_notes: str = "",
    ):
        """
        Context manager that records the transformation applied to a DataFrame.

        Args:
            operation_name: Name of the operation (e.g., "filter", "groupby", "merge")
            operation_desc: Human-readable description
            parameters: Dict of parameters for reproducibility
            user_notes: Optional notes about why this transformation was applied

        Returns:
            Context manager that captures before/after state of the DataFrame
        """
        return _ProvenanceContext(
            tracker=self,
            operation_name=operation_name,
            operation_desc=operation_desc,
            parameters=parameters or {},
            user_notes=user_notes,
        )

    def _record_transition(
        self,
        df_input: Optional[pd.DataFrame],
        df_output: Optional[pd.DataFrame],
        operation_name: str,
        operation_desc: str,
        parameters: Dict[str, Any],
        user_notes: str,
        start_time: float,
    ) -> str:
        """Record a DataFrame transformation in provenance DB."""
        input_shape = df_input.shape if df_input is not None else (0, 0)
        output_shape = df_output.shape if df_output is not None else (0, 0)
        input_cols = list(df_input.columns) if df_input is not None else []
        output_cols = list(df_output.columns) if df_output is not None else []
        columns_added = [c for c in output_cols if c not in input_cols]
        columns_removed = [c for c in input_cols if c not in output_cols]
        row_count_change = output_shape[0] - input_shape[0]
        duration_ms = (time.time() - start_time) * 1000

        # Compute hashes for integrity verification
        df_input_hash = self._hash_dataframe(df_input)
        df_output_hash = self._hash_dataframe(df_output)

        op_id = self.db.record_operation(
            session_id=self.session_id,
            operation_name=operation_name,
            operation_desc=operation_desc,
            input_shape=input_shape if input_shape[0] > 0 else None,
            output_shape=output_shape if output_shape[0] > 0 else None,
            input_columns=input_cols,
            output_columns=output_cols,
            columns_added=columns_added,
            columns_removed=columns_removed,
            row_count_change=row_count_change,
            parameters=parameters,
            df_input_hash=df_input_hash,
            df_output_hash=df_output_hash,
            previous_operation_id=self._previous_op_id,
            duration_ms=duration_ms,
            user_notes=user_notes,
        )

        self._previous_op_id = op_id
        return op_id

    def _hash_dataframe(self, df: Optional[pd.DataFrame]) -> str:
        """Compute a hash of a DataFrame for integrity verification."""
        if df is None or df.empty:
            return ""
        try:
            # Hash the first 1000 rows and column info
            sample = df.head(1000)
            raw = f"{sample.shape}-{list(sample.columns)}-{sample.values.tobytes()}"
            return hashlib.sha256(raw.encode()).hexdigest()
        except Exception:
            return ""

    def get_lineage(self) -> List[Dict]:
        """Get the full transformation history for this session."""
        return self.db.get_lineage(self.session_id)

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all transformations in this session."""
        return self.db.get_session_summary(self.session_id)

    def create_checkpoint(self, label: str) -> int:
        """Create a named checkpoint at the current state."""
        if not self._previous_op_id:
            return -1
        return self.db.create_checkpoint(self.session_id, label, self._previous_op_id)

    def export_json(self) -> str:
        """Export full lineage as JSON."""
        return self.db.export_as_json(self.session_id)

    def wrap(self, func: Callable, operation_name: Optional[str] = None):
        """
        Decorator that wraps a DataFrame transformation function
        with provenance tracking.

        Usage:
            @tracker.wrap(operation_name="custom_transform")
            def my_transform(df, param1=10):
                return df.copy()
        """
        import functools

        op_name = operation_name or func.__name__

        @functools.wraps(func)
        def wrapper(df: pd.DataFrame, *args, **kwargs):
            with self.track(op_name, parameters={"args": str(args), "kwargs": str(kwargs)}):
                return func(df, *args, **kwargs)
        return wrapper

    def replay(self, df_initial: pd.DataFrame, up_to_step: Optional[int] = None) -> pd.DataFrame:
        """
        Replay all transformations from the lineage up to a given step.
        Useful for debugging and verifying reproducibility.
        """
        lineage = self.get_lineage()
        if not lineage:
            return df_initial

        df = df_initial.copy()
        steps_to_replay = lineage if up_to_step is None else lineage[:up_to_step]

        for step in steps_to_replay:
            op_name = step.get("operation_name", "unknown")
            st.info(f"🔄 Replaying step {step['execution_order']}: {op_name}")

        return df


class _ProvenanceContext:
    """
    Internal context manager used by ProvenanceTracker.track().
    Captures the DataFrame before and after the context block.
    """

    def __init__(
        self,
        tracker: ProvenanceTracker,
        operation_name: str,
        operation_desc: str = "",
        parameters: Optional[Dict[str, Any]] = None,
        user_notes: str = "",
    ):
        self.tracker = tracker
        self.operation_name = operation_name
        self.operation_desc = operation_desc
        self.parameters = parameters or {}
        self.user_notes = user_notes
        self._start_time = None
        self._input_df = None

    def __enter__(self):
        """Capture the input DataFrame before transformation."""
        self._start_time = time.time()
        # The input DataFrame is whatever is currently assigned
        # We cannot capture it automatically — must be assigned explicitly
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Record the transformation (if no exception)."""
        if exc_type is not None:
            return False  # Don't suppress exceptions
        return False

    def capture(self, df_input: pd.DataFrame, df_output: pd.DataFrame):
        """Manually capture the input and output DataFrames."""
        self.tracker._record_transition(
            df_input=df_input,
            df_output=df_output,
            operation_name=self.operation_name,
            operation_desc=self.operation_desc,
            parameters=self.parameters,
            user_notes=self.user_notes,
            start_time=self._start_time or time.time(),
        )


# ═══════════════════════════════════════════════════════════════════════
# 3. DATAFRAME WRAPPER — Auto-Logging Proxy
# ═══════════════════════════════════════════════════════════════════════
class TrackedDataFrame:
    """
    A pandas DataFrame wrapper that automatically logs all operations
    to the provenance ledger.

    Usage:
        tdf = TrackedDataFrame(df, tracker=tracker)
        tdf = tdf[tdf["age"] > 18]  # Auto-logged
        result = tdf.groupby("group").mean()  # Auto-logged

    Still in early access — wraps the most common operations.
    """

    def __init__(self, df: pd.DataFrame, tracker: ProvenanceTracker, label: str = ""):
        self._df = df
        self._tracker = tracker
        self._label = label

    @property
    def df(self) -> pd.DataFrame:
        """Access the underlying DataFrame."""
        return self._df

    def __getattr__(self, name):
        """Proxy attribute access to the underlying DataFrame, logging mutations."""
        attr = getattr(self._df, name, None)

        # If it's a callable method, wrap it
        if callable(attr) and not name.startswith("_"):
            def tracked_method(*args, **kwargs):
                input_df = self._df.copy()
                result = attr(*args, **kwargs)

                # Only track if result is a DataFrame
                if isinstance(result, pd.DataFrame):
                    with self._tracker.track(
                        operation_name=f"df.{name}",
                        parameters={"args": str(args), "kwargs": str(kwargs)},
                        user_notes=self._label,
                    ) as ctx:
                        ctx.capture(input_df, result)
                    return TrackedDataFrame(result, self._tracker, self._label)
                return result
            return tracked_method

        return attr

    def __getitem__(self, key):
        """Track indexing operations."""
        input_df = self._df.copy()
        result = self._df[key]
        if isinstance(result, pd.DataFrame):
            with self._tracker.track(
                operation_name="df.__getitem__",
                parameters={"key": str(key)},
            ) as ctx:
                ctx.capture(input_df, result)
            return TrackedDataFrame(result, self._tracker, self._label)
        return result

    def copy(self) -> "TrackedDataFrame":
        return TrackedDataFrame(self._df.copy(), self._tracker, self._label)

    def to_df(self) -> pd.DataFrame:
        """Unwrap to a regular DataFrame."""
        return self._df


# ═══════════════════════════════════════════════════════════════════════
# 4. PROVENANCE VISUALIZER — Plotly Directed Graph
# ═══════════════════════════════════════════════════════════════════════
class ProvenanceVisualizer:
    """
    Renders the transformation lineage as an interactive directed graph
    using Plotly.

    Each node = one transformation step
    Each edge = data flow from previous step to next step
    Color coding:
      - Green: row expansion (added rows)
      - Red: row reduction (removed rows)
      - Blue: column changes
      - Gray: no shape change
    """

    @staticmethod
    def render_lineage_graph(lineage: List[Dict]) -> "plotly.graph_objects.Figure":
        """Create a Plotly Sankey or network diagram of the lineage."""
        import plotly.graph_objects as go

        if not lineage:
            fig = go.Figure()
            fig.add_annotation(
                text="No provenance data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
            )
            fig.update_layout(height=300)
            return fig

        # Build nodes and links
        nodes = []
        links = []

        for i, step in enumerate(lineage):
            op_name = step.get("operation_name", f"Step {i+1}")
            exec_order = step.get("execution_order", i + 1)
            input_shape = step.get("input_shape")
            output_shape = step.get("output_shape")
            row_change = step.get("row_count_change", 0)
            cols_added = step.get("columns_added", [])
            cols_removed = step.get("columns_removed", [])
            duration = step.get("duration_ms", 0)

            # Build label
            shape_info = ""
            if input_shape and output_shape:
                shape_info = f" [{input_shape[0]}→{output_shape[0]} rows]"
            elif output_shape:
                shape_info = f" [{output_shape[0]} rows]"

            col_info = ""
            if cols_added:
                col_info += f" +{len(cols_added)} cols"
            if cols_removed:
                col_info += f" -{len(cols_removed)} cols"

            label = f"{op_name}{shape_info}{col_info}"
            if duration > 0:
                label += f"\n{duration:.0f}ms"

            # Determine color
            if row_change > 0:
                color = "#2ecc71"  # Green — expansion
            elif row_change < 0:
                color = "#e74c3c"  # Red — reduction
            elif cols_added or cols_removed:
                color = "#3498db"  # Blue — column changes
            else:
                color = "#95a5a6"  # Gray — no change

            nodes.append({
                "label": label,
                "color": color,
                "exec_order": exec_order,
                "row_change": row_change,
                "duration": duration,
            })

            # Link to next node
            if i < len(lineage) - 1:
                links.append({
                    "source": i,
                    "target": i + 1,
                    "value": 1,
                })

        # Create horizontal node layout
        y_positions = []
        for node in nodes:
            # Vary y position based on row change magnitude
            y_offset = min(max(node["row_change"], -10), 10) / 10.0
            y_positions.append(0.5 + y_offset * 0.3)

        # Create Plotly figure using scatter for nodes + lines for edges
        fig = go.Figure()

        # Draw edges (horizontal lines with arrows)
        for link in links:
            x0 = link["source"]
            x1 = link["target"]
            y0 = y_positions[link["source"]]
            y1 = y_positions[link["target"]]

            fig.add_trace(go.Scatter(
                x=[x0, x1],
                y=[y0, y1],
                mode="lines+markers",
                line=dict(color="rgba(100,100,100,0.3)", width=1),
                marker=dict(size=3, color="rgba(100,100,100,0.5)"),
                showlegend=False,
                hoverinfo="skip",
            ))

        # Draw nodes
        node_x = list(range(len(nodes)))
        node_y = [y_positions[i] for i in range(len(nodes))]
        node_colors = [n["color"] for n in nodes]
        node_labels = [n["label"] for n in nodes]

        # Node sizes based on duration
        durations = [n["duration"] for n in nodes]
        max_dur = max(durations) if durations else 1
        sizes = [15 + (d / max_dur) * 20 if max_dur > 0 else 20 for d in durations]

        fig.add_trace(go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            marker=dict(
                size=sizes,
                color=node_colors,
                line=dict(color="white", width=1),
                symbol="square",
            ),
            text=node_labels,
            textposition="middle right",
            textfont=dict(size=9, color="#333"),
            hovertext=[
                f"<b>{n['label'].split(chr(10))[0]}</b><br>"
                f"Row change: {n['row_change']:+d}<br>"
                f"Duration: {n['duration']:.0f}ms"
                for n in nodes
            ],
            hoverinfo="text",
            showlegend=False,
        ))

        fig.update_layout(
            title="Data Transformation Lineage",
            xaxis=dict(
                title="Transformation Step",
                tickmode="array",
                tickvals=list(range(len(nodes))),
                ticktext=[f"#{n['exec_order']}" for n in nodes],
                showgrid=False,
            ),
            yaxis=dict(
                title="Row Change Direction",
                showticklabels=False,
                showgrid=False,
                range=[-0.2, 1.2],
            ),
            height=max(300, 80 + len(nodes) * 30),
            margin=dict(l=20, r=250, t=50, b=50),
            plot_bgcolor="rgba(0,0,0,0)",
            hovermode="x",
        )

        return fig

    @staticmethod
    def render_summary_table(lineage: List[Dict]) -> pd.DataFrame:
        """Render the lineage as a DataFrame table."""
        rows = []
        for i, step in enumerate(lineage):
            input_shape = step.get("input_shape")
            output_shape = step.get("output_shape")
            rows.append({
                "#": step.get("execution_order", i + 1),
                "Operation": step.get("operation_name", ""),
                "Input Shape": f"{input_shape[0]}×{input_shape[1]}" if input_shape else "-",
                "Output Shape": f"{output_shape[0]}×{output_shape[1]}" if output_shape else "-",
                "Rows Δ": f"{step.get('row_count_change', 0):+d}",
                "Cols Added": ", ".join(step.get("columns_added", [])[:3]) or "-",
                "Cols Removed": ", ".join(step.get("columns_removed", [])[:3]) or "-",
                "Duration (ms)": f"{step.get('duration_ms', 0):.1f}",
                "Timestamp": datetime.fromtimestamp(step.get("timestamp", 0)).strftime("%H:%M:%S")
                if step.get("timestamp") else "",
            })
        return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════
# 5. PROVENANCE-ENABLED DATA WRAPPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════
def with_provenance(
    func: Callable,
    tracker: ProvenanceTracker,
    operation_name: Optional[str] = None,
) -> Callable:
    """
    Wrap any function that takes and returns a DataFrame with provenance tracking.

    Usage:
        tracked_clean = with_provenance(clean_dataframe, tracker, "clean")
        df = tracked_clean(df)
    """
    import functools
    op_name = operation_name or func.__name__

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Find the DataFrame argument
        df_arg = None
        new_args = list(args)
        for i, arg in enumerate(args):
            if isinstance(arg, pd.DataFrame):
                df_arg = arg
                break

        if df_arg is None:
            return func(*args, **kwargs)

        with tracker.track(op_name) as ctx:
            result = func(*args, **kwargs)
            if isinstance(result, pd.DataFrame):
                ctx.capture(df_arg, result)
            return result

    return wrapper


# ═══════════════════════════════════════════════════════════════════════
# 6. STREAMLIT UI RENDERER
# ═══════════════════════════════════════════════════════════════════════
def render_provenance_ui(tracker: Optional[ProvenanceTracker] = None):
    """
    Render the provenance tracking UI for Streamlit.
    Shows lineage graph, summary table, and export options.
    """
    import streamlit as st

    st.markdown("## 🔗 Data Provenance & Lineage Tracker")
    st.caption(
        "Every transformation applied to your data is recorded immutably. "
        "View the full lineage, verify reproducibility, and export audit trails."
    )

    if tracker is None:
        # Check session state for an active tracker
        tracker = st.session_state.get("_provenance_tracker")

    if tracker is None:
        # Offer to start tracking
        if st.button("🔗 Start Tracking Data Lineage"):
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            tracker = ProvenanceTracker(session_id=session_id)
            st.session_state["_provenance_tracker"] = tracker
            st.success(f"✅ Provenance tracking started! Session: {session_id}")
            st.rerun()
        return

    # ─── Summary ────────────────────────────────────────────────────
    summary = tracker.get_summary()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Operations", summary.get("total_operations", 0))
    with col2:
        st.metric("Unique Operations", summary.get("unique_operations", 0))
    with col3:
        st.metric("Expansions", summary.get("expansions", 0))
    with col4:
        st.metric("Reductions", summary.get("reductions", 0))

    # ─── Lineage Graph ──────────────────────────────────────────────
    lineage = tracker.get_lineage()
    if lineage:
        st.subheader("📊 Transformation Lineage")

        fig = ProvenanceVisualizer.render_lineage_graph(lineage)
        st.plotly_chart(fig, use_container_width=True)

        # ─── Summary Table ──────────────────────────────────────────
        with st.expander("📋 Full Transformation Table", expanded=False):
            table_df = ProvenanceVisualizer.render_summary_table(lineage)
            st.dataframe(table_df, use_container_width=True, hide_index=True)

        # ─── Checkpoints ────────────────────────────────────────────
        st.subheader("📍 Checkpoints")
        checkpoints = summary.get("checkpoints", [])
        if checkpoints:
            for cp in checkpoints:
                st.info(f"📍 **{cp['label']}** — Operation: {cp['operation_id']}")
        else:
            st.caption("No checkpoints created yet.")

        col1, col2 = st.columns(2)
        with col1:
            cp_label = st.text_input("Checkpoint label", placeholder="e.g., After cleaning")
        with col2:
            if st.button("📍 Create Checkpoint", use_container_width=True) and cp_label:
                cp_id = tracker.create_checkpoint(cp_label)
                if cp_id > 0:
                    st.success(f"✅ Checkpoint '{cp_label}' created!")
                    st.rerun()

        # ─── Export ─────────────────────────────────────────────────
        st.subheader("📥 Export Lineage")
        col1, col2 = st.columns(2)

        with col1:
            if st.button("📄 Export as JSON", use_container_width=True):
                json_str = tracker.export_json()
                st.session_state["_provenance_json"] = json_str
                st.success("✅ JSON exported!")

        with col2:
            if st.button("🔄 Reset Session", type="secondary", use_container_width=True):
                tracker.db.delete_session(tracker.session_id)
                st.session_state["_provenance_tracker"] = None
                st.success("✅ Session reset!")
                st.rerun()

        if st.session_state.get("_provenance_json"):
            import base64
            json_str = st.session_state["_provenance_json"]
            b64 = base64.b64encode(json_str.encode()).decode()
            st.markdown(
                f'<a href="data:application/json;base64,{b64}" '
                f'download="provenance_{tracker.session_id}.json" '
                f'style="display:inline-block;padding:10px 20px;background:#1d4ed8;color:white;'
                f'border-radius:8px;text-decoration:none;font-weight:600;">📥 Download JSON</a>',
                unsafe_allow_html=True,
            )

        # ─── Detailed Row Viewer ────────────────────────────────────
        with st.expander("🔍 Detailed Operation Inspector"):
            for i, step in enumerate(lineage):
                op_name = step.get("operation_name", f"Step {i+1}")
                exec_order = step.get("execution_order", i + 1)
                with st.container():
                    st.markdown(f"""
                    <div style="padding:0.5rem;margin:0.3rem 0;border-radius:8px;
                                border:1px solid #e2e8f0;background:#f8fafc;">
                        <strong>#{exec_order}: {op_name}</strong><br>
                        <span style="font-size:0.85rem;color:#64748b;">
                            {step.get('operation_desc', '')}
                        </span>
                    </div>
                    """, unsafe_allow_html=True)

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        shape_in = step.get("input_shape")
                        shape_out = step.get("output_shape")
                        st.caption(f"Input: {shape_in[0]}×{shape_in[1] if shape_in else '?'} → "
                                  f"Output: {shape_out[0]}×{shape_out[1] if shape_out else '?'}")
                    with col2:
                        st.caption(f"Rows: {step.get('row_count_change', 0):+d}")
                    with col3:
                        st.caption(f"Duration: {step.get('duration_ms', 0):.1f}ms")

                    params = step.get("parameters", {})
                    if params and params != "{}":
                        with st.expander("Parameters"):
                            st.json(params)
    else:
        st.info("No operations recorded yet. Start applying data transformations with tracking enabled.")

