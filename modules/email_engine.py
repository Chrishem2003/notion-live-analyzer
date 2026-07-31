"""Email Engine  SMTP/SendGrid Integration for Reports."""
import os
import io
import base64
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from typing import Optional, List, Dict, Any

import streamlit as st

# ═══════════════════════════════════════════════════════════════════════
# EMAIL CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "chrishem242@gmail.com")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM_NAME = "Bio-Research Platform"
SMTP_FROM_EMAIL = "chrishem242@gmail.com"

# Alternative: SendGrid
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")

def _send_via_smtp(msg: MIMEMultipart) -> bool:
    """Send email via SMTP."""
    try:
        context = ssl.create_default_context()
        
        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls(context=context)
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
        
        return True
    except Exception as e:
        st.error(f"SMTP send failed: {e}")
        return False

def _send_via_sendgrid(to_email: str, subject: str, html: str, attachments: List[tuple] = None) -> bool:
    """Send email via SendGrid API."""
    if not SENDGRID_API_KEY:
        return False
    
    try:
        import requests
        url = "https://api.sendgrid.com/v3/mail/send"
        
        msg = {
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": SMTP_FROM_EMAIL, "name": SMTP_FROM_NAME},
            "subject": subject,
            "content": [{"type": "text/html", "value": html}],
        }
        
        if attachments:
            msg["attachments"] = []
            for filename, content, mime_type in attachments:
                msg["attachments"].append({
                    "content": base64.b64encode(content).decode(),
                    "filename": filename,
                    "type": mime_type,
                    "disposition": "attachment",
                })
        
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {SENDGRID_API_KEY}",
                "Content-Type": "application/json",
            },
            json=msg,
        )
        return response.status_code in (200, 201, 202)
    except Exception as e:
        st.error(f"SendGrid send failed: {e}")
        return False

def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    plain_body: str = None,
    attachments: List[Dict[str, Any]] = None,
) -> bool:
    """
    Send email with optional attachments.
    
    Args:
        to_email: Recipient email address
        subject: Email subject line
        html_body: HTML email body
        plain_body: Plain text alternative (optional)
        attachments: List of dicts with 'filename', 'content', 'mime_type' keys
    
    Returns:
        True if sent successfully
    """
    if not to_email:
        return False
    
    # Try SendGrid first if available
    if SENDGRID_API_KEY:
        attachments_data = None
        if attachments:
            attachments_data = [
                (a.get("filename", "attachment"), a.get("content", b""), a.get("mime_type", "application/octet-stream"))
                for a in attachments
            ]
        return _send_via_sendgrid(to_email, subject, html_body, attachments_data)
    
    # Fall back to SMTP
    if not SMTP_PASSWORD:
        st.warning("Email service not configured")
        return False
    
    if plain_body is None:
        plain_body = html_body.replace("<br>", "\n").replace("<h1>", "\n").replace("</h1>", "\n")
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
    msg["To"] = to_email
    msg["Date"] = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")
    
    msg.attach(MIMEText(plain_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))
    
    # Add attachments
    if attachments:
        for att in attachments:
            part = MIMEBase(
                att.get("mime_type", "application/octet-stream").split("/")[0],
                att.get("mime_type", "application/octet-stream").split("/")[1] if "/" in att.get("mime_type", "") else "octet-stream"
            )
            part.set_payload(att.get("content", b""))
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f'attachment; filename= {att.get("filename", "attachment")}',
            )
            msg.attach(part)
    
    return _send_via_smtp(msg)

# ═══════════════════════════════════════════════════════════════════════
# EMAIL TEMPLATES
# ═══════════════════════════════════════════════════════════════════════

