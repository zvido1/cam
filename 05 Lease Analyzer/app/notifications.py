"""
CAM Lease Analyzer Web App — Email Notifications

Sends email via SendGrid (preferred), Gmail API (OAuth2), or SMTP fallback.
If none is configured, logs the notification instead.
"""

import base64
import logging
import os
import smtplib
from email import encoders
from email.message import EmailMessage
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import List, Optional

from app.config import get_config, email_configured, gmail_api_configured, sendgrid_configured

logger = logging.getLogger(__name__)

MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024


def _build_html_email(
    job_id: str,
    results_url: str,
    summary: dict,
    attachment_info: Optional[dict] = None,
    mode: str = "compare",
) -> tuple:
    """Build HTML + plain text email bodies. Returns (html, plain).

    Step 255: when ``mode == "compare"`` (Mode A), insert a single locked line
    referencing the new Aligned Provision Comparison artifact. Mode C jobs
    never generate that artifact, so the line is suppressed there.
    """
    info = attachment_info or {}
    is_mode_c = (mode == "analyze")
    deviates = summary.get("deviates", 0)
    total = summary.get("total_provisions_checked", 0)
    critical = summary.get("critical", 0)
    high = summary.get("high", 0)
    medium = summary.get("medium", 0)
    low = summary.get("low", 0)

    # Summary banner color based on highest severity
    if critical > 0:
        banner_color = "#c0392b"
        banner_bg = "#fdf2f2"
        banner_border = "#e74c3c"
        status_line = f"🚨 {critical} critical finding{'s' if critical != 1 else ''} require immediate attention"
    elif high > 0:
        banner_color = "#c0470a"
        banner_bg = "#fff4ef"
        banner_border = "#e8613c"
        status_line = f"⚠️ {high} high-severity finding{'s' if high != 1 else ''} require attorney review"
    elif deviates > 0:
        banner_color = "#856404"
        banner_bg = "#fffbf0"
        banner_border = "#f0c040"
        status_line = f"📋 {deviates} deviation{'s' if deviates != 1 else ''} found — review recommended"
    else:
        banner_color = "#155724"
        banner_bg = "#f0fff4"
        banner_border = "#28a745"
        status_line = "✅ All provisions conform to the standard template"

    # Severity rows — only show non-zero
    sev_rows = ""
    if critical > 0:
        sev_rows += f'<tr><td style="padding:4px 0;color:#c0392b;">🚨 Critical</td><td style="padding:4px 0;font-weight:600;">{critical}</td></tr>'
    if high > 0:
        sev_rows += f'<tr><td style="padding:4px 0;color:#c0470a;">🟠 High</td><td style="padding:4px 0;font-weight:600;">{high}</td></tr>'
    if medium > 0:
        sev_rows += f'<tr><td style="padding:4px 0;color:#856404;">🟡 Medium</td><td style="padding:4px 0;font-weight:600;">{medium}</td></tr>'
    if low > 0:
        sev_rows += f'<tr><td style="padding:4px 0;color:#555;">⚪ Low</td><td style="padding:4px 0;font-weight:600;">{low}</td></tr>'
    if not sev_rows:
        sev_rows = '<tr><td colspan="2" style="padding:4px 0;color:#155724;">No deviations found</td></tr>'

    # Attached files list
    attachment_lines = ""
    if info.get("summary_included"):
        attachment_lines += '<li>📄 Lease_Analysis_Synopsis.pdf — combined CAM synopsis</li>'
    annotated = info.get("annotated_tenants", [])
    unannotated = info.get("unannotated_tenants", [])
    for fname in annotated:
        attachment_lines += f'<li>📎 Annotated: {fname}</li>'
    for fname in unannotated:
        attachment_lines += f'<li style="color:#888;">📄 {fname} (annotation not available for TXT files)</li>'
    attachments_section = f"""
        <p style="margin:16px 0 6px;font-weight:600;">Attached Files:</p>
        <ul style="margin:0;padding-left:20px;color:#2980b9;line-height:1.8;">{attachment_lines}</ul>
    """ if attachment_lines else ""

    # Step 255: locked one-line reference to the Aligned Provision Comparison
    # artifact. Mode A only. Phrasing is fixed by the spec — do NOT change.
    comparison_reference_html = ""
    comparison_reference_plain = ""
    if not is_mode_c:
        comparison_reference_html = (
            '<p style="margin:14px 0 0;color:#444;font-size:0.92rem;">'
            'Also included: Aligned Provision Comparison '
            '(view both leases clause-by-clause)'
            '</p>'
        )
        comparison_reference_plain = (
            "Also included: Aligned Provision Comparison "
            "(view both leases clause-by-clause)\n"
        )

    short_id = job_id[:12] if len(job_id) > 12 else job_id
    from datetime import datetime as _dt
    current_year = _dt.now().year

    html = f"""
<html>
<body style="font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;color:#333;line-height:1.6;background:#f5f6fa;margin:0;padding:20px;">
  <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">

    <!-- Header -->
    <div style="background:#1e2a3a;padding:24px 32px;text-align:center;">
      <h1 style="margin:0;color:#fff;font-size:1.4rem;font-weight:700;letter-spacing:0.02em;">Vered.ai</h1>
      <p style="margin:4px 0 0;color:#94a3b8;font-size:0.85rem;">Lease Analysis Complete</p>
    </div>

    <!-- Body -->
    <div style="padding:28px 32px;">
      <p style="margin:0 0 20px;">Your lease analysis is ready. Here's a summary of what was found:</p>

      <!-- Status banner -->
      <div style="background:{banner_bg};border-left:4px solid {banner_border};padding:14px 18px;border-radius:4px;margin-bottom:24px;">
        <p style="margin:0;color:{banner_color};font-weight:600;">{status_line}</p>
        <p style="margin:6px 0 0;color:#555;font-size:0.9rem;">{total} provisions analyzed · Job {short_id}</p>
      </div>

      <!-- Severity breakdown -->
      <table style="width:100%;border-collapse:collapse;margin-bottom:24px;">
        <tr style="border-bottom:1px solid #eee;">
          <td style="padding:6px 0;font-weight:600;color:#555;font-size:0.85rem;text-transform:uppercase;letter-spacing:0.05em;">Finding</td>
          <td style="padding:6px 0;font-weight:600;color:#555;font-size:0.85rem;text-transform:uppercase;letter-spacing:0.05em;">Count</td>
        </tr>
        {sev_rows}
      </table>

      {attachments_section}
      {comparison_reference_html}

      <!-- CTA Button -->
      <div style="text-align:center;margin:28px 0 20px;">
        <a href="{results_url}"
           style="background:#1e2a3a;color:#fff;padding:14px 28px;text-decoration:none;border-radius:6px;font-weight:600;font-size:1rem;display:inline-block;letter-spacing:0.02em;">
          View Interactive Dashboard →
        </a>
      </div>

      <!-- Expiry notice -->
      <div style="background:#fffbf0;border:1px solid #f0c040;border-radius:4px;padding:12px 16px;font-size:0.85rem;color:#856404;">
        <strong>Note:</strong> Results are automatically purged from our servers after 7 days.
      </div>
    </div>

    <!-- Footer -->
    <div style="background:#f8f9fa;padding:16px 32px;text-align:center;border-top:1px solid #eee;">
      <p style="margin:0;font-size:0.78rem;color:#95a5a6;">
        Uploaded files deleted immediately. Analysis results purged after 7 days.<br>
        © {current_year} Vered.ai · <a href="https://www.vered.ai" style="color:#95a5a6;">vered.ai</a>
      </p>
    </div>

  </div>
</body>
</html>
"""

    plain = (
        f"Your lease analysis is complete.\n\n"
        f"Results: {deviates} deviation(s) found across {total} provisions checked.\n"
    )
    if critical:
        plain += f"  Critical: {critical}\n"
    if high:
        plain += f"  High: {high}\n"
    if medium:
        plain += f"  Medium: {medium}\n"
    if low:
        plain += f"  Low: {low}\n"
    if comparison_reference_plain:
        plain += f"\n{comparison_reference_plain}"
    plain += f"\nView your results: {results_url}\n\nJob ID: {job_id}\n"

    return html, plain


