#!/usr/bin/env python3
"""
Pre-parse demo leases — generate extraction cache for sample files.

Runs Stage 1 (provision extraction) on each demo tenant against the demo
template and saves results to extraction_cache/. This allows demo runs
to skip the expensive Gemini API call.

Usage:
    cd "05 Lease Analyzer"
    python preparse_demos.py
"""

import json
import sys
import time
from pathlib import Path

# Ensure project root is importable
APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(APP_DIR))

# Load environment (API keys + app config) using cam's built-in loader
from cam.core.config import find_and_load_env
find_and_load_env()

from cam.adapters.lease_review.lease_parser import parse_document
from cam.adapters.lease_review.lease_extract import extract_provisions
from cam.adapters.lease_review.lease_provision_taxonomy import get_active_provisions
from cam.adapters.lease_review.extraction_cache import save_extraction_to_cache, _cache_key

DEMO_DIR = APP_DIR / "static" / "demo"
TEMPLATE_FILE = DEMO_DIR / "template.txt"

DEMO_TENANTS = [
    "T-01_clean.txt",
    "T-03_obvious.txt",
    "T-07_aggressive.txt",
    "T-10_sophisticated.txt",
]


def main():
    if not TEMPLATE_FILE.exists():
        print(f"ERROR: Template not found at {TEMPLATE_FILE}")
        sys.exit(1)

    print("Parsing template...", flush=True)
    template_text = parse_document(str(TEMPLATE_FILE))
    print(f"  Template: {len(template_text)} chars", flush=True)

    provisions = get_active_provisions()
    print(f"  Provisions: {len(provisions)}", flush=True)

    config = {
        "tenant_word_count": 0,  # will be set per tenant
    }

    results = []
    for tenant_name in DEMO_TENANTS:
        tenant_path = DEMO_DIR / tenant_name
        if not tenant_path.exists():
            print(f"\nSKIPPING {tenant_name} — file not found")
            continue

        print(f"\n{'='*60}", flush=True)
        print(f"EXTRACTING: {tenant_name}", flush=True)
        print(f"{'='*60}", flush=True)

        tenant_text = parse_document(str(tenant_path))
        word_count = len(tenant_text.split())
        config["tenant_word_count"] = word_count
        print(f"  Tenant: {len(tenant_text)} chars ({word_count} words)", flush=True)

        # Check if already cached
        key = _cache_key(template_text, tenant_text)
        cache_file = APP_DIR / "extraction_cache" / f"{key}.json"
        if cache_file.exists():
            print(f"  Already cached: {key} — skipping API call", flush=True)
            results.append((tenant_name, key, "cached"))
            continue

        start = time.time()
        try:
            extraction = extract_provisions(template_text, tenant_text, provisions, config)
            elapsed = time.time() - start

            cache_key = save_extraction_to_cache(template_text, tenant_text, extraction)
            n_provisions = len(extraction.get("provisions", []))
            n_discovered = len(extraction.get("discovered_provisions", []))
            print(f"  Done: {n_provisions} provisions, {n_discovered} discovered in {elapsed:.1f}s", flush=True)
            print(f"  Cached as: {cache_key}", flush=True)
            results.append((tenant_name, cache_key, "extracted"))
        except Exception as e:
            elapsed = time.time() - start
            print(f"  FAILED after {elapsed:.1f}s: {e}", flush=True)
            results.append((tenant_name, None, f"error: {e}"))

        # Brief cooldown between API calls
        if tenant_name != DEMO_TENANTS[-1]:
            print("  Cooldown 10s...", flush=True)
            time.sleep(10)

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for name, key, status in results:
        print(f"  {name}: {status} ({key or 'n/a'})")
    print(f"\nCache directory: {APP_DIR / 'extraction_cache'}")


if __name__ == "__main__":
    main()
