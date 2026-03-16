"""
CAM Lease Analyzer Web App — Email Notifications

Simple email sender using Python's built-in smtplib.
If SMTP is not configured, logs the notification instead of sending.
"""

import logging
import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import List, Optional

from app.config import get_config, email_configured

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
    """Send notification that analysis is done with link to results.

    Args:
        to_email: Recipient email address.
        job_id: The job identifier.
        job_url: URL to the interactive results dashboard.
        summary: Dict with deviates, total_provisions_checked, critical, high counts.
        attachments: Optional list of file paths to attach (summary DOCX, annotated docs).
        attachment_info: Optional dict with summary_included, annotated_tenants, unannotated_tenants.

    Returns True if sent (or logged), False on error.
    """
    subject = "Your lease analysis is complete"
    info = attachment_info or {}

    # Build plain text body
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

    # Dynamic attachment section
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
        f"\xf0\x9f\x94\x92 Your documents were deleted after processing. "
        f"Results will be permanently deleted after the download window closes.\n\n"
        f"Job ID: {job_id}\n"
    )

    return _send_email(to_email, subject, body, attachments=attachments)


def send_job_failed_email(
    to_email: str,
    job_id: str,
    error_summary: str,
) -> bool:
    """Send notification that something went wrong.

    Returns True if sent (or logged), False on error.
    """
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
    """Send an email or log it if SMTP is not configured."""
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

    try:
        msg = MIMEMultipart()
        msg["From"] = config["NOTIFICATION_FROM"] or config["SMTP_USER"]
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        # Add attachments (if any, and if within size limit)
        if attachments:
            total_size = 0
            valid_attachments = []
            for filepath in attachments:
                p = Path(filepath)
                if p.exists():
                    total_size += p.stat().st_size
                    valid_attachments.append(p)

            if total_size > MAX_ATTACHMENT_BYTES:
                # Too large — attach only the first file (summary) and note in body
                logger.warning(
                    f"Attachments too large ({total_size / 1024 / 1024:.1f} MB). "
                    f"Attaching summary only."
                )
                valid_attachments = valid_attachments[:1]

            for p in valid_attachments:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(p.read_bytes())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={p.name}",
                )
                msg.attach(part)

            logger.info(f"Attaching {len(valid_attachments)} file(s) to email")

        with smtplib.SMTP(config["SMTP_HOST"], config["SMTP_PORT"]) as server:
            server.starttls()
            server.login(config["SMTP_USER"], config["SMTP_PASSWORD"])
            server.send_message(msg)

        logger.info(f"Email sent to {to_email}: {subject}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False