def send_job_complete_email(
    to_email: str,
    job_id: str,
    job_url: str,
    summary: dict,
    attachments: Optional[List[str]] = None,
    attachment_info: Optional[dict] = None,
    tenant_names: Optional[List[str]] = None,
    mode: str = "compare",
) -> bool:
    """Send notification that analysis is done with link to results.

    Step 255: ``mode`` is forwarded to the body builder so Mode A emails get
    the locked Aligned Provision Comparison reference line and Mode C emails
    do not.
    """
    def _strip_ext(name: str) -> str:
        return Path(name).stem if name else name

    names = [_strip_ext(n) for n in (tenant_names or []) if n]
    if len(names) == 1:
        subject = f"Lease Analysis Ready \u2014 {names[0]}"
    elif len(names) == 2:
        subject = f"Lease Analysis Ready \u2014 {names[0]} & {names[1]}"
    elif len(names) >= 3:
        subject = f"Lease Analysis Ready \u2014 {len(names)} Leases Reviewed"
    else:
        subject = "Your Lease Analysis is Ready"
    html, plain = _build_html_email(job_id, job_url, summary, attachment_info, mode=mode)
    return _send_email(to_email, subject, plain, html=html, attachments=attachments)


def send_job_failed_email(
    to_email: str,
    job_id: str,
    error_summary: str,
) -> bool:
    """Send notification that something went wrong."""
    subject = "Lease Analysis — Error During Processing"
    plain = (
        f"Your lease analysis encountered an error during processing.\n\n"
        f"Error: {error_summary}\n\n"
        f"Please try again or contact support.\n\n"
        f"Job ID: {job_id}\n"
    )
    return _send_email(to_email, subject, plain)


