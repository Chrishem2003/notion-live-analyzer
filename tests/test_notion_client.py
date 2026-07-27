"""Unit tests for modules.notion_client."""
import hashlib

import pandas as pd
import pytest
import requests

from modules import notion_client as nc


class FakeResponse:
    """Minimal stand-in for ``requests.Response``."""

    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text

    def json(self):
        return self._payload


@pytest.fixture(autouse=True)
def clear_cache():
    nc.clear_request_cache()
    yield
    nc.clear_request_cache()


class TestRichTextAndParsers:
    def test_extract_rich_text_concatenates_plain_text(self):
        assert nc.extract_rich_text([{"plain_text": "Hello "}, {"plain_text": "World"}]) == "Hello World"

    def test_extract_rich_text_handles_empty_and_non_dict(self):
        assert nc.extract_rich_text([]) == ""
        assert nc.extract_rich_text(None) == ""
        assert nc.extract_rich_text(["not-a-dict", {"plain_text": "ok"}]) == "ok"

    def test_parse_formula(self):
        assert nc.parse_formula({"type": "number", "number": 42}) == 42
        assert nc.parse_formula({"type": "string", "string": "abc"}) == "abc"
        assert nc.parse_formula({}) is None
        assert nc.parse_formula({"no_type": 1}) is None

    def test_parse_rollup(self):
        assert nc.parse_rollup({"type": "array", "array": [1, 2]}) == [1, 2]
        assert nc.parse_rollup({"type": "number", "number": 3}) == 3
        assert nc.parse_rollup({}) is None
        assert nc.parse_rollup({"no_type": 1}) is None

    @pytest.mark.parametrize(
        "prop_type,payload,expected",
        [
            ("title", {"title": [{"plain_text": "T"}]}, "T"),
            ("rich_text", {"rich_text": [{"plain_text": "R"}]}, "R"),
            ("number", {"number": 7}, 7),
            ("select", {"select": {"name": "Alpha"}}, "Alpha"),
            ("select", {"select": None}, None),
            ("multi_select", {"multi_select": [{"name": "a"}, {"name": "b"}]}, ["a", "b"]),
            ("multi_select", {"multi_select": []}, []),
            ("status", {"status": {"name": "Done"}}, "Done"),
            ("status", {"status": None}, None),
            ("date", {"date": {"start": "2024-01-01"}}, "2024-01-01"),
            ("date", {"date": None}, None),
            ("checkbox", {"checkbox": True}, True),
            ("checkbox", {}, False),
            ("email", {"email": "a@b.c"}, "a@b.c"),
            ("phone", {"phone": "123"}, "123"),
            ("url", {"url": "https://x.dev"}, "https://x.dev"),
            ("formula", {"formula": {"type": "number", "number": 1}}, 1),
            ("relation", {"relation": [{"id": "p1"}]}, ["p1"]),
            ("relation", {"relation": []}, []),
            ("rollup", {"rollup": {"type": "number", "number": 2}}, 2),
            ("people", {"people": [{"name": "Ada"}, {"id": "u2"}]}, ["Ada", "u2"]),
            ("people", {"people": []}, []),
            ("files", {"files": [{"name": "f.png"}]}, ["f.png"]),
            ("files", {"files": [{"external": {"url": "http://x/f.png"}}]}, ["http://x/f.png"]),
            ("created_by", {"created_by": {"name": "Ada"}}, "Ada"),
            ("created_by", {"created_by": {}}, "Unknown"),
            ("created_time", {"created_time": "2024-01-01T00:00:00Z"}, "2024-01-01T00:00:00Z"),
            ("last_edited_by", {"last_edited_by": {}}, "Unknown"),
            ("last_edited_time", {"last_edited_time": "2024-01-02T00:00:00Z"}, "2024-01-02T00:00:00Z"),
            ("unique_id", {"unique_id": {"prefix": "TASK", "number": 12}}, "TASK-12"),
            ("unique_id", {"unique_id": None}, None),
            ("button", {"button": {"action": "run"}}, "run"),
        ],
    )
    def test_property_parsers(self, prop_type, payload, expected):
        assert nc.NOTION_PROPERTY_PARSERS[prop_type](payload) == expected


