"""Unit tests for modules.email_reports."""
from datetime import datetime, timezone

import pytest
import requests

from modules import email_reports as mail

EMAIL_VARS = (
    "SENDGRID_API_KEY", "SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME",
    "SMTP_PASSWORD", "SMTP_USE_TLS", "REPORT_SENDER_EMAIL", "REPORT_SENDER_NAME",
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in EMAIL_VARS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def sendgrid(monkeypatch):
    monkeypatch.setenv("REPORT_SENDER_EMAIL", "audit@example.org")
    monkeypatch.setenv("SENDGRID_API_KEY", "SG.test-key")


@pytest.fixture
def smtp(monkeypatch):
    monkeypatch.setenv("REPORT_SENDER_EMAIL", "audit@example.org")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.org")


class FakeResponse:
    def __init__(self, status_code=202, text=""):
        self.status_code = status_code
        self.text = text


class FakeSMTP:
    """Records what a transport would have done."""

    instances = []

    def __init__(self, host, port, timeout=None):
        self.host, self.port, self.timeout = host, port, timeout
        self.started_tls = False
        self.login_args = None
        self.messages = []
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self):
        self.started_tls = True

    def login(self, username, password):
        self.login_args = (username, password)

    def send_message(self, message):
        self.messages.append(message)


@pytest.fixture
def fake_smtp(monkeypatch):
    FakeSMTP.instances = []
    monkeypatch.setattr(mail.smtplib, "SMTP", FakeSMTP)
    return FakeSMTP


class TestConfiguration:
    def test_no_configuration_reports_none(self):
        assert mail.active_transport() == "none"

    def test_sender_alone_is_not_enough(self, monkeypatch):
        monkeypatch.setenv("REPORT_SENDER_EMAIL", "audit@example.org")
        assert mail.active_transport() == "none"
        assert "SENDGRID_API_KEY" in mail.configuration_hint()

    def test_transport_without_sender_is_none(self, monkeypatch):
        monkeypatch.setenv("SENDGRID_API_KEY", "SG.x")
        assert mail.active_transport() == "none"
        assert "REPORT_SENDER_EMAIL" in mail.configuration_hint()

    def test_sendgrid_wins_over_smtp(self, monkeypatch, sendgrid):
        monkeypatch.setenv("SMTP_HOST", "smtp.example.org")
        assert mail.active_transport() == "sendgrid"

    def test_smtp_used_when_no_api_key(self, smtp):
        assert mail.active_transport() == "smtp"

    def test_hint_is_empty_once_configured(self, sendgrid):
        assert mail.configuration_hint() == ""

    def test_sender_name_defaults(self, sendgrid):
        address, name = mail.sender()
        assert address == "audit@example.org"
        assert name


class TestValidation:
    @pytest.mark.parametrize(
        "address", ["a@b.co", "first.last@uni.ac.ug", "x+tag@example.org"]
    )
    def test_valid(self, address):
        assert mail.valid_email(address)

    @pytest.mark.parametrize("address", ["", "nope", "a@b", "a b@c.com", "@b.com", None])
    def test_invalid(self, address):
        assert not mail.valid_email(address)

    def test_no_recipient_is_a_programming_error(self, sendgrid):
        with pytest.raises(mail.EmailError):
            mail.send([], "subject", "body")

    def test_invalid_recipient_is_a_result_not_an_exception(self, sendgrid):
        result = mail.send(["nope"], "subject", "body")
        assert not result.sent
        assert "Invalid address" in result.detail


class TestUnconfiguredSend:
    def test_returns_hint_instead_of_raising(self):
        result = mail.send(["a@b.co"], "subject", "body")
        assert not result.sent
        assert result.transport == "none"
        assert not result.configured
        assert "REPORT_SENDER_EMAIL" in result.detail


class TestSendGridTransport:
    def test_successful_send(self, monkeypatch, sendgrid):
        captured = {}

        def fake_post(url, json=None, headers=None, timeout=None):
            captured.update(url=url, json=json, headers=headers)
            return FakeResponse(202)

        monkeypatch.setattr(mail.requests, "post", fake_post)
        result = mail.send(["reader@example.org"], "Subject", "Body")

        assert result.sent and result.transport == "sendgrid"
        assert captured["url"] == mail.SENDGRID_ENDPOINT
        assert captured["headers"]["Authorization"] == "Bearer SG.test-key"
        assert captured["json"]["from"]["email"] == "audit@example.org"
        assert captured["json"]["personalizations"][0]["to"] == [
            {"email": "reader@example.org"}
        ]

    def test_html_is_sent_as_a_second_part(self, monkeypatch, sendgrid):
        captured = {}
        monkeypatch.setattr(
            mail.requests, "post",
            lambda url, json=None, **kw: (captured.update(json=json), FakeResponse())[1],
        )
        mail.send(["r@example.org"], "S", "text", "<b>html</b>")
        types = [part["type"] for part in captured["json"]["content"]]
        assert types == ["text/plain", "text/html"]

    def test_attachments_are_base64(self, monkeypatch, sendgrid):
        import base64

        captured = {}
        monkeypatch.setattr(
            mail.requests, "post",
            lambda url, json=None, **kw: (captured.update(json=json), FakeResponse())[1],
        )
        mail.send(
            ["r@example.org"], "S", "body",
            attachments=[mail.Attachment("r.txt", b"hello", "text/plain")],
        )
        item = captured["json"]["attachments"][0]
        assert base64.b64decode(item["content"]) == b"hello"
        assert item["filename"] == "r.txt"

    def test_rejection_is_reported(self, monkeypatch, sendgrid):
        monkeypatch.setattr(
            mail.requests, "post",
            lambda *a, **kw: FakeResponse(403, "forbidden: unverified sender"),
        )
        result = mail.send(["r@example.org"], "S", "body")
        assert not result.sent
        assert result.status_code == 403
        assert "unverified sender" in result.detail

    def test_network_error_is_caught(self, monkeypatch, sendgrid):
        def boom(*a, **kw):
            raise requests.ConnectionError("dns failure")

        monkeypatch.setattr(mail.requests, "post", boom)
        result = mail.send(["r@example.org"], "S", "body")
        assert not result.sent
        assert "dns failure" in result.detail


