
"""Unit tests for modules.config."""
import pickle

import pytest

from modules import config


class TestConstants:
    def test_refresh_options(self):
        assert config.DEFAULT_REFRESH_OPTIONS["Off"] == 0
        assert config.DEFAULT_REFRESH_OPTIONS["5 min"] == 300

    def test_keep_alive_options_are_seconds(self):
        assert all(isinstance(v, int) and v > 0 for v in config.DEFAULT_KEEP_ALIVE_OPTIONS.values())

    def test_research_palettes_have_eight_colors(self):
        assert config.RESEARCH_PALETTE_NAMES == list(config.RESEARCH_PALETTES)
        for name, colors in config.RESEARCH_PALETTES.items():
            assert len(colors) == 8, name
            assert all(c.startswith("#") for c in colors), name

    def test_publication_config_keys(self):
        for key in ("font_family", "font_size_title", "marker_size", "margin_t"):
            assert key in config.PUBLICATION_CONFIG


class TestInitSessionState:
    def test_populates_defaults(self, bare_session_state):
        config.init_session_state()
        assert bare_session_state["user_NOTION_TOKEN"] == ""
        assert bare_session_state["creds_validated"] is False
        assert bare_session_state["refresh_choice"] == "30 sec"
        assert bare_session_state["saved_dashboards"] == {}
        assert bare_session_state["statistical_results"] == []

    def test_does_not_overwrite_existing_values(self, bare_session_state):
        bare_session_state["refresh_choice"] = "5 min"
        config.init_session_state()
        assert bare_session_state["refresh_choice"] == "5 min"

    def test_is_idempotent(self, bare_session_state):
        config.init_session_state()
        bare_session_state["theme"] = "dark"
        config.init_session_state()
        assert bare_session_state["theme"] == "dark"


class TestGetSecret:
    def test_session_override_wins(self, bare_session_state, monkeypatch):
        monkeypatch.setenv("NOTION_TOKEN", "from-env")
        bare_session_state["user_NOTION_TOKEN"] = "from-session"
        assert config.get_secret("NOTION_TOKEN") == "from-session"

    def test_falls_back_to_streamlit_secrets(self, bare_session_state, monkeypatch):
        monkeypatch.delenv("NOTION_TOKEN", raising=False)
        monkeypatch.setattr(config.st, "secrets", {"NOTION_TOKEN": "from-secrets"}, raising=False)
        assert config.get_secret("NOTION_TOKEN") == "from-secrets"

    def test_falls_back_to_environment(self, bare_session_state, monkeypatch):
        monkeypatch.setattr(config.st, "secrets", {}, raising=False)
        monkeypatch.setenv("NOTION_TOKEN", "from-env")
        assert config.get_secret("NOTION_TOKEN") == "from-env"

    def test_returns_none_when_unset(self, bare_session_state, monkeypatch):
        monkeypatch.setattr(config.st, "secrets", {}, raising=False)
        monkeypatch.delenv("NOTION_TOKEN", raising=False)
        assert config.get_secret("NOTION_TOKEN") is None

    def test_secret_lookup_error_is_swallowed(self, bare_session_state, monkeypatch):
        class ExplodingSecrets:
            def __contains__(self, item):
                raise RuntimeError("no secrets file")

        monkeypatch.setattr(config.st, "secrets", ExplodingSecrets(), raising=False)
        monkeypatch.setenv("NOTION_TOKEN", "from-env")
        assert config.get_secret("NOTION_TOKEN") == "from-env"

    def test_empty_session_value_is_ignored(self, bare_session_state, monkeypatch):
        monkeypatch.setattr(config.st, "secrets", {}, raising=False)
        bare_session_state["user_NOTION_TOKEN"] = ""
        monkeypatch.setenv("NOTION_TOKEN", "from-env")
        assert config.get_secret("NOTION_TOKEN") == "from-env"


class TestBackgroundImage:
    def test_returns_first_existing_candidate(self, tmp_path, monkeypatch):
        assets = tmp_path / "assets"
        assets.mkdir()
        target = assets / "background.jpg"
        target.write_bytes(b"jpeg-bytes")
        monkeypatch.setattr(config, "ASSETS_DIR", assets)
        monkeypatch.setattr(config, "APP_DIR", tmp_path)
        assert config.find_background_image() == target

    def test_returns_none_when_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "ASSETS_DIR", tmp_path / "assets")
        monkeypatch.setattr(config, "APP_DIR", tmp_path)
        assert config.find_background_image() is None

    @pytest.mark.parametrize(
        "suffix,mime",
        [
            ("png", "image/png"),
            ("jpg", "image/jpeg"),
            ("jpeg", "image/jpeg"),
            ("webp", "image/webp"),
            ("gif", "image/gif"),
            ("svg", "image/svgxml"),
            ("bin", "application/octet-stream"),
        ],
    )
    def test_image_to_data_url_mime_types(self, tmp_path, suffix, mime):
        path = tmp_path / f"img.{suffix}}"
        path.write_bytes(b"abc")
        url = config.image_to_data_url(path)
        assert url.startswith(f"data:{mime}};base64,")
        assert url.endswith("YWJj")


class TestDiskCache:
    @pytest.fixture(autouse=True)
    def cache_dir(self, tmp_path, monkeypatch):
        directory = tmp_path / ".cache"
        monkeypatch.setattr(config, "CACHE_DIR", directory)
        return directory

    def test_save_and_load_roundtrip(self, cache_dir):
        config.save_cache("payload", {"a": [1, 2, 3]})
        assert (cache_dir / "payload.pkl").exists()
        assert config.load_cache("payload") == {"a": [1, 2, 3]}

    def test_load_missing_key_returns_none(self):
        assert config.load_cache("nope") is None

    def test_save_uses_pickle_format(self, cache_dir):
        config.save_cache("raw", [1, 2])
        assert pickle.loads((cache_dir / "raw.pkl").read_bytes()) == [1, 2]

    def test_clear_cache_removes_entries_and_recreates_dir(self, cache_dir):
        config.save_cache("payload", 1)
        config.clear_cache()
        assert cache_dir.exists()
        assert list(cache_dir.iterdir()) == []

    def test_clear_cache_is_safe_when_missing(self, cache_dir):
        config.clear_cache()
        assert not cache_dir.exists()

