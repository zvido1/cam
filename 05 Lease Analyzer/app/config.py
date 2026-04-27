"""
CAM Lease Analyzer Web App — Configuration

All settings via environment variables with sensible defaults.
"""

import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

# ── Path resolution ──
APP_DIR = Path(__file__).parent.resolve()          # 05 Lease Analyzer/app/
LEASE_DIR = APP_DIR.parent.resolve()               # 05 Lease Analyzer/
CAM_ROOT = LEASE_DIR.parent.resolve()              # CAM project root

# Load .env from the Lease Analyzer directory
if load_dotenv:
    load_dotenv(LEASE_DIR / ".env")

# Ensure cam package is importable
if str(CAM_ROOT) not in sys.path:
    sys.path.insert(0, str(CAM_ROOT))


# ── App version ──
# Bump this manually on significant changes so Railway logs are self-annotating.
# Format: YYYY-MM-DD.N (date + build counter)
APP_VERSION = os.getenv("APP_VERSION", "2026-03-20.1")

# Git SHA — Railway injects RAILWAY_GIT_COMMIT_SHA automatically.
GIT_SHA = os.getenv("RAILWAY_GIT_COMMIT_SHA", "")[:8] or "local"


def get_config() -> dict:
    """Load configuration from environment variables."""
    return {
        # Access control
        "ACCESS_CODE": os.getenv("ACCESS_CODE", "cam_demo_2026"),

        # Email — SendGrid (preferred) → Gmail API → SMTP fallback
        "SENDGRID_API_KEY": os.getenv("SENDGRID_API_KEY", ""),
        "SENDGRID_FROM_EMAIL": os.getenv("SENDGRID_FROM_EMAIL", ""),
        "GMAIL_CLIENT_ID": os.getenv("GMAIL_CLIENT_ID", ""),
        "GMAIL_CLIENT_SECRET": os.getenv("GMAIL_CLIENT_SECRET", ""),
        "GMAIL_REFRESH_TOKEN": os.getenv("GMAIL_REFRESH_TOKEN", ""),
        "GMAIL_USER": os.getenv("GMAIL_USER", ""),
        # SMTP fallback (optional)
        "SMTP_HOST": os.getenv("SMTP_HOST", ""),
        "SMTP_PORT": int(os.getenv("SMTP_PORT", "587")),
        "SMTP_USER": os.getenv("SMTP_USER", ""),
        "SMTP_PASSWORD": os.getenv("SMTP_PASSWORD", ""),
        "NOTIFICATION_FROM": os.getenv("NOTIFICATION_FROM", ""),

        # App
        "APP_BASE_URL": os.getenv("APP_BASE_URL", "http://localhost:8000"),

        # Directories
        "UPLOAD_DIR": os.getenv("UPLOAD_DIR", str(LEASE_DIR / "uploads")),
        "RESULTS_DIR": os.getenv("RESULTS_DIR", str(LEASE_DIR / "results")),

        # Results expiration (minutes after completion — default 7 days).
        # Set JOB_EXPIRY_MINUTES env var to override (e.g. 1440 = 24h, 10080 = 7 days).
        "JOB_EXPIRY_MINUTES": int(os.getenv("JOB_EXPIRY_MINUTES", "10080")),
    }


def email_configured(config: dict = None) -> bool:
    """Check if email is configured (Gmail API or SMTP)."""
    if config is None:
        config = get_config()
    gmail_ok = bool(
        config.get("GMAIL_CLIENT_ID")
        and config.get("GMAIL_CLIENT_SECRET")
        and config.get("GMAIL_REFRESH_TOKEN")
        and config.get("GMAIL_USER")
    )
    smtp_ok = bool(config.get("SMTP_HOST") and config.get("SMTP_USER"))
    return gmail_ok or smtp_ok


def gmail_api_configured(config: dict = None) -> bool:
    """Check if Gmail API credentials are configured."""
    if config is None:
        config = get_config()
    return bool(
        config.get("GMAIL_CLIENT_ID")
        and config.get("GMAIL_CLIENT_SECRET")
        and config.get("GMAIL_REFRESH_TOKEN")
        and config.get("GMAIL_USER")
    )


def sendgrid_configured(config: dict = None) -> bool:
    """Check if SendGrid API key is configured."""
    if config is None:
        config = get_config()
    return bool(config.get("SENDGRID_API_KEY"))