def _send_email(
    to_email: str,
    subject: str,
    body: str,
    html: Optional[str] = None,
    attachments: Optional[List[str]] = None,
) -> bool:
    """Send email via SendGrid → Gmail API → SMTP → log fallback."""
    config = get_config()

    if not email_configured(config) and not sendgrid_configured(config):
        logger.info(
            f"Email not configured — logging notification:\n"
            f"  To: {to_email}\n  Subject: {subject}\n  Body:\n{body}"
        )
        return True

    if sendgrid_configured(config):
        return _send_via_sendgrid(to_email, subject, body, html, attachments, config)

    if gmail_api_configured(config):
        return _send_via_gmail_api(to_email, subject, body, html, attachments, config)

    return _send_via_smtp(to_email, subject, body, html, attachments, config)


def _send_via_sendgrid(
    to_email: str,
    subject: str,
    plain: str,
    html: Optional[str],
    attachments: Optional[List[str]],
    config: dict,
) -> bool:
    """Send email using SendGrid REST API (stdlib only — no pip dependency)."""
    try:
        import urllib.request
        import json as _json

        from_email_raw = config.get("SENDGRID_FROM_EMAIL") or config.get("NOTIFICATION_FROM") or "noreply@vered.ai"
        # Support "Name <email>" format, or just an email address
        if "<" in from_email_raw:
            import re as _re
            _m = _re.match(r"(.+?)<(.+?)>", from_email_raw)
            from_email = {"email": _m.group(2).strip(), "name": _m.group(1).strip()} if _m else {"email": from_email_raw}
        else:
            from_email = {"email": from_email_raw, "name": "Vered.ai"}

        payload = {
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": from_email if isinstance(from_email, dict) else {"email": from_email},
            "subject": subject,
            "content": [
                {"type": "text/plain", "value": plain},
            ],
        }
        if html:
            payload["content"].append({"type": "text/html", "value": html})

        # Attachments
        if attachments:
            valid, _ = _filter_attachments(attachments)
            if valid:
                import base64 as _b64
                sg_attachments = []
                for p in valid:
                    safe_name = _sanitize_attachment_filename(p.name)
                    encoded = _b64.b64encode(p.read_bytes()).decode()
                    sg_attachments.append({
                        "content": encoded,
                        "filename": safe_name,
                        "type": "application/octet-stream",
                        "disposition": "attachment",
                    })
                if sg_attachments:
                    payload["attachments"] = sg_attachments

        data = _json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            "https://api.sendgrid.com/v3/mail/send",
            data=data,
            headers={
                "Authorization": f"Bearer {config['SENDGRID_API_KEY']}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            logger.info(f"SendGrid: sent to {to_email} — HTTP {status}")
            return status in (200, 202)

    except Exception as e:
        logger.error(f"SendGrid failed to {to_email}: {e} — falling back to SMTP")
        return _send_via_smtp(to_email, subject, plain, html, attachments, config)


def _send_via_gmail_api(
    to_email: str,
    subject: str,
    plain: str,
    html: Optional[str],
    attachments: Optional[List[str]],
    config: dict,
) -> bool:
    """Send email using Gmail API with OAuth2 credentials."""
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = Credentials(
            None,
            refresh_token=config["GMAIL_REFRESH_TOKEN"],
            client_id=config["GMAIL_CLIENT_ID"],
            client_secret=config["GMAIL_CLIENT_SECRET"],
            token_uri="https://oauth2.googleapis.com/token",
        )
        service = build("gmail", "v1", credentials=creds)

        msg = MIMEMultipart("mixed")
        msg["From"] = f"CAM Lease Analysis <{config['GMAIL_USER']}>"
        msg["To"] = to_email
        msg["Subject"] = subject

        # Multipart/alternative for plain + HTML
        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(plain, "plain"))
        if html:
            alt.attach(MIMEText(html, "html"))
        msg.attach(alt)

        # Attachments
        if attachments:
            valid, _ = _filter_attachments(attachments)
            for p in valid:
                safe_name = _sanitize_attachment_filename(p.name)
                part = MIMEBase("application", "octet-stream")
                part.set_payload(p.read_bytes())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f'attachment; filename="{safe_name}"')
                msg.attach(part)
            logger.info(f"Attaching {len(valid)} file(s) via Gmail API")

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        result = service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()

        logger.info(f"Gmail API: sent to {to_email} — id {result['id']}")
        return True

    except Exception as e:
        logger.error(f"Gmail API failed: {e} — falling back to SMTP")
        return _send_via_smtp(to_email, subject, plain, html, attachments, config)