class TestCachingDecorator:
    def test_result_is_cached_within_ttl(self):
        calls = []

        @nc._cached_request("unit-test", ttl=60)
        def counted(value):
            calls.append(value)
            return value * 2

        assert counted(3) == 6
        assert counted(3) == 6
        assert calls == [3]

    def test_force_refresh_bypasses_cache(self):
        calls = []

        @nc._cached_request("unit-test-force", ttl=60)
        def counted(value):
            calls.append(value)
            return value

        counted(1)
        counted(1, force_refresh=True)
        assert calls == [1, 1]

    def test_expired_entry_is_recomputed(self, monkeypatch):
        calls = []
        now = [1000.0]
        monkeypatch.setattr(nc.time, "time", lambda: now[0])

        @nc._cached_request("unit-test-ttl", ttl=10)
        def counted(value):
            calls.append(value)
            return value

        counted(5)
        now[0] += 11
        counted(5)
        assert calls == [5, 5]

    def test_clear_request_cache_empties_store(self):
        @nc._cached_request("unit-test-clear", ttl=60)
        def identity(value):
            return value

        identity(1)
        assert nc._request_cache
        nc.clear_request_cache()
        assert nc._request_cache == {}


class TestRateLimiter:
    def test_allows_calls_below_limit_without_sleeping(self, monkeypatch):
        slept = []
        monkeypatch.setattr(nc.time, "sleep", lambda s: slept.append(s))
        limiter = nc.RateLimiter(max_calls=3, per_seconds=1.0)
        for _ in range(3):
            limiter.wait_if_needed()
        assert slept == []
        assert len(limiter.calls) == 3

    def test_sleeps_when_limit_exceeded(self, monkeypatch):
        slept = []
        monkeypatch.setattr(nc.time, "sleep", lambda s: slept.append(s))
        monkeypatch.setattr(nc.time, "time", lambda: 100.0)
        limiter = nc.RateLimiter(max_calls=2, per_seconds=1.0)
        limiter.wait_if_needed()
        limiter.wait_if_needed()
        limiter.wait_if_needed()
        assert len(slept) == 1
        assert slept[0] == pytest.approx(1.0)

    def test_old_calls_fall_out_of_the_window(self, monkeypatch):
        clock = [0.0]
        monkeypatch.setattr(nc.time, "time", lambda: clock[0])
        limiter = nc.RateLimiter(max_calls=1, per_seconds=1.0)
        limiter.wait_if_needed()
        clock[0] = 5.0
        limiter.wait_if_needed()
        assert len(limiter.calls) == 1


class TestHeadersAndErrors:
    def test_make_headers(self):
        headers = nc._make_headers("tok")
        assert headers["Authorization"] == "Bearer tok"
        assert headers["Notion-Version"] == nc.NOTION_VERSION
        assert headers["Content-Type"] == "application/json"

    @pytest.mark.parametrize("status", [401, 403])
    def test_auth_errors_flag_credentials(self, status, bare_session_state):
        assert nc._handle_api_error(FakeResponse(status), "tok") is True
        assert bare_session_state["creds_failed"] is True

    def test_rate_limit_error_is_not_fatal(self, monkeypatch):
        monkeypatch.setattr(nc.time, "sleep", lambda s: None)
        assert nc._handle_api_error(FakeResponse(429), "tok") is False

    def test_missing_database_is_fatal_only_with_db_id(self):
        assert nc._handle_api_error(FakeResponse(404), "tok", "db1") is True
        assert nc._handle_api_error(FakeResponse(404), "tok") is False

    def test_success_is_not_an_error(self):
        assert nc._handle_api_error(FakeResponse(200), "tok", "db1") is False


class TestFingerprinting:
    def test_fingerprint_is_stable_and_order_independent(self):
        props_a = {"Name": {"type": "title"}, "Score": {"type": "number"}}
        props_b = {"Score": {"type": "number"}, "Name": {"type": "title"}}
        assert nc.fingerprint_database(props_a) == nc.fingerprint_database(props_b)

    def test_fingerprint_changes_with_schema(self):
        base = nc.fingerprint_database({"Name": {"type": "title"}})
        assert base != nc.fingerprint_database({"Name": {"type": "rich_text"}})

    def test_non_dict_properties_are_ignored(self):
        assert nc.fingerprint_database({"Name": "oops"}) == hashlib.sha256(b"").hexdigest()


