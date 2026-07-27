"""
Email delivery for audit reports
================================
Two interchangeable transports, chosen by whichever environment variables are
set: the SendGrid v3 REST API (preferred on hosted deployments, no SDK needed)
or plain SMTP. With neither configured every call returns a
:class:`DeliveryResult` explaining which variable is missing, so the UI can
offer "download instead" rather than raising at the user.

    SENDGRID_API_KEY        SendGrid transport
    SMTP_HOST / SMTP_PORT / SMTP_USERNAME / SMTP_PASSWORD / SMTP_USE_TLS
    REPORT_SENDER_EMAIL     From: address (required by both transports)
    REPORT_SENDER_NAME      optional display name
"""
from __future__ import annotations

import os
import re
import smtplib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Any, Dict, List, Optional, Sequence, Tuple

import requests

SENDGRID_ENDPOINT = "https://api.sendgrid.com/v3/mail/send"
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
DEFAULT_TIMEOUT = 15


class EmailError(Exception):
    """Raised for programming errors, not for delivery failures."""


@dataclass(frozen=True)
class Attachment:
    filename: str
    content: bytes
    mime_type: str = "application/pdf"


@dataclass(frozen=True)
class DeliveryResult:
    sent: bool
    transport: str
    detail: str = ""
    status_code: Optional[int] = None

    @property
    def configured(self) -> bool:
        return self.transport != "none"


def valid_email(address: str) -> bool:
    return bool(EMAIL_PATTERN.match((address or "").strip()))


def sender() -> Tuple[str, str]:
    """``(address, display name)`` for the From header."""
    address = os.environ.get("REPORT_SENDER_EMAIL", "").strip()
    name = os.environ.get("REPORT_SENDER_NAME", "Research Suite Audit").strip()
    return address, name


def active_transport() -> str:
    """``'sendgrid'``, ``'smtp'`` or ``'none'``."""
    if not os.environ.get("REPORT_SENDER_EMAIL", "").strip():
        return "none"
    if os.environ.get("SENDGRID_API_KEY", "").strip():
        return "sendgrid"
    if os.environ.get("SMTP_HOST", "").strip():
        return "smtp"
    return "none"


def configuration_hint() -> str:
    """Explain to an admin exactly what is missing."""
    if not os.environ.get("REPORT_SENDER_EMAIL", "").strip():
        return "Set REPORT_SENDER_EMAIL, plus either SENDGRID_API_KEY or SMTP_HOST."
    if active_transport() == "none":
        return "Set SENDGRID_API_KEY, or SMTP_HOST (with SMTP_USERNAME/SMTP_PASSWORD)."
    return ""


# ═══════════════════════════════════════════════════════════════════════
# Transports
# ═══════════════════════════════════════════════════════════════════════
def _sendgrid_payload(
    to: Sequence[str],
    subject: str,
    body: str,
    html: Optional[str],
    attachments: Sequence[Attachment],
) -> Dict[str, Any]:
    import base64

    address, name = sender()
    content = [{"type": "text/plain", "value": body}]
    if html:
        content.append({"type": "text/html", "value": html})
    payload: Dict[str, Any] = {
        "personalizations": [{"to": [{"email": r} for r in to]}],
        "from": {"email": address, "name": name},
        "subject": subject,
        "content": content,
    }
    if attachments:
        payload["attachments"] = [
            {
                "content": base64.b64encode(a.content).decode(),
                "filename": a.filename,
                "type": a.mime_type,
                "disposition": "attachment",
            }
            for a in attachments
        ]
    return payload


def _send_via_sendgrid(
    to: Sequence[str],
    subject: str,
    body: str,
    html: Optional[str],
    attachments: Sequence[Attachment],
) -> DeliveryResult:
    key = os.environ["SENDGRID_API_KEY"].strip()
    try:
        response = requests.post(
            SENDGRID_ENDPOINT,
            json=_sendgrid_payload(to, subject, body, html, attachments),
            headers={"Authorization": f"Bearer {key}"},
            timeout=DEFAULT_TIMEOUT,
        )
    except requests.RequestException as exc:
        return DeliveryResult(False, "sendgrid", f"Network error: {exc}")
    if response.status_code in (200, 201, 202):
        return DeliveryResult(True, "sendgrid", "Accepted by SendGrid.", response.status_code)
    return DeliveryResult(
        False, "sendgrid", f"SendGrid rejected the message: {response.text[:200]}",
        response.status_code,
    )


