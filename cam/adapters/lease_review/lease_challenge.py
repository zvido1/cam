"""
CAM Lease Review — Stage 3: Targeted Challenge

1 API call to GPT-5.2 (reasoning_effort=high) covering ONLY flagged provisions.
Skipped entirely if nothing is flagged.
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
from cam.adapters.lease_review.stage_fallback import call_with_fallback, SINGLE_STAGE_CHAIN

PROMPT_PATH = Path(__file__).parent / "prompts" / "challenge.txt"
SCHEMA_PATH = Path(__file__).parent / "schemas" / "challenge_schema.json"


def _load_prompt_template() -> str:
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()


def _compact_reasoning(text: str, max_chars: int = 260) -> str:
    """Prefer a complete first sentence over blunt mid-sentence truncation."""
    text = " ".join((text or "").split())
    if not text:
        return ""
    for punct in (". ", "! ", "? "):
        idx = text.find(punct)
        if 0 < idx + 1 <= max_chars:
            return text[: idx + 1].strip()
    if len(text) <= max_chars:
        return text
    clipped = text[:max_chars].rsplit(" ", 1)[0].strip()
    return clipped + "..."


def _build_flagged_provisions_text(
    flagged: List[dict],
    extraction_map: Dict[str, dict],
    evaluation_agg: Dict[str, dict],
    config: dict = None,
) -> str:
    """Build the challenge prompt text for flagged provisions."""
    config = config or {}
    template_defs = config.get("_template_definitions", "")
    tenant_defs = config.get("_tenant_definitions", "")

    parts = []
    for f in flagged:
        pid = f["provision_id"]
        ext = extraction_map.get(pid, {})
        agg = evaluation_agg.get(pid, {})

        tmpl = ext.get("template_text", "")
        tenant = ext.get("tenant_text", "")
        status = ext.get("status", "FOUND_BOTH")
        defn = ext.get("definition_changes", "")

        # Summarize evaluator findings
        verdicts = agg.get("verdicts", {})
        reasoning = agg.get("reasoning", {})
        pattern = agg.get("agreement_pattern", "unknown")

        evaluator_summary = f"Agreement: {pattern}\n"
        for key in ["A", "B", "C"]:
            v = verdicts.get(key, "?")
            r = _compact_reasoning(reasoning.get(key, ""))
            evaluator_summary += f"  Evaluator {key}: {v} — {r}\n"

        part = f"--- {pid}: {f.get('provision_name', pid)} ---\n"
        part += f"Status: {status}\n\n"
        part += f"TEMPLATE TEXT:\n{tmpl}\n\n"
        if status == "TEMPLATE_ONLY":
            part += "TENANT TEXT: [MISSING — provision not found in tenant lease]\n\n"
        else:
            part += f"TENANT TEXT:\n{tenant}\n\n"
        if defn:
            part += f"DEFINITION CHANGES: {defn}\n\n"
        part += f"EVALUATOR FINDINGS:\n{evaluator_summary}\n"

        # Add fragility signals if present
        frag = f.get("fragility", {})
        rule_ls_002_fired = False
        if frag.get("rules_fired"):
            part += "FRAGILITY SIGNALS:\n"
            for r in frag["rules_fired"]:
                part += f"  {r['rule_id']} ({r['signal']}): {r['details'][:120]}\n"
                if r["rule_id"] == "RULE-LS-002":
                    rule_ls_002_fired = True
            part += "\n"

        # Inject definition cascade context when RULE-LS-002 fired
        if rule_ls_002_fired and template_defs and tenant_defs:
            part += "DEFINITION CASCADE DETECTED:\n"
            part += f"Template definitions section:\n{template_defs[:1500]}\n\n"
            part += f"Tenant definitions section:\n{tenant_defs[:1500]}\n\n"
            part += "This provision references a changed defined term. Evaluate whether the redefinition materially alters this provision's meaning, rights, or obligations.\n\n"

        parts.append(part)

    return "\n".join(parts)


def _validate_challenge(obj: dict) -> Tuple[bool, Optional[str]]:
    if "challenges" not in obj:
        return False, "Missing 'challenges' key"
    if not isinstance(obj["challenges"], list):
        return False, "'challenges' must be an array"
    for i, ch in enumerate(obj["challenges"]):
        if "provision_id" not in ch:
            return False, f"challenges[{i}] missing 'provision_id'"
        if ch.get("challenge_verdict") not in ("SUBSTANTIVE_DEVIATION", "COSMETIC_ONLY", "NEEDS_EXPERT"):
            return False, f"challenges[{i}] invalid challenge_verdict: {ch.get('challenge_verdict')}"
    return True, None


MAX_PROVISIONS_PER_CHALLENGE = 8


def _challenge_batch(
    batch: List[dict],
    extraction_map: Dict[str, dict],
    evaluation_agg: Dict[str, dict],
    config: dict,
) -> Dict[str, Any]:
    """Challenge a single batch of flagged provisions using fallback chain."""
    prompt_template = _load_prompt_template()
    flagged_text = _build_flagged_provisions_text(batch, extraction_map, evaluation_agg, config)
    user_prompt = prompt_template.replace("{flagged_provisions}", flagged_text)

    system_prompt = (
        "You are a senior legal reviewer with expertise in commercial real estate law. "
        "Your role is to critically examine potential lease deviations and determine whether "
        "they represent real legal risk. Always respond with valid JSON only."
    )

    obj, meta = call_with_fallback(
        stage_name="lease_challenge",
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        validate_fn=_validate_challenge,
        max_output_tokens=config.get("challenge_max_tokens", 6000),
        reasoning_effort="high",
    )

    # Cancel check immediately after API return
    from cam.adapters.lease_review.lease_adapter import _check_cancel
    _check_cancel(config)

    return (
        {ch["provision_id"]: ch for ch in obj.get("challenges", [])},
        obj.get("challenges", []),
        {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
        },
    )


def challenge_provisions(
    flagged: List[dict],
    extraction_map: Dict[str, dict],
    evaluation_agg: Dict[str, dict],
    config: dict,
) -> Dict[str, Any]:
    """Run Stage 3: Targeted challenge on flagged provisions.

    If more than MAX_PROVISIONS_PER_CHALLENGE provisions are flagged,
    splits into batches to prevent GPT-5.2 empty output on large prompts.

    Args:
        flagged: List of flagged provision dicts (from triage).
        extraction_map: {provision_id: extraction_dict} from Stage 1.
        evaluation_agg: {provision_id: aggregated_eval} from Stage 2.
        config: Pipeline config.

    Returns:
        Dict with "challenges" (per-provision) and "meta".
    """
    if not flagged:
        return {"challenges": {}, "meta": {"skipped": True, "reason": "no_flagged_provisions"}}

    start_time = time.time()
    all_challenges = {}
    all_raw = []
    api_calls = 0
    challenge_prompts = {"system_prompt": None, "user_prompt": None}

    # Chunk into batches if needed
    for i in range(0, len(flagged), MAX_PROVISIONS_PER_CHALLENGE):
        batch = flagged[i:i + MAX_PROVISIONS_PER_CHALLENGE]
        batch_num = (i // MAX_PROVISIONS_PER_CHALLENGE) + 1
        if len(flagged) > MAX_PROVISIONS_PER_CHALLENGE:
            print(f"[lease_challenge] Batch {batch_num}: {len(batch)} provisions", flush=True)
        challenges, raw, prompts = _challenge_batch(batch, extraction_map, evaluation_agg, config)
        all_challenges.update(challenges)
        all_raw.extend(raw)
        api_calls += 1
        if batch_num == 1:
            challenge_prompts = prompts

    elapsed = time.time() - start_time

    return {
        "challenges": all_challenges,
        "raw_challenges": all_raw,
        "prompts": challenge_prompts if flagged else {"system_prompt": None, "user_prompt": None},
        "meta": {
            "elapsed_sec": round(elapsed, 2),
            "provisions_challenged": len(flagged),
            "api_calls": api_calls,
        },
    }
