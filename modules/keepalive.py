"""
Keep-Alive System — multi-layer approach to prevent app sleep.
5 layers: Client JS + Server Thread + Streamlit Config + Cron + Auto-Restart
"""
import time
import threading
import logging
import requests
from typing import Optional

from modules.runtime_perf import resolve_app_url

logger = logging.getLogger(__name__)

# ─── Layer 1: Client-Side JS Heartbeat ───────────────────────────────
def inject_client_keepalive(interval_sec: int = 300):
    """
    Inject JavaScript that periodically pings the app to keep the session alive.
    This is Layer 1 of the keep-alive system.
    """
    if interval_sec <= 0:
        return ""

    keep_alive_ms = interval_sec * 1000
    script = f"""
    <script>
    // Keep-Alive Layer 1: Client-Side Heartbeat
    (function() {{
        // Clear any existing interval
        if (window._ka_interval) {{
            clearInterval(window._ka_interval);
        }}
        window._ka_interval = setInterval(function() {{
            fetch(window.location.href, {{ method: 'HEAD', cache: 'no-store' }})
                .then(r => console.log('[Keep-Alive] Ping OK @', new Date().toISOString()))
                .catch(e => console.warn('[Keep-Alive] Ping failed', e));
        }}, {keep_alive_ms});

        // Visibility change: re-enable keep-alive when tab becomes visible
        document.addEventListener('visibilitychange', function() {{
            if (!document.hidden && !window._ka_interval) {{
                console.log('[Keep-Alive] Tab visible — re-establishing heartbeat');
                window._ka_interval = setInterval(function() {{
                    fetch(window.location.href, {{ method: 'HEAD', cache: 'no-store' }})
                        .then(r => console.log('[Keep-Alive] Ping OK @', new Date().toISOString()))
                        .catch(e => console.warn('[Keep-Alive] Ping failed', e));
                }}, {keep_alive_ms});
            }}
        }});

        console.log('[Keep-Alive] Heartbeat started — interval: {keep_alive_ms}ms');
    }})();
    </script>
    """
    return script


# ─── Layer 2: Server-Side Background Thread ──────────────────────────
class ServerKeepAliveThread:
    """Background thread that pings the app from inside the server."""

    def __init__(self, app_url: Optional[str] = None, interval: int = 300):
        self.app_url = app_url or resolve_app_url()
        self.interval = interval
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Start the background keep-alive thread.

        No-op without a public URL: pinging the container's own localhost keeps
        nothing awake and only holds a thread open for the process lifetime.
        """
        if self._running or not self.app_url:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="keepalive-server")
        self._thread.start()
        logger.info(f"[Keep-Alive Layer 2] Server thread started — pinging {self.app_url} every {self.interval}s")

    def stop(self):
        """Stop the background keep-alive thread."""
        self._running = False
        logger.info("[Keep-Alive Layer 2] Server thread stopped")

    def _run(self):
        """Main loop for the keep-alive thread."""
        while self._running:
            try:
                response = requests.head(self.app_url, timeout=10)
                logger.debug(f"[Keep-Alive] Server ping → {response.status_code}")
            except requests.exceptions.RequestException as e:
                logger.warning(f"[Keep-Alive] Server ping failed: {e}")
            except Exception as e:
                logger.error(f"[Keep-Alive] Unexpected error: {e}")
            time.sleep(self.interval)

    @property
    def is_alive(self) -> bool:
        """Check if the thread is running."""
        return self._thread is not None and self._thread.is_alive()


# ─── Layer 3: Streamlit Config Heartbeat ─────────────────────────────
# Handled via .streamlit/config.toml:
# [server]
# heartbeatInterval = 5000
# maxUploadSize = 50
# enableXsrfProtection = false


# ─── Layer 4: External Cron / Health Monitor ─────────────────────────
def get_health_check_html() -> str:
    """Return a simple health check response for external monitors."""
    import json
    health_data = {
        "status": "healthy",
        "timestamp": time.time(),
        "uptime": time.time() - _get_start_time(),
        "service": "notion-live-analyzer",
        "version": "2.0.0",
    }
    return f"""
    <html>
    <head><title>Health Check</title></head>
    <body style="font-family: monospace; padding: 2rem;">
        <h1>✅ Notion Live Analyzer — Healthy</h1>
        <pre>{json.dumps(health_data, indent=2)}</pre>
        <p>Time: {time.ctime()}</p>
    </body>
    </html>
    """

_start_time = time.time()

def _get_start_time() -> float:
    """Get the application start time."""
    return _start_time


# ─── Layer 5: Auto-Restart Watchdog ──────────────────────────────────
class Watchdog:
    """
    Monitors the application health and triggers auto-restart if needed.
    In Streamlit, auto-restart is achieved via st.rerun().
    """

    def __init__(self, max_stale_seconds: int = 300):
        self.max_stale = max_stale_seconds
        self._last_healthy = time.time()

    def check(self) -> bool:
        """Check if the app is healthy. Returns False if restart needed."""
        elapsed = time.time() - self._last_healthy
        if elapsed > self.max_stale:
            logger.warning(f"[Watchdog] App appears stale ({elapsed:.0f}s since last check)")
            return False
        self._last_healthy = time.time()
        return True

    def mark_healthy(self):
        """Mark the app as healthy."""
        self._last_healthy = time.time()


# ─── Singleton Instance ───────────────────────────────────────────────
_server_keepalive = ServerKeepAliveThread()
_watchdog = Watchdog()

def start_server_keepalive(app_url: Optional[str] = None, interval: int = 300):
    """Start the server-side keep-alive thread (singleton)."""
    if app_url:
        _server_keepalive.app_url = app_url
    _server_keepalive.interval = interval
    _server_keepalive.start()

def stop_server_keepalive():
    """Stop the server-side keep-alive thread."""
    _server_keepalive.stop()

def get_watchdog() -> Watchdog:
    """Get the watchdog singleton."""
    return _watchdog