def _build_mime(
    to: Sequence[str],
    subject: str,
    body: str,
    html: Optional[str],
    attachments: Sequence[Attachment],
) -> EmailMessage:
    address, name = sender()
    message = EmailMessage()
    message["From"] = f"{name} <{address}>" if name else address
    message["To"] = ", ".join(to)
    message["Subject"] = subject
    message.set_content(body)
    if html:
        message.add_alternative(html, subtype="html")
    for item in attachments:
        maintype, _, subtype = item.mime_type.partition("/")
        message.add_attachment(
            item.content,
            maintype=maintype or "application",
            subtype=subtype or "octet-stream",
            filename=item.filename,
        )
    return message


def _send_via_smtp(
    to: Sequence[str],
    subject: str,
    body: str,
    html: Optional[str],
    attachments: Sequence[Attachment],
) -> DeliveryResult:
    host = os.environ["SMTP_HOST"].strip()
    port = int(os.environ.get("SMTP_PORT", "587"))
    username = os.environ.get("SMTP_USERNAME", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "")
    use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() not in ("false", "0", "no")
    message = _build_mime(to, subject, body, html, attachments)
    try:
        with smtplib.SMTP(host, port, timeout=DEFAULT_TIMEOUT) as server:
            if use_tls:
                server.starttls()
            if username:
                server.login(username, password)
            server.send_message(message)
    except (smtplib.SMTPException, OSError) as exc:
        return DeliveryResult(False, "smtp", f"SMTP error: {exc}")
    return DeliveryResult(True, "smtp", f"Handed to {host}.")


def send(
    to: Sequence[str],
    subject: str,
    body: str,
    html: Optional[str] = None,
    attachments: Sequence[Attachment] = (),
) -> DeliveryResult:
    """Deliver a message through whichever transport is configured."""
    recipients = [r.strip() for r in to if r and r.strip()]
    if not recipients:
        raise EmailError("At least one recipient is required.")
    invalid = [r for r in recipients if not valid_email(r)]
    if invalid:
        return DeliveryResult(False, active_transport(), f"Invalid address: {invalid[0]}")
    transport = active_transport()
    if transport == "none":
        return DeliveryResult(False, "none", configuration_hint())
    if transport == "sendgrid":
        return _send_via_sendgrid(recipients, subject, body, html, attachments)
    return _send_via_smtp(recipients, subject, body, html, attachments)


# ═══════════════════════════════════════════════════════════════════════
# Audit report rendering
# ═══════════════════════════════════════════════════════════════════════
@dataclass
class AuditSummary:
    """The handful of audit numbers worth putting in an email."""

    document: str
    authenticity: Optional[float] = None
    ai_content: Optional[float] = None
    similarity: Optional[float] = None
    citation_coverage: Optional[float] = None
    findings: List[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def rows(self) -> List[Tuple[str, str]]:
        def pct(value: Optional[float]) -> str:
            return "—" if value is None else f"{value:.1f}%"

        return [
            ("Authenticity", pct(self.authenticity)),
            ("AI-pattern score", pct(self.ai_content)),
            ("Internal corpus similarity", pct(self.similarity)),
            ("Citation coverage", pct(self.citation_coverage)),
        ]


def render_report(summary: AuditSummary) -> Tuple[str, str, str]:
    """Return ``(subject, plain text, html)`` for an audit summary."""
    stamp = summary.generated_at.strftime("%Y-%m-%d %H:%M UTC")
    subject = f"Audit report — {summary.document}"
    lines = [f"Audit report for: {summary.document}", f"Generated: {stamp}", ""]
    lines += [f"{label}: {value}" for label, value in summary.rows()]
    if summary.findings:
        lines += ["", "Findings:"] + [f"  - {f}" for f in summary.findings]
    lines += [
        "",
        "Similarity is measured against this workspace's own corpus and the "
        "references you supplied — it is not a web-wide plagiarism check.",
    ]
    text = "\n".join(lines)

    cells = "".join(
        f"<tr><td style='padding:4px 12px 4px 0'>{label}</td>"
        f"<td style='padding:4px 0'><b>{value}</b></td></tr>"
        for label, value in summary.rows()
    )
    findings_html = (
        "<h4>Findings</h4><ul>"
        + "".join(f"<li>{f}</li>" for f in summary.findings)
        + "</ul>"
        if summary.findings
        else ""
    )
    html = (
        f"<div style='font-family:system-ui,sans-serif'>"
        f"<h3>Audit report — {summary.document}</h3>"
        f"<p style='color:#666'>Generated {stamp}</p>"
        f"<table>{cells}</table>{findings_html}"
        f"<p style='color:#666;font-size:12px'>Similarity is measured against this "
        f"workspace's own corpus and the references you supplied — it is not a "
        f"web-wide plagiarism check.</p></div>"
    )
    return subject, text, html


def send_audit_report(
    to: Sequence[str],
    summary: AuditSummary,
    attachments: Sequence[Attachment] = (),
) -> DeliveryResult:
    subject, text, html = render_report(summary)
    return send(to, subject, text, html, attachments)
