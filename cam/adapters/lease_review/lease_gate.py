"""
CAM Lease Review — Document Type Gate

Runs a single lightweight API call to verify the tenant document is a
commercial lease before any expensive processing begins. If not a lease,
returns an abort signal with a user-friendly error message.
"""

import time
from cam.core.provider_router import ModelTarget

GATE_PROMPT = """You are a document classifier. You will be shown the beginning of a document.

Your ONLY task: determine whether this document is a commercial lease agreement.

A commercial lease agreement:
- Is a contract between a landlord and a tenant
- Grants the tenant the right to occupy a commercial property (retail, office, industrial, etc.)
- Contains provisions about rent, term, premises, and tenant obligations

Answer with ONLY one of these two words:
LEASE
NOT_LEASE

Do not explain. Do not add any other text. Just the single word."""


def check_document_is_lease(tenant_text: str, cfg: dict) -> dict:
    """
    Classify whether tenant_text is a commercial lease.

    Returns:
        {
            "is_lease": bool,
            "abort": bool,
            "abort_message": str or None,
            "elapsed_sec": float,
        }
    """
    start = time.time()

    # Use first 3000 chars — enough to classify, cheap to process
    sample = tenant_text[:3000].strip()

    user_prompt = f"DOCUMENT:\n\n{sample}"

    try:
        # Use fastest/cheapest available model for gate check
        # Step 508: was "claude-sonnet-4-20250514", which has been RETIRED and 404s
        # on every call. The except-block below is fail-open (`is_lease: True`), so the
        # gate has been a permanent no-op since that id was withdrawn -- every document
        # passed, including one that is not a lease. claude-haiku-4-5 is the cheapest
        # and fastest model already in the pipeline (role A's own-chain fallback), which
        # is exactly what the comment above asks for.
        gate_model = cfg.get("gate_model", "claude-haiku-4-5-20251001")
        gate_provider = cfg.get("gate_provider", "anthropic")
        gate_timeout = cfg.get("gate_timeout", 30.0)

        target = ModelTarget(
            name=f"{gate_provider}:{gate_model}-gate",
            provider=gate_provider,
            model=gate_model,
            priority=1,
            max_output_tokens=10,
            temperature=0.0,
            timeout_sec=gate_timeout,
        )

        # Use adapter directly — gate returns plain text, not JSON
        if gate_provider == "anthropic":
            from cam.core.provider_router import AnthropicAdapter
            adapter = AnthropicAdapter()
        elif gate_provider == "openai":
            from cam.core.provider_router import OpenAIAdapter
            adapter = OpenAIAdapter()
        elif gate_provider == "google":
            from cam.core.provider_router import GoogleGenAIAdapter
            adapter = GoogleGenAIAdapter()
        else:
            from cam.core.provider_router import AnthropicAdapter
            adapter = AnthropicAdapter()

        raw_text = adapter.call(GATE_PROMPT, user_prompt, target)

        raw = (raw_text or "").strip().upper()
        is_lease = raw.startswith("LEASE") and not raw.startswith("NOT_LEASE")

        elapsed = round(time.time() - start, 2)

        if is_lease:
            return {
                "is_lease": True,
                "abort": False,
                "abort_message": None,
                "elapsed_sec": elapsed,
            }
        else:
            return {
                "is_lease": False,
                "abort": True,
                "abort_message": (
                    "The uploaded document does not appear to be a commercial lease agreement. "
                    "Please check your file and upload a valid commercial lease."
                ),
                "elapsed_sec": elapsed,
            }

    except Exception as e:
        # Gate failure is non-fatal — log and proceed
        # Better to run and maybe produce imperfect results than to block valid leases
        elapsed = round(time.time() - start, 2)
        print(f"[lease_gate] Gate check failed (non-fatal): {e}", flush=True)
        return {
            "is_lease": True,  # Assume valid and proceed
            "abort": False,
            "abort_message": None,
            "elapsed_sec": elapsed,
            "gate_error": str(e),
        }