VERIFICATION_EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
    /* --- GLOBAL SIDEBAR DARK THEMING OVERRIDE --- */
    [data-testid="stSidebar"], section[data-testid="stSidebar"] {
        background-color: #090d16 !important;
        border-right: 1px solid #1e293b !important;
    }
    
    /* Force all sidebar text, links, and headers to high-contrast off-white */
    [data-testid="stSidebar"] *, section[data-testid="stSidebar"] * {
        color: #f8fafc !important;
    }

    /* Target navigation links and text explicitly */
    [data-testid="stSidebarNav"] span, 
    [data-testid="stSidebarNav"] a,
    [data-testid="stSidebarNavLink"],
    [data-testid="stSidebarHeader"] {
        color: #f8fafc !important;
        font-weight: 600 !important;
    }

    /* Navigation item hover state */
    [data-testid="stSidebarNavLink"]:hover,
    [data-testid="stSidebarNav"] a:hover {
        background-color: #1e293b !important;
        border-radius: 8px !important;
    }

    /* Currently selected navigation item active state */
    [data-testid="stSidebarNavLink"][aria-current="page"],
    [data-testid="stSidebarNav"] a[aria-selected="true"] {
        background-color: #0284c7 !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
    }

    /* Custom form inputs inside sidebar */
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] .stMultiSelect label {
        color: #38bdf8 !important;
        font-weight: 700 !important;
    }
        body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #1d4ed8, #3b82f6); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f8fafc; padding: 30px; border: 1px solid #e2e8f0; }}
        .footer {{ background: #1e293b; color: #94a3b8; padding: 20px; text-align: center; border-radius: 0 0 10px 10px; font-size: 12px; }}
        .btn {{ display: inline-block; background: #3b82f6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
        .score-box {{ background: white; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #22c55e; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎓 Student Verification Approved</h1>
        </div>
        <div class="content">
            <p>Congratulations <strong>{user_name}</strong>!</p>
            
            <p>Your student verification has been <strong>successfully approved</strong>.</p>
            
            <div class="score-box">
                <strong>Verification Score:</strong> {score}%<br>
                <strong>University:</strong> {university}<br>
                <strong>Verification Date:</strong> {date}
            </div>
            
            <p>You now have <strong>FREE Standard Tier</strong> access to:</p>
            <ul>
                <li>✅ Full Literature Search Engine</li>
                <li>✅ File Exports (CSV, PDF, Excel)</li>
                <li>✅ Standard Automation Tools</li>
                <li>✅ 15-Day Free Trial to Premium</li>
            </ul>
            
            <p style="margin-top: 30px;">
                <a href="{app_url}" class="btn">Access Your Account</a>
            </p>
        </div>
        <div class="footer">
            <p>Bio-Research Platform  Accelerating Academic Research</p>
            <p>© 2024 Bio-Research Platform. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
"""

AUDIT_REPORT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
    /* --- GLOBAL SIDEBAR DARK THEMING OVERRIDE --- */
    [data-testid="stSidebar"], section[data-testid="stSidebar"] {
        background-color: #090d16 !important;
        border-right: 1px solid #1e293b !important;
    }
    
    /* Force all sidebar text, links, and headers to high-contrast off-white */
    [data-testid="stSidebar"] *, section[data-testid="stSidebar"] * {
        color: #f8fafc !important;
    }

    /* Target navigation links and text explicitly */
    [data-testid="stSidebarNav"] span, 
    [data-testid="stSidebarNav"] a,
    [data-testid="stSidebarNavLink"],
    [data-testid="stSidebarHeader"] {
        color: #f8fafc !important;
        font-weight: 600 !important;
    }

    /* Navigation item hover state */
    [data-testid="stSidebarNavLink"]:hover,
    [data-testid="stSidebarNav"] a:hover {
        background-color: #1e293b !important;
        border-radius: 8px !important;
    }

    /* Currently selected navigation item active state */
    [data-testid="stSidebarNavLink"][aria-current="page"],
    [data-testid="stSidebarNav"] a[aria-selected="true"] {
        background-color: #0284c7 !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
    }

    /* Custom form inputs inside sidebar */
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] .stMultiSelect label {
        color: #38bdf8 !important;
        font-weight: 700 !important;
    }
        body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #0f172a, #1e293b); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f8fafc; padding: 30px; border: 1px solid #e2e8f0; }}
        .footer {{ background: #1e293b; color: #94a3b8; padding: 20px; text-align: center; border-radius: 0 0 10px 10px; font-size: 12px; }}
        .score-card {{ display: inline-block; background: white; padding: 15px 25px; border-radius: 8px; margin: 10px; text-align: center; }}
        .score-value {{ font-size: 24px; font-weight: bold; }}
        .score-label {{ font-size: 12px; color: #64748b; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #e2e8f0; }}
        th {{ background: #f1f5f9; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📜 Academic Audit Report</h1>
            <p>Generated: {generated_date}</p>
        </div>
        <div class="content">
            <h2>Audit Summary</h2>
            
            <div>
                <div class="score-card" style="border-left: 4px solid {ai_color};">
                    <div class="score-value">{ai_score}%</div>
                    <div class="score-label">AI Content</div>
                </div>
                <div class="score-card" style="border-left: 4px solid {plagiarism_color};">
                    <div class="score-value">{plagiarism_score}%</div>
                    <div class="score-label">Plagiarism Risk</div>
                </div>
                <div class="score-card" style="border-left: 4px solid {authenticity_color};">
                    <div class="score-value">{authenticity_score}%</div>
                    <div class="score-label">Authenticity</div>
                </div>
            </div>
            
            <h3>Document Details</h3>
            <table>
                <tr><th>Metric</th><th>Value</th></tr>
                <tr><td>Total Words</td><td>{word_count}</td></tr>
                <tr><td>Sentences</td><td>{sentence_count}</td></tr>
                <tr><td>Burstiness</td><td>{burstiness}</td></tr>
                <tr><td>Vocabulary Richness</td><td>{vocabulary}</td></tr>
            </table>
            
            <p><strong>Session ID:</strong> {session_id}</p>
            
            {report_attachments}
            
            <p style="margin-top: 20px;">
                View full report in the platform: <a href="{app_url}">Access Audit Portal</a>
            </p>
        </div>
        <div class="footer">
            <p>Bio-Research Platform  Academic Integrity Tools</p>
            <p>© 2024 Bio-Research Platform. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
"""

WELCOME_EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
    /* --- GLOBAL SIDEBAR DARK THEMING OVERRIDE --- */
    [data-testid="stSidebar"], section[data-testid="stSidebar"] {
        background-color: #090d16 !important;
        border-right: 1px solid #1e293b !important;
    }
    
    /* Force all sidebar text, links, and headers to high-contrast off-white */
    [data-testid="stSidebar"] *, section[data-testid="stSidebar"] * {
        color: #f8fafc !important;
    }

    /* Target navigation links and text explicitly */
    [data-testid="stSidebarNav"] span, 
    [data-testid="stSidebarNav"] a,
    [data-testid="stSidebarNavLink"],
    [data-testid="stSidebarHeader"] {
        color: #f8fafc !important;
        font-weight: 600 !important;
    }

    /* Navigation item hover state */
    [data-testid="stSidebarNavLink"]:hover,
    [data-testid="stSidebarNav"] a:hover {
        background-color: #1e293b !important;
        border-radius: 8px !important;
    }

    /* Currently selected navigation item active state */
    [data-testid="stSidebarNavLink"][aria-current="page"],
    [data-testid="stSidebarNav"] a[aria-selected="true"] {
        background-color: #0284c7 !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
    }

    /* Custom form inputs inside sidebar */
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] .stMultiSelect label {
        color: #38bdf8 !important;
        font-weight: 700 !important;
    }
        body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #1d4ed8, #3b82f6); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f8fafc; padding: 30px; border: 1px solid #e2e8f0; }}
        .footer {{ background: #1e293b; color: #94a3b8; padding: 20px; text-align: center; border-radius: 0 0 10px 10px; font-size: 12px; }}
        .features {{ list-style: none; padding: 0; }}
        .features li {{ padding: 10px 0; border-bottom: 1px solid #e2e8f0; }}
        .btn {{ display: inline-block; background: #3b82f6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔬 Welcome to Bio-Research Platform</h1>
        </div>
        <div class="content">
            <p>Hello <strong>{user_name}</strong>!</p>
            
            <p>Welcome to the Bio-Research Platform  your comprehensive toolkit for academic research and literature analysis.</p>
            
            <h3>Your Account</h3>
            <ul class="features">
                <li>📧 Email: {user_email}</li>
                <li>💳 Tier: {tier}</li>
                <li>📅 Joined: {join_date}</li>
            </ul>
            
            <h3>Platform Features</h3>
            <ul class="features">
                {features_list}
            </ul>
            
            <p style="margin-top: 30px;">
                <a href="{app_url}" class="btn">Get Started</a>
            </p>
        </div>
        <div class="footer">
            <p>Bio-Research Platform  Accelerating Academic Research</p>
            <p>© 2024 Bio-Research Platform. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
"""

# ═══════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def send_verification_approval(email: str, user_name: str, score: int, university: str) -> bool:
    """Send verification approval email."""
    html = VERIFICATION_EMAIL_TEMPLATE.format(
        user_name=user_name or "Student",
        score=score,
        university=university or "Verified Institution",
        date=datetime.utcnow().strftime("%Y-%m-%d"),
        app_url=os.environ.get("APP_URL", "https://your-app.streamlit.app"),
    )
    return send_email(email, "🎓 Student Verification Approved", html)

def send_audit_report(
    email: str,
    report_data: Dict[str, Any],
    pdf_content: bytes = None,
) -> bool:
    """Send audit report email."""
    scores = report_data.get("composite_scores", {})
    profile = report_data.get("statistical_profile", {})
    
    def get_color(score):
        if score < 30: return "#22c55e"
        if score < 60: return "#f59e0b"
        return "#ef4444"
    
    html = AUDIT_REPORT_TEMPLATE.format(
        generated_date=datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
        ai_score=scores.get("ai_content_score", "N/A"),
        ai_color=get_color(float(scores.get("ai_content_score", 0))),
        plagiarism_score=scores.get("plagiarism_score", "N/A"),
        plagiarism_color=get_color(float(scores.get("plagiarism_score", 0))),
        authenticity_score=scores.get("authenticity_score", "N/A"),
        authenticity_color=get_color(float(scores.get("authenticity_score", 100))),
        word_count=profile.get("total_words", "N/A"),
        sentence_count=profile.get("sentences", "N/A"),
        burstiness=profile.get("burstiness", "N/A"),
        vocabulary=profile.get("vocabulary_richness", "N/A"),
        session_id=report_data.get("session_id", "N/A")[:20] + "...",
        report_attachments="<p>📎 Full PDF report attached.</p>" if pdf_content else "",
        app_url=os.environ.get("APP_URL", "https://your-app.streamlit.app"),
    )
    
    attachments = None
    if pdf_content:
        attachments = [{
            "filename": f"audit_report_{datetime.now().strftime('%Y%m%d')}.pdf",
            "content": pdf_content,
            "mime_type": "application/pdf",
        }]
    
    return send_email(email, "📜 Academic Audit Report Ready", html, attachments=attachments)

def send_welcome_email(email: str, tier: str = "Free") -> bool:
    """Send welcome email to new users."""
    features = {
        "Free": """
            <li>🔍 Basic Literature Search</li>
            <li>📊 Data Visualization Tools</li>
            <li>📁 File Analysis (CSV, Excel)</li>
            <li>📜 Audit Compliance Tools</li>
        """,
        "Standard": """
            <li>✅ Everything in Free</li>
            <li>📚 Full Literature Engine</li>
            <li>📥 Unlimited File Exports</li>
            <li>⚙️ Standard Automation</li>
            <li>🎁 15-Day Premium Trial</li>
        """,
        "Premium": """
            <li>✅ Everything in Standard</li>
            <li>🔬 Deep Research Synthesis</li>
            <li>📧 Automated Email Reports</li>
            <li>📋 Notion Workspace Integration</li>
            <li>👑 Priority Support</li>
        """,
    }
    
    html = WELCOME_EMAIL_TEMPLATE.format(
        user_name=email.split("@")[0],
        user_email=email,
        tier=tier,
        join_date=datetime.utcnow().strftime("%Y-%m-%d"),
        features_list=features.get(tier, features["Free"]),
        app_url=os.environ.get("APP_URL", "https://your-app.streamlit.app"),
    )
    
    return send_email(email, "🔬 Welcome to Bio-Research Platform!", html)

# ═══════════════════════════════════════════════════════════════════════
# EMAIL DELIVERY OPTIONS (UI)
# ═══════════════════════════════════════════════════════════════════════

def render_email_options(report_data: Dict, pdf_bytes: bytes = None):
    """Render UI for email delivery options."""
    st.subheader("📧 Deliver Report")
    
    delivery_method = st.radio(
        "Delivery Method",
        ["📥 Download Now", "📧 Send to Email"],
        horizontal=True,
    )
    
    if delivery_method == "📥 Download Now":
        if pdf_bytes:
            st.download_button(
                "📥 Download PDF Report",
                data=pdf_bytes,
                file_name=f"audit_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",
            )
        else:
            # Generate text report
            from modules.audit_engine import get_audit_orchestrator
            orch = get_audit_orchestrator()
            text_report = orch.generate_export_report([report_data])
            st.download_button(
                "📥 Download Text Report",
                data=text_report,
                file_name=f"audit_report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                mime="text/plain",
            )
    else:
        col1, col2 = st.columns([2, 1])
        with col1:
            email = st.text_input(
                "Email Address",
                value=st.session_state.get("user_email", ""),
            )
        with col2:
            st.markdown("#####")
            if st.button("📤 Send Report"):
                if not email or "@" not in email:
                    st.error("Please enter a valid email")
                else:
                    with st.spinner("Sending..."):
                        success = send_audit_report(email, report_data, pdf_bytes)
                        if success:
                            st.success(f"✅ Report sent to {email}")
                        else:
                            st.error("Failed to send email. Please try again.")
