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


# Maximum provisions per severity call — above this we chunk
SEVERITY_CHUNK_SIZE = 5


def assess_severity(
    confirmed_deviations: List[dict],
    extraction_map: Dict[str, dict],
    evaluation_agg: Dict[str, dict],
    challenge_results: Dict[str, dict],
    fragility_map: Dict[str, dict],
    config: dict,
) -> Dict[str, Any]:
    """Run Stage 5: Severity assessment on confirmed deviations.

    Chunks into batches of SEVERITY_CHUNK_SIZE when there are many deviations,
    to avoid output token overflow on large leases.

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

    # Split into chunks if needed
    chunks = [
        confirmed_deviations[i:i + SEVERITY_CHUNK_SIZE]
        for i in range(0, len(confirmed_deviations), SEVERITY_CHUNK_SIZE)
    ]
    needs_chunking = len(chunks) > 1
    if needs_chunking:
        print(f"[lease_severity] {len(confirmed_deviations)} deviations → {len(chunks)} chunks of ≤{SEVERITY_CHUNK_SIZE}", flush=True)

    prompt_template = _load_prompt_template()
    system_prompt = (
        "You are a commercial real estate legal expert assessing the severity of "
        "confirmed lease deviations. Be precise and practical in your severity ratings. "
        "Always respond with valid JSON only."
    )

    from cam.adapters.lease_review.lease_adapter import _check_cancel

    all_severities = []
    all_raw = []
    total_elapsed = 0.0
    last_meta = {}
    total_api_calls = 0

    start_time = time.time()

    for chunk_idx, chunk in enumerate(chunks):
        if needs_chunking:
            print(f"[lease_severity chunk {chunk_idx+1}/{len(chunks)}] {len(chunk)} provisions...", flush=True)

        details_text = _build_deviation_details(
            chunk, extraction_map, evaluation_agg, challenge_results, fragility_map
        )
        user_prompt = prompt_template.replace("{deviation_details}", details_text)

        chunk_start = time.time()
        obj, meta = call_with_fallback(
            stage_name="lease_severity",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            validate_fn=_validate_severity,
            max_output_tokens=config.get("severity_max_tokens", 4000),
            reasoning_effort="medium",
        )
        chunk_elapsed = time.time() - chunk_start
        total_elapsed += chunk_elapsed
        total_api_calls += 1
        last_meta = meta

        chunk_results = obj.get("severities", [])
        all_severities.extend(chunk_results)
        all_raw.extend(chunk_results)

        if needs_chunking:
            print(f"[lease_severity chunk {chunk_idx+1}/{len(chunks)}] {len(chunk_results)} severities in {chunk_elapsed:.1f}s", flush=True)

        # Cancel check between chunks
        _check_cancel(config)

    severities = {s["provision_id"]: s for s in all_severities}

    return {
        "severities": severities,
        "raw_severities": all_raw,
        "prompts": {
            "system_prompt": system_prompt,
            "user_prompt": "(chunked — see individual chunk prompts)",
        },
        "meta": {
            "model": last_meta.get("model", "unknown"),
            "provider": last_meta.get("provider", "unknown"),
            "elapsed_sec": round(total_elapsed, 2),
            "provisions_assessed": len(confirmed_deviations),
            "chunks": len(chunks),
            "api_calls": total_api_calls,
            "fallback_used": last_meta.get("fallback_used", False),
        },
    }
