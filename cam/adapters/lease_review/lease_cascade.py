"""
CAM Lease Review — Definition Cascade Micro-Stage

Runs ONLY when RULE-LS-002 fires on one or more provisions.
One focused API call to determine if a redefined term materially
changes each affected provision's legal effect.

0-1 API calls. Only invoked when cascade-flagged provisions exist.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from cam.core.provider_router import (
    ModelTarget,
    ProviderRouter,
    RouterConfig,
)
from cam.adapters.lease_review.stage_fallback import call_with_fallback

PROMPT_PATH = Path(__file__).parent / "prompts" / "cascade_evaluation.txt"


def _load_prompt_template() -> str:
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()


def _find_cascade_provisions(
    fragility_results: List[dict],
    extraction_provisions: List[dict],
) -> List[dict]:
    """Find provisions where RULE-LS-002 fired (definition override detected).

    Returns list of dicts with provision_id, provision info, and the changed terms
    referenced by that provision.
    """
    ext_map = {p["provision_id"]: p for p in extraction_provisions}
    cascade_provisions = []

    for frag in fragility_results:
        pid = frag["provision_id"]
        if not frag.get("fragile"):
            continue

        for rule in frag.get("rules_fired", []):
            if rule["rule_id"] == "RULE-LS-002":
                ext = ext_map.get(pid, {})
                # Extract which changed terms this provision references from rule details
                # Details format: "References changed defined terms: Affiliate, Base Rent"
                details = rule.get("details", "")
                terms = []
                if "References changed defined terms:" in details:
                    terms_str = details.split("References changed defined terms:")[-1].strip()
                    terms = [t.strip() for t in terms_str.split(",") if t.strip()]

                cascade_provisions.append({
                    "provision_id": pid,
                    "provision_name": ext.get("provision_name", pid),
                    "template_text": ext.get("template_text", ""),
                    "tenant_text": ext.get("tenant_text", ""),
                    "changed_terms_referenced": terms,
                    "rule_details": details,
                })
                break  # Only one RULE-LS-002 per provision

    return cascade_provisions


def _build_provisions_block(cascade_provisions: List[dict]) -> str:
    """Build the provisions text block for the cascade prompt."""
    parts = []
    for cp in cascade_provisions:
        part = f"--- {cp['provision_id']}: {cp['provision_name']} ---\n"
        part += f"Text: {cp['template_text'][:800]}\n"
        if cp["tenant_text"]:
            part += f"Tenant text: {cp['tenant_text'][:800]}\n"
        part += f"Changed term referenced: {', '.join(cp['changed_terms_referenced'])}\n"
        parts.append(part)
    return "\n".join(parts)


def _validate_cascade(obj: dict) -> Tuple[bool, Optional[str]]:
    """Validate cascade response structure."""
    if "cascades" not in obj:
        return False, "Missing 'cascades' key"
    if not isinstance(obj["cascades"], list):
        return False, "'cascades' must be an array"
    for i, c in enumerate(obj["cascades"]):
        if "provision_id" not in c:
            return False, f"cascades[{i}] missing 'provision_id'"
        if c.get("verdict") not in ("CASCADE_MATERIAL", "CASCADE_IMMATERIAL"):
            return False, f"cascades[{i}] invalid verdict: {c.get('verdict')}"
    return True, None


def evaluate_definition_cascades(
    fragility_results: List[dict],
    extraction_provisions: List[dict],
    template_definitions: str,
    tenant_definitions: str,
    changed_terms: List[str],
    config: dict,
) -> Dict[str, Any]:
    """Focused evaluation: does each redefined term materially change its provision?

    One API call covering all cascade-flagged provisions.
    Returns dict with per-provision CASCADE_MATERIAL or CASCADE_IMMATERIAL verdicts.

    Args:
        fragility_results: Stage 4 output (with rules_fired).
        extraction_provisions: Stage 1 output.
        template_definitions: Full definitions section from template.
        tenant_definitions: Full definitions section from tenant.
        changed_terms: Pre-computed list of changed defined terms.
        config: Pipeline configuration.

    Returns:
        Dict with "cascades" (provision_id -> cascade_dict) and "meta".
    """
    # Find provisions where RULE-LS-002 fired
    cascade_provisions = _find_cascade_provisions(fragility_results, extraction_provisions)

    if not cascade_provisions:
        return {
            "cascades": {},
            "meta": {"skipped": True, "reason": "no_cascade_provisions"},
        }

    # Build the prompt
    prompt_template = _load_prompt_template()
    provisions_block = _build_provisions_block(cascade_provisions)

    user_prompt = prompt_template.replace("{template_definitions}", template_definitions[:2000])
    user_prompt = user_prompt.replace("{tenant_definitions}", tenant_definitions[:2000])
    user_prompt = user_prompt.replace("{changed_terms}", ", ".join(changed_terms))
    user_prompt = user_prompt.replace("{provisions_block}", provisions_block)

    system_prompt = (
        "You are a legal analyst specializing in lease term analysis. "
        "Your task is to evaluate whether changes to defined terms materially "
        "affect specific lease provisions. Always respond with valid JSON only."
    )

    start_time = time.time()

    obj, meta = call_with_fallback(
        stage_name="lease_cascade",
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        validate_fn=_validate_cascade,
        max_output_tokens=config.get("cascade_max_tokens", 3000),
        reasoning_effort="high",
    )

    # Cancel check immediately after API return
    from cam.adapters.lease_review.lease_adapter import _check_cancel
    _check_cancel(config)

    elapsed = time.time() - start_time

    # Build lookup: provision_id -> cascade result
    cascades = {}
    for c in obj.get("cascades", []):
        cascades[c["provision_id"]] = c

    return {
        "cascades": cascades,
        "raw_cascades": obj.get("cascades", []),
        "meta": {
            "model": meta.get("model", "unknown"),
            "provider": meta.get("provider", "unknown"),
            "elapsed_sec": round(elapsed, 2),
            "provisions_evaluated": len(cascade_provisions),
            "api_calls": 1,
            "fallback_used": meta.get("fallback_used", False),
        },
    }
