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


def get_config() -> dict:
    """Load configuration from environment variables."""
    return {
        # Access control
        "ACCESS_CODE": os.getenv("ACCESS_CODE", "cam_demo_2026"),

        # Email / SMTP (optional — app works without it)
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

        # Results expiration (minutes after completion — default 24 hours)
        "JOB_EXPIRY_MINUTES": int(os.getenv("JOB_EXPIRY_MINUTES", "1440")),
    }


def email_configured(config: dict = None) -> bool:
    """Check if SMTP email is configured."""
    if config is None:
        config = get_config()
    return bool(config["SMTP_HOST"] and config["SMTP_USER"])
