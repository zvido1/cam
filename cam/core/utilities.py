"""
CAM Utilities Module
Extracted from run_gpqa_cam.py for modularity.
Shared utility functions for logging, hashing, and error handling.
"""

import hashlib
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def log(message: str, log_handle=None):
    """Log message with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{timestamp}] {message}"
    print(msg)
    if log_handle:
        log_handle.write(msg + "\n")
        log_handle.flush()


def get_hash(text: str) -> str:
    """Compute SHA256 hash of text."""
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def add_audit_entry(audit_trail: list, round_name: str, model_name: str, role: str, input_text: str, output_text: str):
    """Add a structured entry to the audit trail."""
    audit_trail.append({
        "round": round_name,
        "model": model_name,
        "role": role,
        "input_hash": get_hash(input_text),
        "output_hash": get_hash(output_text),
        "timestamp": datetime.now().isoformat()
    })


def get_prompt_hash(prompt_path: Path) -> str:
    """Compute SHA256 hash of prompt file."""
    with open(prompt_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def check_quota_error(error_msg: str, component_name: str, log_handle) -> bool:
    """
    Check if error is a quota/funding issue. If so, log fatal error and exit.
    Returns True if quota error detected (script will exit), False otherwise.
    
    IMPORTANT: Timeouts and JSON extraction failures are NOT quota errors - 
    they are handled as regular failures that may trigger retries or abstention.
    """
    error_lower = error_msg.lower()
    
    # EXCLUDE timeout errors - these are NOT quota issues
    if "timeout" in error_lower or "timed out" in error_lower or "APITimeoutError" in error_msg:
        return False  # Timeouts are not quota errors
    
    # EXCLUDE JSON extraction/parsing errors - these are NOT quota issues
    # These occur when the model returns valid content but JSON extraction fails
    if "json_extraction_failed" in error_lower or "json_parse_failed" in error_lower:
        return False  # JSON parsing errors are not quota errors
    
    # EXCLUDE empty output errors - these are transient API issues, NOT quota issues
    # v2.5.4 FIX: Google sometimes returns empty responses that should be retried
    if "empty_output" in error_lower or "no extractable text" in error_lower:
        return False  # Empty outputs are transient, not quota errors
    
    # EXCLUDE schema validation errors - these are NOT quota issues
    if "schema" in error_lower and ("validation" in error_lower or "failed" in error_lower):
        return False  # Schema validation errors are not quota errors
    
    # Check for various quota/funding error indicators
    quota_indicators = [
        "insufficient_quota" in error_lower,  # v2.5.4 FIX: was missing "in error_lower"
        "quota" in error_lower and ("exceeded" in error_lower or "limit" in error_lower or "check your plan" in error_lower),
        "429" in error_msg and "rate limit" in error_lower,  # Only 429 with "rate limit", not just any 429
        "rate" in error_lower and "limit" in error_lower and ("quota" in error_lower or "exceeded" in error_lower),
        "billing" in error_lower and "quota" in error_lower,
        "check your plan and billing" in error_lower,
        "exceeded your current quota" in error_lower,
        "please check your plan and billing" in error_lower
    ]
    
    if any(quota_indicators):
        log(f"\n{'='*70}", log_handle)
        log(f"      [FATAL] QUOTA/FUNDING ERROR DETECTED", log_handle)
        log(f"      [FATAL] {component_name} failed due to insufficient quota/funding", log_handle)
        log(f"      [FATAL] Error: {error_msg}", log_handle)
        log(f"      [FATAL] Script stopping immediately - please add funds to continue", log_handle)
        log(f"      [FATAL] All components must work - cannot proceed with partial results", log_handle)
        log(f"{'='*70}\n", log_handle)
        sys.exit(1)
    return False


def normalize_choice_text(text: str) -> str:
    """
    Normalize choice text for fuzzy matching.
    - lowercase
    - collapse whitespace
    - strip punctuation
    - strip leading "mutant " prefix if present
    """
    import string
    if not text:
        return ""
    text = text.lower().strip()
    # Collapse whitespace
    text = " ".join(text.split())
    # Strip punctuation
    text = text.translate(str.maketrans("", "", string.punctuation))
    # Strip common prefixes that might cause drift
    for prefix in ["mutant ", "option ", "choice "]:
        if text.startswith(prefix):
            text = text[len(prefix):]
    return text.strip()
