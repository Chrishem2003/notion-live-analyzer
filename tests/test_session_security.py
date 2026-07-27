"""Unit tests for modules.session_security."""
import time

import pytest

from modules import session_security as sec

KAMPALA = sec.COUNTRY_CENTROIDS["UG"]
LONDON = sec.COUNTRY_CENTROIDS["GB"]
NAIROBI = sec.COUNTRY_CENTROIDS["KE"]


def headers(**overrides):
    base = {
        "X-Forwarded-For": "102.86.4.10",
        "User-Agent": "Mozilla/5.0",
        "CF-IPCountry": "UG",
    }
    base.update(overrides)
    return base


class TestClientIP:
    def test_reads_the_forwarded_header(self):
        assert sec.client_ip(headers()) == "102.86.4.10"

    def test_header_lookup_is_case_insensitive(self):
        assert sec.client_ip({"x-forwarded-for": "102.86.4.10"}) == "102.86.4.10"

    def test_private_hops_are_skipped(self):
        chain = {"X-Forwarded-For": "10.0.0.4, 192.168.1.9, 102.86.4.10"}
        assert sec.client_ip(chain) == "102.86.4.10"

    def test_falls_back_to_other_proxy_headers(self):
        assert sec.client_ip({"CF-Connecting-IP": "102.86.4.10"}) == "102.86.4.10"

    def test_garbage_is_ignored(self):
        assert sec.client_ip({"X-Forwarded-For": "not-an-ip, also-bad"}) is None

    def test_no_headers(self):
        assert sec.client_ip(None) is None

    def test_ipv6_is_supported(self):
        assert sec.client_ip({"X-Forwarded-For": "2001:4860:4860::8888"})


class TestSignals:
    def test_chain_is_preserved_in_order(self):
        signals = sec.read_signals({"X-Forwarded-For": "1.1.1.1, 2.2.2.2"})
        assert signals.forwarded_chain == ("1.1.1.1", "2.2.2.2")

    def test_country_is_upper_cased(self):
        assert sec.read_signals({"cf-ipcountry": "ug"}).country == "UG"

    def test_placeholder_countries_are_dropped(self):
        assert sec.read_signals({"CF-IPCountry": "XX"}).country is None

    def test_proxy_headers_are_listed(self):
        signals = sec.read_signals(headers(Via="1.1 squid", **{"X-VPN": "yes"}))
        assert set(signals.proxy_headers) == {"via", "x-vpn"}

    def test_clean_session_has_no_proxy_headers(self):
        assert sec.read_signals(headers()).proxy_headers == ()


class TestGeometry:
    def test_distance_between_known_cities(self):
        distance = sec.haversine_km(KAMPALA, LONDON)
        assert 6000 < distance < 7500

    def test_same_point_is_zero(self):
        assert sec.haversine_km(KAMPALA, KAMPALA) == 0

    def test_neighbouring_country_overnight_is_plausible(self):
        impossible, _ = sec.travel_is_impossible(KAMPALA, NAIROBI, seconds=12 * 3600)
        assert not impossible

    def test_short_hops_are_inside_the_grace_radius(self):
        nearby = (KAMPALA[0] + 0.4, KAMPALA[1])
        impossible, speed = sec.travel_is_impossible(KAMPALA, nearby, seconds=1)
        assert not impossible and speed == 0.0

    def test_intercontinental_in_a_minute_is_impossible(self):
        impossible, speed = sec.travel_is_impossible(KAMPALA, LONDON, seconds=60)
        assert impossible and speed > sec.MAX_TRAVEL_KMH

    def test_intercontinental_over_a_day_is_fine(self):
        impossible, _ = sec.travel_is_impossible(KAMPALA, LONDON, seconds=86400)
        assert not impossible

    def test_zero_elapsed_time_does_not_divide_by_zero(self):
        impossible, speed = sec.travel_is_impossible(KAMPALA, LONDON, seconds=0)
        assert not impossible and speed == 0.0