class TestSMTPTransport:
    def test_successful_send(self, smtp, fake_smtp):
        result = mail.send(["reader@example.org"], "Subject", "Body")
        assert result.sent and result.transport == "smtp"
        server = fake_smtp.instances[0]
        assert (server.host, server.port) == ("smtp.example.org", 587)
        assert server.started_tls
        message = server.messages[0]
        assert message["To"] == "reader@example.org"
        assert message["Subject"] == "Subject"

    def test_credentials_are_used_when_present(self, monkeypatch, smtp, fake_smtp):
        monkeypatch.setenv("SMTP_USERNAME", "apikey")
        monkeypatch.setenv("SMTP_PASSWORD", "secret")
        mail.send(["r@example.org"], "S", "body")
        assert fake_smtp.instances[0].login_args == ("apikey", "secret")

    def test_anonymous_relay_skips_login(self, smtp, fake_smtp):
        mail.send(["r@example.org"], "S", "body")
        assert fake_smtp.instances[0].login_args is None

    def test_tls_can_be_disabled(self, monkeypatch, smtp, fake_smtp):
        monkeypatch.setenv("SMTP_USE_TLS", "false")
        mail.send(["r@example.org"], "S", "body")
        assert not fake_smtp.instances[0].started_tls

    def test_custom_port(self, monkeypatch, smtp, fake_smtp):
        monkeypatch.setenv("SMTP_PORT", "2525")
        mail.send(["r@example.org"], "S", "body")
        assert fake_smtp.instances[0].port == 2525

    def test_attachment_is_attached(self, smtp, fake_smtp):
        mail.send(
            ["r@example.org"], "S", "body",
            attachments=[mail.Attachment("audit.txt", b"data", "text/plain")],
        )
        message = fake_smtp.instances[0].messages[0]
        names = [part.get_filename() for part in message.iter_attachments()]
        assert "audit.txt" in names

    def test_smtp_failure_is_reported(self, monkeypatch, smtp, fake_smtp):
        def boom(self, message):
            raise mail.smtplib.SMTPRecipientsRefused({})

        monkeypatch.setattr(FakeSMTP, "send_message", boom)
        result = mail.send(["r@example.org"], "S", "body")
        assert not result.sent
        assert "SMTP error" in result.detail

    def test_multiple_recipients(self, smtp, fake_smtp):
        mail.send(["a@x.org", "b@x.org"], "S", "body")
        assert fake_smtp.instances[0].messages[0]["To"] == "a@x.org, b@x.org"


class TestRendering:
    def summary(self, **kwargs):
        defaults = dict(
            document="Chapter 3",
            authenticity=88.0,
            ai_content=12.5,
            similarity=4.25,
            citation_coverage=71.0,
            generated_at=datetime(2026, 5, 1, 9, 30, tzinfo=timezone.utc),
        )
        defaults.update(kwargs)
        return mail.AuditSummary(**defaults)

    def test_subject_names_the_document(self):
        subject, _, _ = mail.render_report(self.summary())
        assert subject == "Audit report — Chapter 3"

    def test_text_contains_every_metric(self):
        _, text, _ = mail.render_report(self.summary())
        for fragment in ("88.0%", "12.5%", "4.2%", "71.0%"):
            assert fragment in text

    def test_missing_metrics_render_as_dashes(self):
        _, text, _ = mail.render_report(self.summary(similarity=None))
        assert "Internal corpus similarity: —" in text

    def test_findings_are_listed(self):
        _, text, html = mail.render_report(self.summary(findings=["3 uncited claims"]))
        assert "3 uncited claims" in text
        assert "<li>3 uncited claims</li>" in html

    def test_scope_is_disclosed_in_both_parts(self):
        _, text, html = mail.render_report(self.summary())
        assert "not a web-wide plagiarism check" in text
        assert "not a\nweb-wide plagiarism check" in html or "web-wide" in html

    def test_timestamp_is_utc(self):
        _, text, _ = mail.render_report(self.summary())
        assert "2026-05-01 09:30 UTC" in text

    def test_send_audit_report_uses_the_rendered_subject(self, smtp, fake_smtp):
        result = mail.send_audit_report(["r@example.org"], self.summary())
        assert result.sent
        assert fake_smtp.instances[0].messages[0]["Subject"] == "Audit report — Chapter 3"
