"""
CAM Lease Review — Template Summary Reader

Extracts key identifying fields from a lease document using a single
lightweight API call. Used to populate the template summary card in the UI.
"""

import json
from cam.core.provider_router import AnthropicAdapter, ModelTarget

READER_PROMPT = """You are extracting key fields from a commercial lease agreement.

Extract ONLY these fields:
- landlord: Full legal name of the landlord/lessor entity
- property: Property name and address (combine name + address into one string)
- base_rent: Base rent amount and frequency (e.g. "$4,200/month"). If the rent amount is a blank placeholder (like "$______" or "__________"), return the string "[blank]". Return empty string only if rent is not mentioned at all.
- lease_term: The DURATION of the lease (e.g. "5 years", "36 months"). Look for phrases like "five (5) years", "three (3) years", etc. Extract the duration even if the exact start or end dates are blank placeholders. If the term duration is a blank placeholder, return "[blank]". Return empty string only if no duration is mentioned at all.
- governing_law: Governing state or jurisdiction, or empty string

Respond ONLY with a JSON object. No other text.
Example: {"landlord":"Meridian Commercial Properties LLC","property":"Meridian Town Center, 4500 Commerce Boulevard","base_rent":"$4,200/month","lease_term":"5 years","governing_law":"State of Columbia"}"""


def read_template_summary(text: str) -> dict:
    """Extract summary fields from lease text. Returns dict with 5 string fields."""
    sample = text[:12000]

    empty = {"landlord": "", "property": "", "base_rent": "",
             "lease_term": "", "governing_law": ""}

    try:
        target = ModelTarget(
            name="anthropic:claude-sonnet",
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            timeout_sec=30.0,
            max_output_tokens=200,
            temperature=0.0,
        )

        adapter = AnthropicAdapter()
        raw = adapter.call(
            system_prompt=READER_PROMPT,
            user_prompt=f"LEASE DOCUMENT:\n\n{sample}",
            target=target,
        ).strip()

        # Strip any markdown fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        result = json.loads(raw.strip())
        # Ensure all keys present
        for k in empty:
            if k not in result:
                result[k] = ""
        return result

    except Exception as e:
        print(f"[lease_template_reader] Failed (non-fatal): {e}", flush=True)
        return empty