class TestAssess:
    def test_clean_session_passes(self):
        result = sec.assess(headers())
        assert result.level is sec.RiskLevel.OK
        assert result.score == 0
        assert result.allowed

    def test_no_headers_at_all_is_only_a_soft_signal(self):
        result = sec.assess({})
        assert result.level is sec.RiskLevel.OK
        assert result.score > 0

    def test_proxy_header_raises_the_score(self):
        result = sec.assess(headers(Via="1.1 anonymous-proxy"))
        assert result.score >= 25
        assert "Proxy headers" in result.summary

    def test_country_mismatch_is_scored_but_not_flagged_alone(self):
        """Travel and university VPNs cause this constantly — it needs company."""
        result = sec.assess(headers(), declared="NG")
        assert result.level is sec.RiskLevel.OK
        assert result.score >= 30
        assert "does not match" in result.summary

    def test_mismatch_plus_proxy_headers_is_flagged_for_review(self):
        result = sec.assess(headers(Via="1.1 anonymous-proxy"), declared="NG")
        assert result.level is sec.RiskLevel.REVIEW

    def test_matching_declared_country_is_clean(self):
        assert sec.assess(headers(), declared="ug").level is sec.RiskLevel.OK

    def test_long_forwarding_chain_counts(self):
        chain = ", ".join(["102.86.4.10"] * 5)
        assert sec.assess(headers(**{"X-Forwarded-For": chain})).score >= 15

    def test_review_never_blocks_access(self):
        result = sec.assess(headers(Via="1.1 proxy"), declared="NG")
        assert result.level is sec.RiskLevel.REVIEW
        assert result.allowed

    def test_impossible_travel_blocks(self):
        now = time.time()
        history = [sec.SessionSighting("ada@uni.ac.ug", "GB", "1.2.3.4", now - 120)]
        result = sec.assess(headers(), history=history, now=now)
        assert result.level is sec.RiskLevel.BLOCK
        assert "Impossible travel" in result.summary
        assert not result.allowed

    def test_plausible_travel_does_not_block(self):
        now = time.time()
        history = [sec.SessionSighting("ada@uni.ac.ug", "GB", "1.2.3.4", now - 86400)]
        assert sec.assess(headers(), history=history, now=now).level is sec.RiskLevel.OK

    def test_unknown_country_history_is_ignored(self):
        now = time.time()
        history = [sec.SessionSighting("ada@uni.ac.ug", "ZZ", None, now - 60)]
        assert sec.assess(headers(), history=history, now=now).level is sec.RiskLevel.OK

    def test_summary_is_readable_when_clean(self):
        assert "No anomalies" in sec.assess(headers()).summary


class TestSecurityLog:
    @pytest.fixture
    def log(self, tmp_path):
        return sec.SecurityLog(tmp_path / "events.db")

    def test_records_and_reads_back(self, log):
        log.record(sec.assess(headers()), account="ada@uni.ac.ug")
        events = log.recent()
        assert len(events) == 1
        assert events[0]["account"] == "ada@uni.ac.ug"
        assert events[0]["country"] == "UG"

    def test_reasons_are_stored(self, log):
        log.record(sec.assess(headers(Via="proxy")), account="ada@uni.ac.ug")
        assert "Proxy headers" in log.recent()[0]["reasons"]

    def test_recent_is_newest_first(self, log):
        now = time.time()
        for offset in range(3):
            log.record(sec.assess(headers()), account=f"u{offset}", now=now + offset)
        assert [e["account"] for e in log.recent()] == ["u2", "u1", "u0"]

    def test_recent_respects_the_limit(self, log):
        for index in range(5):
            log.record(sec.assess(headers()), account=f"u{index}")
        assert len(log.recent(limit=2)) == 2

    def test_filter_by_level(self, log):
        log.record(sec.assess(headers()), account="clean")
        log.record(sec.assess(headers(Via="proxy"), declared="NG"), account="flagged")
        flagged = log.recent(level=sec.RiskLevel.REVIEW)
        assert [e["account"] for e in flagged] == ["flagged"]

    def test_counts_group_by_level(self, log):
        log.record(sec.assess(headers()), account="a")
        log.record(sec.assess(headers(Via="proxy"), declared="NG"), account="b")
        assert log.counts() == {"ok": 1, "review": 1}

    def test_sightings_feed_the_travel_check(self, log):
        now = time.time()
        log.record(sec.assess(headers()), account="ada@uni.ac.ug", now=now)
        sightings = log.sightings("ada@uni.ac.ug")
        assert sightings[0].country == "UG"
        assert sightings[0].coordinates == KAMPALA

    def test_sightings_are_scoped_to_one_account(self, log):
        log.record(sec.assess(headers()), account="ada@uni.ac.ug")
        log.record(sec.assess(headers()), account="bob@uni.ac.ug")
        assert len(log.sightings("ada@uni.ac.ug")) == 1

    def test_empty_log(self, log):
        assert log.recent() == []
        assert log.counts() == {}
        assert log.sightings("nobody") == []

    def test_uses_accounts_db_path_by_default(self, tmp_path, monkeypatch):
        target = tmp_path / "accounts.db"
        monkeypatch.setenv("ACCOUNTS_DB_PATH", str(target))
        sec.SecurityLog().record(sec.assess(headers()))
        assert target.exists()
