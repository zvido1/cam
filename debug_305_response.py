"""
Debug script: call Claude Sonnet with the Step 305 prompt for 2 elements of LP-09
and print the raw response + what safe_json_extract returns.
"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from cam.core.config import find_and_load_env
find_and_load_env()

from cam.core.provider_router import ModelTarget, ProviderRouter, RouterConfig
from cam.core.json_extract import safe_json_extract
from cam.adapters.lease_review.lease_coverage_305 import _SYSTEM_PROMPT

MINI_ELEMENTS = [
    {
        "element_id": "LP-09.assignment_requires_landlord_consent",
        "element_label": "Assignment requires landlord consent",
        "synonyms": ["Tenant shall not assign this Lease without Landlord's prior written consent"],
        "must_be_explicit": True,
        "implicit_coverage_acceptable": False,
        "default_law_covers": False,
        "cross_LP_coverage": None,
        "absence_severity": "high",
    },
    {
        "element_id": "LP-09.affiliate_transfer_exception_defined",
        "element_label": "Affiliate transfer exception",
        "synonyms": ["assignment to an Affiliate"],
        "must_be_explicit": False,
        "implicit_coverage_acceptable": True,
        "default_law_covers": False,
        "cross_LP_coverage": None,
        "absence_severity": "low",
    },
]

USER_PROMPT = f"""LP: LP-09 -- Subletting & Assignment
GOVERNING LAW: Not specified

EXPECTED ELEMENTS (2 total):
{json.dumps(MINI_ELEMENTS, indent=2)}

LEASE PROVISION TEXT:
Tenant may not assign this Lease or sublet the Premises without Landlord's prior written consent.
Landlord shall not unreasonably withhold, condition, or delay consent. Affiliate assignments
are permitted without consent provided Tenant gives prior written notice.

Return a JSON array of exactly 2 verdict objects, one per element in the order listed above."""

target = ModelTarget(
    name="anthropic:claude-sonnet-4-6-debug-305",
    provider="anthropic",
    model="claude-sonnet-4-6",
    max_output_tokens=1000,
    temperature=0.0,
    timeout_sec=60.0,
)
router = ProviderRouter([target], RouterConfig())
adapter = router._get_adapter("anthropic")

print("Calling Claude Sonnet 4.6 with Step 305 prompt...")
raw = adapter.call(_SYSTEM_PROMPT, USER_PROMPT, target)
print(f"\n--- RAW RESPONSE (first 500 chars) ---\n{raw[:500]}")
print(f"\n--- RAW RESPONSE (last 200 chars) ---\n{raw[-200:]}")

parsed = safe_json_extract(raw.strip())
print(f"\n--- PARSED TYPE: {type(parsed).__name__} ---")
if isinstance(parsed, dict):
    print(f"Dict keys: {list(parsed.keys())}")
    for k, v in parsed.items():
        print(f"  [{k!r}] -> {type(v).__name__}: {str(v)[:100]}")
elif isinstance(parsed, list):
    print(f"List length: {len(parsed)}")
    if parsed:
        print(f"First item: {parsed[0]}")
else:
    print(f"Value: {parsed}")
