

import psutil
from functools import lru_cache
from modules.database import log_backend_event

@lru_cache(maxsize=128)
def cached_query_processor(query_string: str) -> str:
    """
    Bounded LRU cache for high-frequency analytical queries to prevent RAM bloat.
    """
    return f"Processed result for: {query_string}"

def check_ram_utilization_guard(max_threshold_percent: float = 85.0) -> bool:
    """
    Monitors system RAM utilization and triggers warning flags if memory consumption exceeds safe bounds.
    """
    mem = psutil.virtual_memory()
    if mem.percent > max_threshold_percent:
        log_backend_event("WARNING", f"High RAM usage detected: {mem.percent}% utilized.")
        return False
    return True

def chunked_file_reader(file_path: str, chunk_size: int = 1024 * 1024):
    """
    Generator that reads large files in memory-safe chunks (default 1MB) to prevent OOM errors.
    """
    try:
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk
    except Exception as e:
        log_backend_event("ERROR", f"Chunked file reader exception on {file_path}: {str(e)}")