def _send_via_smtp(
    to_email: str,
    subject: str,
    plain: str,
    html: Optional[str],
    attachments: Optional[List[str]],
    config: dict,
) -> bool:
    """Send email using SMTP (fallback)."""
    try:
        msg = MIMEMultipart("mixed")
        msg["From"] = config.get("NOTIFICATION_FROM") or config.get("SMTP_USER", "")
        msg["To"] = to_email
        msg["Subject"] = subject

        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(plain, "plain"))
        if html:
            alt.attach(MIMEText(html, "html"))
        msg.attach(alt)

        if attachments:
            valid, _ = _filter_attachments(attachments)
            for p in valid:
                safe_name = _sanitize_attachment_filename(p.name)
                part = MIMEBase("application", "octet-stream")
                part.set_payload(p.read_bytes())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f'attachment; filename="{safe_name}"')
                msg.attach(part)

        port = int(config.get("SMTP_PORT", 587))
        if port == 465:
            import ssl
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(config["SMTP_HOST"], port, context=ctx) as server:
                server.login(config["SMTP_USER"], config["SMTP_PASSWORD"])
                server.send_message(msg)
        else:
            with smtplib.SMTP(config["SMTP_HOST"], port) as server:
                server.starttls()
                server.login(config["SMTP_USER"], config["SMTP_PASSWORD"])
                server.send_message(msg)

        logger.info(f"SMTP: sent to {to_email}: {subject}")
        return True

    except Exception as e:
        logger.error(f"SMTP failed to {to_email}: {e}")
        return False


def _sanitize_attachment_filename(filename: str) -> str:
    """Sanitize filename for safe use in email Content-Disposition headers.
    Replaces Unicode characters that cause Gmail to show 'noname' attachments.
    """
    replacements = {
        '\u2014': '-',   # em dash
        '\u2013': '-',   # en dash
        '\u2018': "'",   # left single quote
        '\u2019': "'",   # right single quote
        '\u201c': '"',   # left double quote
        '\u201d': '"',   # right double quote
        '\u2026': '...',  # ellipsis
    }
    for char, replacement in replacements.items():
        filename = filename.replace(char, replacement)
    # Remove any remaining non-ASCII characters
    filename = filename.encode('ascii', 'ignore').decode('ascii')
    # Clean up any double spaces or leading/trailing spaces
    filename = ' '.join(filename.split())
    return filename or 'attachment'


def _filter_attachments(attachments: List[str]) -> tuple:
    """Filter to valid files within size limit. Returns (valid_paths, reason)."""
    total_size = 0
    valid = []
    for filepath in (attachments or []):
        if not filepath:  # skip None and empty strings
            continue
        p = Path(filepath)
        if p.exists() and p.is_file():  # is_file() prevents Path("") matching cwd
            size = p.stat().st_size
            if size == 0:  # skip empty files — they show as "noname" in Gmail
                logger.warning(f"Skipping empty attachment: {p.name}")
                continue
            total_size += size
            valid.append(p)
    if total_size > MAX_ATTACHMENT_BYTES:
        logger.warning(f"Attachments too large ({total_size/1024/1024:.1f} MB) — summary only")
        return valid[:1], "size_limit"
    return valid, None
