"""
Extraction Cache — Pre-parsed provision mapping for sample/demo leases.

Caches Stage 1 (extract_provisions) results so demo files skip the expensive
Gemini API call. Cache keys are SHA-256 hashes of the parsed document text.

Cache files live in {LEASE_DIR}/extraction_cache/ as JSON.
"""

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Default cache directory — alongside the app in 05 Lease Analyzer/
_CACHE_DIR = Path(__file__).resolve().parents[3] / "05 Lease Analyzer" / "extraction_cache"


def _cache_key(template_text: str, tenant_text: str) -> str:
    """Generate a cache key from template + tenant text content."""
    t_hash = hashlib.sha256(template_text.encode("utf-8")).hexdigest()[:16]
    n_hash = hashlib.sha256(tenant_text.encode("utf-8")).hexdigest()[:16]
    return f"{t_hash}_{n_hash}"


def get_cache_dir() -> Path:
    """Return the cache directory path, creating it if needed."""
    cache_dir = Path(os.getenv("EXTRACTION_CACHE_DIR", str(_CACHE_DIR)))
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def load_cached_extraction(
    template_text: str,
    tenant_text: str,
) -> Optional[Dict[str, Any]]:
    """Look up a cached extraction result for this template+tenant pair.

    Returns the extraction dict if found, None otherwise.
    """
    key = _cache_key(template_text, tenant_text)
    cache_file = get_cache_dir() / f"{key}.json"

    if not cache_file.exists():
        return None

    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info("Extraction cache HIT: %s", key)
        print(f"[extraction_cache] Cache HIT: {key} — skipping Stage 1 API call", flush=True)

        # Mark metadata so downstream knows this was cached
        if "meta" in data:
            data["meta"]["cached"] = True
            data["meta"]["cache_key"] = key

        return data
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Extraction cache read error for %s: %s", key, e)
        return None


def save_extraction_to_cache(
    template_text: str,
    tenant_text: str,
    extraction: Dict[str, Any],
) -> str:
    """Save an extraction result to the cache.

    Returns the cache key used.
    """
    key = _cache_key(template_text, tenant_text)
    cache_file = get_cache_dir() / f"{key}.json"

    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(extraction, f, indent=2, default=str)
        logger.info("Extraction cache SAVED: %s", key)
        print(f"[extraction_cache] Saved: {key}", flush=True)
    except OSError as e:
        logger.warning("Extraction cache write error for %s: %s", key, e)

    return key
