
"""Unit tests for modules.keepalive."""
import json

import pytest
import requests

from modules import keepalive


class TestInjectClientKeepalive:
    def test_returns_empty_string_when_disabled(self):
        assert keepalive.inject_client_keepalive(0) == ""
        assert keepalive.inject_client_keepalive(-5) == ""

    def test_embeds_interval_in_milliseconds(self):
        script = keepalive.inject_client_keepalive(30)
        assert "30000" in script
        assert script.strip().startswith("<script>")
        assert "visibilitychange" in script


class TestServerKeepAliveThread:
    def test_default_url_from_environment(self, monkeypatch):
        monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://example.dev")
        assert keepalive.ServerKeepAliveThread().app_url == "https://example.dev"

    def test_default_url_fallback(self, monkeypatch):
        monkeypatch.delenv("RENDER_EXTERNAL_URL", raising=False)
        assert keepalive.ServerKeepAliveThread().app_url == "http://localhost:8501"

    def test_explicit_url_wins(self, monkeypatch):
        monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://example.dev")
        assert keepalive.ServerKeepAliveThread("https://other.dev").app_url == "https://other.dev"

    def test_start_is_idempotent(self, monkeypatch):
        started = []

        class FakeThread:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

            def start(self):
                started.append(self.kwargs)

            def is_alive(self):
                return True

        monkeypatch.setattr(keepalive.threading, "Thread", lambda **kw: FakeThread(**kw))
        ka = keepalive.ServerKeepAliveThread("http://x", interval=1)
        ka.start()
        ka.start()
        assert len(started) == 1
        assert started[0]["daemon"] is True
        assert ka.is_alive is True

    def test_stop_clears_running_flag(self, monkeypatch):
        fake_thread = type("T", (), {"start": lambda self: None, "is_alive": lambda self: False})()
        monkeypatch.setattr(keepalive.threading, "Thread", lambda **kw: fake_thread)
        ka = keepalive.ServerKeepAliveThread("http://x")
        ka.start()
        ka.stop()
        assert ka._running is False

    def test_is_alive_false_before_start(self):
        assert keepalive.ServerKeepAliveThread("http://x").is_alive is False

    def test_run_loop_pings_then_exits(self, monkeypatch):
        calls = []
        ka = keepalive.ServerKeepAliveThread("http://x", interval=0)

        def fake_head(url, timeout=None):
            calls.append((url, timeout))
            ka._running = False
            return type("R", (), {"status_code": 200})()

        monkeypatch.setattr(keepalive.requests, "head", fake_head)
        monkeypatch.setattr(keepalive.time, "sleep", lambda s: None)
        ka._running = True
        ka._run()
        assert calls == [("http://x", 10)]

    def test_run_loop_survives_request_errors(self, monkeypatch):
        ka = keepalive.ServerKeepAliveThread("http://x", interval=0)
        attempts = []

        def fake_head(url, timeout=None):
            attempts.append(url)
            ka._running = False
            raise requests.exceptions.ConnectionError("down")

        monkeypatch.setattr(keepalive.requests, "head", fake_head)
        monkeypatch.setattr(keepalive.time, "sleep", lambda s: None)
        ka._running = True
        ka._run()
        assert attempts == ["http://x"]

    def test_run_loop_survives_unexpected_errors(self, monkeypatch):
        ka = keepalive.ServerKeepAliveThread("http://x", interval=0)

        def fake_head(url, timeout=None):
            ka._running = False
            raise RuntimeError("boom")

        monkeypatch.setattr(keepalive.requests, "head", fake_head)
        monkeypatch.setattr(keepalive.time, "sleep", lambda s: None)
        ka._running = True
        ka._run()  # must not raise


class TestHealthCheck:
    def test_health_html_contains_json_payload(self, monkeypatch):
        monkeypatch.setattr(keepalive, "_start_time", 100.0)
        monkeypatch.setattr(keepalive.time, "time", lambda: 160.0)
        html = keepalive.get_health_check_html()
        assert "Healthy" in html
        payload = json.loads(html.split("<pre>")[1].split("</pre>")[0])
        assert payload["status"] == "healthy"
        assert payload["service"] == "notion-live-analyzer"
        assert payload["uptime"] == pytest.approx(60.0)

    def test_get_start_time(self, monkeypatch):
        monkeypatch.setattr(keepalive, "_start_time", 42.0)
        assert keepalive._get_start_time() == 42.0


class TestWatchdog:
    def test_check_returns_true_while_fresh(self, monkeypatch):
        clock = [0.0]
        monkeypatch.setattr(keepalive.time, "time", lambda: clock[0])
        watchdog = keepalive.Watchdog(max_stale_seconds=100)
        clock[0] = 50.0
        assert watchdog.check() is True

    def test_check_returns_false_when_stale(self, monkeypatch):
        clock = [0.0]
        monkeypatch.setattr(keepalive.time, "time", lambda: clock[0])
        watchdog = keepalive.Watchdog(max_stale_seconds=10)
        clock[0] = 100.0
        assert watchdog.check() is False

    def test_mark_healthy_resets_timer(self, monkeypatch):
        clock = [0.0]
        monkeypatch.setattr(keepalive.time, "time", lambda: clock[0])
        watchdog = keepalive.Watchdog(max_stale_seconds=10)
        clock[0] = 100.0
        watchdog.mark_healthy()
        clock[0] = 105.0
        assert watchdog.check() is True


class TestSingletons:
    def test_start_and_stop_server_keepalive(self, monkeypatch):
        events = []
        monkeypatch.setattr(keepalive._server_keepalive, "start", lambda: events.append("start"))
        monkeypatch.setattr(keepalive._server_keepalive, "stop", lambda: events.append("stop"))
        keepalive.start_server_keepalive("https://app.dev", interval=42)
        assert keepalive._server_keepalive.app_url == "https://app.dev"
        assert keepalive._server_keepalive.interval == 42
        keepalive.stop_server_keepalive()
        assert events == ["start", "stop"]

    def test_start_keeps_existing_url_when_none_given(self, monkeypatch):
        monkeypatch.setattr(keepalive._server_keepalive, "start", lambda: None)
        keepalive._server_keepalive.app_url = "https://keep.dev"
        keepalive.start_server_keepalive(interval=7)
        assert keepalive._server_keepalive.app_url == "https://keep.dev"

    def test_get_watchdog_returns_singleton(self):
        assert keepalive.get_watchdog() is keepalive._watchdog
