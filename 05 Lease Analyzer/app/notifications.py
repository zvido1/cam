"""
CAM Lease Analyzer Web App — Email Notifications

Sends email via Gmail API (OAuth2) if configured, falls back to SMTP.
If neither is configured, logs the notification instead.
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

from app.config import get_config, email_configured, gmail_api_configured

logger = logging.getLogger(__name__)

# Gmail attachment limit (25 MB)
MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024


def send_job_complete_email(
    to_email: str,
    job_id: str,
    job_url: str,
    summary: dict,
    attachments: Optional[List[str]] = None,
    attachment_info: Optional[dict] = None,
) -> bool:
    """Send notification that analysis is done with link to results."""
    subject = "Your lease analysis is complete"
    info = attachment_info or {}

    deviates = summary.get("deviates", 0)
    total = summary.get("total_provisions_checked", 0)
    critical = summary.get("critical", 0)
    high = summary.get("high", 0)

    body = (
        f"Your lease analysis is complete.\n\n"
        f"Results: {deviates} deviation(s) found across {total} provisions checked.\n"
    )
    if critical or high:
        body += f"  - {critical} critical, {high} high severity\n"

    body += "\nAttached:\n"
    if info.get("summary_included"):
        body += "  - Lease_Analysis_Summary.pdf \u2014 combined findings across all tenants\n"
    else:
        body += "  - Note: Summary PDF could not be generated for this analysis.\n"

    annotated = info.get("annotated_tenants", [])
    unannotated = info.get("unannotated_tenants", [])
    if annotated:
        for fname in annotated:
            body += f"  - Annotated: {fname}\n"
    if unannotated:
        body += f"  - Annotation unavailable for: {', '.join(unannotated)} (TXT files)\n"

    body += (
        f"\nView the full interactive dashboard:\n{job_url}\n\n"
        f"Once you open the link, you'll have 15 minutes to download your files.\n"
        f"If you don't open the link, results are available for up to 24 hours.\n\n"
        f"\U0001f512 Your documents were deleted after processing. "
        f"Results will be permanently deleted after the download window closes.\n\n"
        f"Job ID: {job_id}\n"
    )

    return _send_email(to_email, subject, body, attachments=attachments)


def send_job_failed_email(
    to_email: str,
    job_id: str,
    error_summary: str,
) -> bool:
    """Send notification that something went wrong."""
    subject = "Lease analysis encountered an error"
    body = (
        f"Your lease analysis encountered an error during processing.\n\n"
        f"Error: {error_summary}\n\n"
        f"Please try again or contact support.\n\n"
        f"Job ID: {job_id}\n"
    )
    return _send_email(to_email, subject, body)


def _send_email(
    to_email: str,
    subject: str,
    body: str,
    attachments: Optional[List[str]] = None,
) -> bool:
    """Send email via Gmail API if configured, else SMTP, else log."""
    config = get_config()

    if not email_configured(config):
        att_names = [Path(a).name for a in (attachments or [])]
        logger.info(
            "Email not configured — logging notification:\n"
            f"  To: {to_email}\n"
            f"  Subject: {subject}\n"
            f"  Attachments: {att_names}\n"
            f"  Body:\n{body}"
        )
        return True

    if gmail_api_configured(config):
        return _send_via_gmail_api(to_email, subject, body, attachments, config)
    else:
        return _send_via_smtp(to_email, subject, body, attachments, config)


def _send_via_gmail_api(
    to_email: str,
    subject: str,
    body: str,
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

        # Build message
        msg = MIMEMultipart()
        msg["From"] = config["GMAIL_USER"]
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        # Add attachments if any
        if attachments:
            valid_attachments, _ = _filter_attachments(attachments)
            for p in valid_attachments:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(p.read_bytes())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={p.name}")
                msg.attach(part)
            logger.info(f"Attaching {len(valid_attachments)} file(s) via Gmail API")

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        result = service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()

        logger.info(f"Gmail API: email sent to {to_email} — message id {result['id']}")
        return True

    except Exception as e:
        logger.error(f"Gmail API send failed: {e} — falling back to SMTP")
        return _send_via_smtp(to_email, subject, body, attachments, config)


def _send_via_smtp(
    to_email: str,
    subject: str,
    body: str,
    attachments: Optional[List[str]],
    config: dict,
) -> bool:
    """Send email using SMTP (fallback)."""
    try:
        msg = MIMEMultipart()
        msg["From"] = config.get("NOTIFICATION_FROM") or config.get("SMTP_USER", "")
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        if attachments:
            valid_attachments, _ = _filter_attachments(attachments)
            for p in valid_attachments:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(p.read_bytes())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={p.name}")
                msg.attach(part)
            logger.info(f"Attaching {len(valid_attachments)} file(s) via SMTP")

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

        logger.info(f"SMTP: email sent to {to_email}: {subject}")
        return True

    except Exception as e:
        logger.error(f"SMTP send failed to {to_email}: {e}")
        return False


def _filter_attachments(attachments: List[str]) -> tuple:
    """Filter attachments to valid files within size limit.

    Returns (valid_paths, skipped_reason)
    """
    total_size = 0
    valid = []
    for filepath in attachments:
        p = Path(filepath)
        if p.exists():
            total_size += p.stat().st_size
            valid.append(p)

    if total_size > MAX_ATTACHMENT_BYTES:
        logger.warning(
            f"Attachments too large ({total_size / 1024 / 1024:.1f} MB). "
            f"Attaching summary only."
        )
        return valid[:1], "size_limit"

    return valid, None
