"""
CAM Lease Review — Stage 5: Severity Assessment

0-1 API calls. Only runs on provisions confirmed as deviating by Stage 3.
Skipped entirely if no deviations survive challenge.
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

PROMPT_PATH = Path(__file__).parent / "prompts" / "severity.txt"
SCHEMA_PATH = Path(__file__).parent / "schemas" / "severity_schema.json"


def _load_prompt_template() -> str:
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()


def _build_deviation_details(
    confirmed: List[dict],
    extraction_map: Dict[str, dict],
    evaluation_agg: Dict[str, dict],
    challenge_results: Dict[str, dict],
    fragility_map: Dict[str, dict],
) -> str:
    """Build severity prompt text for confirmed deviations."""
    parts = []
    for prov in confirmed:
        pid = prov["provision_id"]
        ext = extraction_map.get(pid, {})
        agg = evaluation_agg.get(pid, {})
        ch = challenge_results.get(pid, {})
        frag = fragility_map.get(pid, {})

        part = f"--- {pid}: {prov.get('provision_name', pid)} ---\n"
        part += f"TEMPLATE TEXT:\n{ext.get('template_text', '')}\n\n"
        part += f"TENANT TEXT:\n{ext.get('tenant_text', '')}\n\n"

        defn = ext.get("definition_changes", "")
        if defn:
            part += f"DEFINITION CHANGES: {defn}\n\n"

        part += f"EVALUATOR AGREEMENT: {agg.get('agreement_pattern', 'unknown')}\n"
        for key in ["A", "B", "C"]:
            v = agg.get("verdicts", {}).get(key, "?")
            part += f"  Evaluator {key}: {v}\n"

        part += f"\nCHALLENGE FINDING: {ch.get('challenge_verdict', 'N/A')}\n"
        part += f"  {ch.get('substantive_finding', '')}\n"
        if ch.get("hidden_dependencies"):
            part += f"  Hidden dependencies: {', '.join(ch['hidden_dependencies'])}\n"

        if frag.get("rules_fired"):
            part += "\nFRAGILITY SIGNALS:\n"
            for r in frag["rules_fired"]:
                part += f"  {r['rule_id']} ({r['signal']}): {r['details'][:100]}\n"

        part += "\n"
        parts.append(part)

    return "\n".join(parts)


def _validate_severity(obj: dict) -> Tuple[bool, Optional[str]]:
    if "severities" not in obj:
        return False, "Missing 'severities' key"
    if not isinstance(obj["severities"], list):
        return False, "'severities' must be an array"
    for i, s in enumerate(obj["severities"]):
        if "provision_id" not in s:
            return False, f"severities[{i}] missing 'provision_id'"
        if s.get("severity") not in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
            return False, f"severities[{i}] invalid severity: {s.get('severity')}"
    return True, None


def assess_severity(
    confirmed_deviations: List[dict],
    extraction_map: Dict[str, dict],
    evaluation_agg: Dict[str, dict],
    challenge_results: Dict[str, dict],
    fragility_map: Dict[str, dict],
    config: dict,
) -> Dict[str, Any]:
    """Run Stage 5: Severity assessment on confirmed deviations.

    Args:
        confirmed_deviations: List of provision dicts confirmed as substantive deviations.
        extraction_map: {provision_id: extraction_dict} from Stage 1.
        evaluation_agg: {provision_id: aggregated_eval} from Stage 2.
        challenge_results: {provision_id: challenge_dict} from Stage 3.
        fragility_map: {provision_id: fragility_dict} from Stage 4.
        config: Pipeline config.

    Returns:
        Dict with "severities" (per-provision) and "meta".
    """
    if not confirmed_deviations:
        return {"severities": {}, "meta": {"skipped": True, "reason": "no_confirmed_deviations"}}

    prompt_template = _load_prompt_template()
    details_text = _build_deviation_details(
        confirmed_deviations, extraction_map, evaluation_agg, challenge_results, fragility_map
    )
    user_prompt = prompt_template.replace("{deviation_details}", details_text)

    system_prompt = (
        "You are a commercial real estate legal expert assessing the severity of "
        "confirmed lease deviations. Be precise and practical in your severity ratings. "
        "Always respond with valid JSON only."
    )

    start_time = time.time()
    obj, meta = call_with_fallback(
        stage_name="lease_severity",
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        validate_fn=_validate_severity,
        max_output_tokens=config.get("severity_max_tokens", 4000),
        reasoning_effort="high",
    )

    # Cancel check immediately after API return
    from cam.adapters.lease_review.lease_adapter import _check_cancel
    _check_cancel(config)

    elapsed = time.time() - start_time

    severities = {s["provision_id"]: s for s in obj.get("severities", [])}

    return {
        "severities": severities,
        "raw_severities": obj.get("severities", []),
        "meta": {
            "model": meta.get("model", "unknown"),
            "provider": meta.get("provider", "unknown"),
            "elapsed_sec": round(elapsed, 2),
            "provisions_assessed": len(confirmed_deviations),
            "api_calls": 1,
            "fallback_used": meta.get("fallback_used", False),
        },
    }