class TestDatabaseDiscovery:
    @pytest.fixture
    def databases(self):
        return [
            {
                "id": "db-simple",
                "title": "Simple",
                "properties": {"Name": {"type": "title"}},
            },
            {
                "id": "db-rich",
                "title": "Rich",
                "properties": {
                    "Name": {"type": "title"},
                    "Score": {"type": "number"},
                    "When": {"type": "date"},
                    "Stage": {"type": "select"},
                    "Tags": {"type": "multi_select"},
                },
            },
        ]

    def test_discover_database_id_picks_richest_schema(self, monkeypatch, databases):
        monkeypatch.setattr(nc, "get_database_options", lambda token: databases)
        assert nc.discover_database_id("tok") == "db-rich"

    def test_discover_database_id_with_no_databases(self, monkeypatch):
        monkeypatch.setattr(nc, "get_database_options", lambda token: [])
        assert nc.discover_database_id("tok") is None

    def test_auto_find_duplicated_db_matches_fingerprint(self, monkeypatch, databases):
        monkeypatch.setattr(nc, "get_database_options", lambda token: databases)
        fingerprint = nc.fingerprint_database(databases[1]["properties"])
        assert nc.auto_find_duplicated_db("tok", fingerprint) == "db-rich"

    def test_auto_find_duplicated_db_returns_none_when_unmatched(self, monkeypatch, databases):
        monkeypatch.setattr(nc, "get_database_options", lambda token: databases)
        assert nc.auto_find_duplicated_db("tok", "0" * 64) is None


class TestGetDatabaseOptions:
    def test_paginates_and_extracts_titles(self, monkeypatch):
        pages = [
            FakeResponse(
                200,
                {
                    "results": [
                        {"id": "db1", "title": [{"plain_text": "First"}], "properties": {}},
                    ],
                    "has_more": True,
                    "next_cursor": "cursor-1",
                },
            ),
            FakeResponse(
                200,
                {
                    "results": [{"id": "db2", "title": [], "properties": {}}],
                    "has_more": False,
                },
            ),
        ]
        seen = []

        def fake_request(method, url, **kwargs):
            seen.append(kwargs.get("json", {}))
            return pages[len(seen) - 1]

        monkeypatch.setattr(nc, "_rate_limited_request", fake_request)
        result = nc.get_database_options("tok", force_refresh=True)
        assert [db["id"] for db in result] == ["db1", "db2"]
        assert result[0]["title"] == "First"
        assert result[1]["title"] == "db2"  # falls back to the id
        assert seen[1]["start_cursor"] == "cursor-1"

    def test_stops_on_http_error(self, monkeypatch):
        monkeypatch.setattr(nc, "_rate_limited_request", lambda *a, **k: FakeResponse(500))
        assert nc.get_database_options("tok", force_refresh=True) == []

    def test_swallows_transport_errors(self, monkeypatch):
        def boom(*a, **k):
            raise RuntimeError("network down")

        monkeypatch.setattr(nc, "_rate_limited_request", boom)
        assert nc.get_database_options("tok", force_refresh=True) == []


class TestGetDatabaseSchema:
    def test_returns_properties(self, monkeypatch):
        payload = {"properties": {"Name": {"type": "title"}}}
        monkeypatch.setattr(nc, "_rate_limited_request", lambda *a, **k: FakeResponse(200, payload))
        assert nc.get_database_schema("tok", "db1", force_refresh=True) == payload["properties"]

    def test_returns_empty_on_error_status(self, monkeypatch):
        monkeypatch.setattr(nc, "_rate_limited_request", lambda *a, **k: FakeResponse(404))
        assert nc.get_database_schema("tok", "db1", force_refresh=True) == {}

    def test_returns_empty_on_exception(self, monkeypatch):
        def boom(*a, **k):
            raise RuntimeError("nope")

        monkeypatch.setattr(nc, "_rate_limited_request", boom)
        assert nc.get_database_schema("tok", "db1", force_refresh=True) == {}


