
import os
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from modules.database import log_backend_event

def send_audit_email(recipient_email: str, subject: str, html_content: str) -> dict:
    """
    Dispatches automated audit and telemetry reports via SendGrid REST API or fallback SMTP.
    Gracefully handles unconfigured states as a non-error condition.
    """
    sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
    sender_email = os.getenv("REPORT_SENDER_EMAIL", "engine@chrishem.enterprise")

    # 1. Attempt SendGrid REST Dispatch if API key is present
    if sendgrid_api_key:
        url = "https://api.sendgrid.com/v3/mail/send"
        headers = {
            "Authorization": f"Bearer {sendgrid_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "personalizations": [{"to": [{"email": recipient_email}]}],
            "from": {"email": sender_email},
            "subject": subject,
            "content": [{"type": "text/html", "value": html_content}]
        }
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code in [200, 202]:
                log_backend_event("INFO", f"Audit report successfully dispatched via SendGrid to {recipient_email}")
                return {"status": "success", "method": "SendGrid"}
        except Exception as e:
            log_backend_event("WARNING", f"SendGrid dispatch failed, attempting SMTP fallback: {str(e)}")

    # 2. Fallback SMTP Dispatch
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")

    if smtp_server and smtp_user and smtp_password:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = sender_email
            msg["To"] = recipient_email
            msg.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.sendmail(sender_email, recipient_email, msg.as_string())
                
            log_backend_event("INFO", f"Audit report successfully dispatched via SMTP to {recipient_email}")
            return {"status": "success", "method": "SMTP"}
        except Exception as e:
            log_backend_event("ERROR", f"SMTP dispatch failed: {str(e)}")
            return {"status": "error", "message": str(e)}

    # 3. Graceful handling if email credentials are unconfigured
    log_backend_event("INFO", "Email reporting skipped: SendGrid API key or SMTP credentials not configured.")
    return {"status": "skipped", "reason": "Email credentials not configured in environment variables."}