class TestFetchNotionData:
    SCHEMA = {
        "properties": {
            "Name": {"type": "title"},
            "Score": {"type": "number"},
            "Tags": {"type": "multi_select"},
        }
    }

    def _responses(self, query_response):
        schema_response = FakeResponse(200, self.SCHEMA)

        def fake_request(method, url, **kwargs):
            return schema_response if method == "GET" else query_response

        return fake_request

    def test_parses_pages_into_dataframe(self, monkeypatch):
        query = FakeResponse(
            200,
            {
                "results": [
                    {
                        "id": "page-1",
                        "created_time": "2024-01-01T00:00:00Z",
                        "last_edited_time": "2024-01-02T00:00:00Z",
                        "properties": {
                            "Name": {"title": [{"plain_text": "Row one"}]},
                            "Score": {"number": 10},
                            "Tags": {"multi_select": [{"name": "x"}, {"name": "y"}]},
                        },
                    }
                ],
                "has_more": False,
            },
        )
        monkeypatch.setattr(nc, "_rate_limited_request", self._responses(query))
        df = nc.fetch_notion_data("tok", "db1")
        assert list(df.columns) == ["Name", "Score", "Tags", "_page_id", "_created_time", "_last_edited_time"]
        assert df.loc[0, "Name"] == "Row one"
        assert df.loc[0, "Score"] == 10
        assert df.loc[0, "Tags"] == "x, y"
        assert df.loc[0, "_page_id"] == "page-1"

    def test_empty_results_return_empty_dataframe(self, monkeypatch):
        query = FakeResponse(200, {"results": [], "has_more": False})
        monkeypatch.setattr(nc, "_rate_limited_request", self._responses(query))
        assert nc.fetch_notion_data("tok", "db1").empty

    def test_schema_error_returns_empty_dataframe(self, monkeypatch, bare_session_state):
        monkeypatch.setattr(nc, "_rate_limited_request", lambda *a, **k: FakeResponse(401))
        result = nc.fetch_notion_data("tok", "db1")
        assert isinstance(result, pd.DataFrame)
        assert result.empty
        assert bare_session_state["creds_failed"] is True

    def test_schema_exception_returns_empty_dataframe(self, monkeypatch):
        def boom(*a, **k):
            raise RuntimeError("offline")

        monkeypatch.setattr(nc, "_rate_limited_request", boom)
        assert nc.fetch_notion_data("tok", "db1").empty

    def test_query_error_status_stops_after_max_attempts(self, monkeypatch, bare_session_state):
        query = FakeResponse(500, text="server error")
        monkeypatch.setattr(nc, "_rate_limited_request", self._responses(query))
        assert nc.fetch_notion_data("tok", "db1").empty

    def test_query_timeout_is_retried(self, monkeypatch):
        monkeypatch.setattr(nc.time, "sleep", lambda s: None)
        attempts = []

        def fake_request(method, url, **kwargs):
            if method == "GET":
                return FakeResponse(200, self.SCHEMA)
            attempts.append(url)
            raise requests.exceptions.Timeout()

        monkeypatch.setattr(nc, "_rate_limited_request", fake_request)
        assert nc.fetch_notion_data("tok", "db1").empty
        assert len(attempts) == 2  # max_attempts

    def test_query_exception_is_retried(self, monkeypatch):
        monkeypatch.setattr(nc.time, "sleep", lambda s: None)

        def fake_request(method, url, **kwargs):
            if method == "GET":
                return FakeResponse(200, self.SCHEMA)
            raise RuntimeError("boom")

        monkeypatch.setattr(nc, "_rate_limited_request", fake_request)
        assert nc.fetch_notion_data("tok", "db1").empty

    def test_unparseable_property_becomes_none(self, monkeypatch):
        query = FakeResponse(
            200,
            {
                "results": [
                    {
                        "id": "page-1",
                        "properties": {
                            "Name": {"title": [{"plain_text": "ok"}]},
                            "Score": {"number": 1},
                            "Tags": {"multi_select": [{"no_name": True}]},
                        },
                    }
                ],
                "has_more": False,
            },
        )
        monkeypatch.setattr(nc, "_rate_limited_request", self._responses(query))
        df = nc.fetch_notion_data("tok", "db1")
        assert df.loc[0, "Tags"] is None

    def test_unknown_property_type_is_stringified(self, monkeypatch):
        schema = {"properties": {"Weird": {"type": "not_a_real_type"}}}

        def fake_request(method, url, **kwargs):
            if method == "GET":
                return FakeResponse(200, schema)
            return FakeResponse(
                200,
                {"results": [{"id": "p1", "properties": {"Weird": {"x": 1}}}], "has_more": False},
            )

        monkeypatch.setattr(nc, "_rate_limited_request", fake_request)
        df = nc.fetch_notion_data("tok", "db1")
        assert df.loc[0, "Weird"] == "{'x': 1}"

    def test_numeric_strings_are_coerced(self, monkeypatch):
        schema = {"properties": {"Score": {"type": "rich_text"}}}

        def fake_request(method, url, **kwargs):
            if method == "GET":
                return FakeResponse(200, schema)
            return FakeResponse(
                200,
                {
                    "results": [
                        {"id": f"p{i}", "properties": {"Score": {"rich_text": [{"plain_text": str(i)}]}}}
                        for i in range(3)
                    ],
                    "has_more": False,
                },
            )

        monkeypatch.setattr(nc, "_rate_limited_request", fake_request)
        df = nc.fetch_notion_data("tok", "db1")
        assert pd.api.types.is_numeric_dtype(df["Score"])
