"""
CAM Lease Review — Stage 2: Multi-Evaluator Assessment

3 parallel API calls (one per evaluator model). Each evaluator assesses
ALL provisions in a single call using cached text from Stage 1.

Evaluators are blind to each other's outputs (CAM invariant).
Evaluators MUST commit to a verdict (no abstention — CAM invariant).

Provider dedup: No two evaluators may use the same provider in the same run.
Fallback chains are staggered to minimize collisions, and a shared
claimed-providers set prevents duplicates at runtime.
"""

import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from cam.core.provider_router import (
    ModelTarget,
    ProviderRouter,
    RouterConfig,
)
from cam.core.provider_health import get_health_tracker
from cam.core.json_extract import safe_json_extract

PROMPT_PATH = Path(__file__).parent / "prompts" / "evaluation.txt"
SCHEMA_PATH = Path(__file__).parent / "schemas" / "evaluation_schema.json"

# Per-attempt timeout for evaluator API calls
EVALUATOR_ATTEMPT_TIMEOUT = 300.0

# Evaluator model definitions — model strings from central model_config.
# To change a model, edit model_config.py only.
#
# Each evaluator has a primary model and a same-provider fallback.
# When all own-provider models fail, draws from shared fallback pool.
#
# Own-provider chains:
#   A: claude-sonnet-4-6  → claude-sonnet-4
#   B: gpt-5.2            → gpt-4o
#   C: grok-4             → grok-3
#
# Shared fallback pool: [gemini-3.1-pro-preview, mistral-large-latest]
#
# Note: mistral uses a direct OpenAI-compatible call (see _call_mistral_direct)
# because ProviderRouter does not support the "mistral" provider string.
from cam.adapters.lease_review.model_config import (  # noqa: E402
    EVALUATOR_A_PRIMARY, EVALUATOR_A_FALLBACK,
    EVALUATOR_B_PRIMARY, EVALUATOR_B_FALLBACK,
    EVALUATOR_C_PRIMARY, EVALUATOR_C_FALLBACK,
    EXTRACTOR_PRIMARY,
)

EVALUATORS = {
    "A": {
        "name": f"{EVALUATOR_A_PRIMARY[0]}:{EVALUATOR_A_PRIMARY[1]}",
        "provider": EVALUATOR_A_PRIMARY[0],
        "model": EVALUATOR_A_PRIMARY[1],
        "label": "Claude Sonnet 4.6",
        "max_output_tokens": 8000,
        "temperature": 0.0,
        "timeout_sec": EVALUATOR_ATTEMPT_TIMEOUT,
        "own_chain": [
            (EVALUATOR_A_FALLBACK[0], EVALUATOR_A_FALLBACK[1], "Claude Sonnet 4"),
        ],
    },
    "B": {
        "name": f"{EVALUATOR_B_PRIMARY[0]}:{EVALUATOR_B_PRIMARY[1]}",
        "provider": EVALUATOR_B_PRIMARY[0],
        "model": EVALUATOR_B_PRIMARY[1],
        "label": "GPT-5.2 (medium)",
        "max_output_tokens": 8000,
        "temperature": 0.0,
        "timeout_sec": EVALUATOR_ATTEMPT_TIMEOUT,
        "reasoning_effort": "medium",
        "own_chain": [
            (EVALUATOR_B_FALLBACK[0], EVALUATOR_B_FALLBACK[1], "GPT-4o"),
        ],
    },
    "C": {
        "name": f"{EVALUATOR_C_PRIMARY[0]}:{EVALUATOR_C_PRIMARY[1]}",
        "provider": EVALUATOR_C_PRIMARY[0],
        "model": EVALUATOR_C_PRIMARY[1],
        "label": "Grok 4",
        "max_output_tokens": 8000,
        "temperature": 0.0,
        "timeout_sec": EVALUATOR_ATTEMPT_TIMEOUT,
        "own_chain": [
            (EVALUATOR_C_FALLBACK[0], EVALUATOR_C_FALLBACK[1], "Grok 3"),
        ],
    },
}

# Shared fallback pool — claimed dynamically across evaluators.
# First evaluator to exhaust its own provider gets gemini; second gets mistral.
# Order matters: gemini first (faster), mistral second.
_SHARED_FALLBACK_POOL = [
    ("google",   "gemini-2.5-pro",       "Gemini 2.5 Pro"),
    ("mistral",  "mistral-large-latest", "Mistral Large"),
]
_pool_lock = threading.Lock()
_pool_claimed: list = []   # list of provider strings already claimed from pool


def _claim_from_shared_pool() -> tuple:
    """Claim the next unclaimed entry from the shared fallback pool.
    Returns (provider, model, label) or None if pool exhausted."""
    with _pool_lock:
        for entry in _SHARED_FALLBACK_POOL:
            provider = entry[0]
            if provider not in _pool_claimed:
                _pool_claimed.append(provider)
                return entry
    return None


def _release_pool_claim(provider: str) -> None:
    """Release a pool claim (called when a pool fallback also fails)."""
    with _pool_lock:
        if provider in _pool_claimed:
            _pool_claimed.remove(provider)

# Shared set of providers claimed by evaluators in this round (thread-safe)
_claimed_providers: Set[str] = set()
_claimed_lock = threading.Lock()


def _load_prompt_template() -> str:
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()


def _load_schema() -> dict:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _build_provision_pairs(provisions: List[dict]) -> str:
    """Format provision pairs for the evaluator prompt."""
    parts = []
    for p in provisions:
        pid = p["provision_id"]
        pname = p.get("provision_name", pid)
        status = p.get("status", "FOUND_BOTH")
        tmpl = p.get("template_text", "")
        tenant = p.get("tenant_text", "")
        defn_change = p.get("definition_changes", "")

        part = f"--- {pid}: {pname} (status: {status}) ---\n"
        if pid.startswith("ADDED-") or (pid.startswith("CUSTOM-") and not tmpl.strip()):
            # Tenant-only clause — no template baseline to compare against.
            # ADDED- = tenant inserted clause not in template at all.
            # CUSTOM- with blank template = non-standard clause found in tenant lease;
            #   extraction found no corresponding text in the template.
            part += f"TEMPLATE TEXT: [NOT PRESENT IN TEMPLATE — clause exists in tenant lease only]\n\n"
            part += f"TENANT TEXT:\n{tenant}\n"
            part += "\nNOTE: This clause does not appear in the landlord's standard template. "
            part += "Evaluate whether it materially favors the tenant at the landlord's expense, "
            part += "or whether it imposes obligations or restrictions on the landlord not present in the template.\n"
        elif status == "TEMPLATE_ONLY":
            part += f"TEMPLATE TEXT:\n{tmpl}\n\nTENANT TEXT: [MISSING — provision not found in tenant lease]\n"
        elif status == "AMBIGUOUS":
            part += f"TEMPLATE TEXT:\n{tmpl}\n\nTENANT TEXT: [AMBIGUOUS — location uncertain]\n{tenant}\n"
        else:
            part += f"TEMPLATE TEXT:\n{tmpl}\n\nTENANT TEXT:\n{tenant}\n"
        if defn_change:
            part += f"\nDEFINITION CHANGES: {defn_change}\n"
        parts.append(part)
    return "\n".join(parts)


def _validate_evaluation(obj: dict) -> Tuple[bool, Optional[str]]:
    """Basic structural validation."""
    if "evaluations" not in obj:
        return False, "Missing 'evaluations' key"
    if not isinstance(obj["evaluations"], list):
        return False, "'evaluations' must be an array"
    for i, ev in enumerate(obj["evaluations"]):
        if "provision_id" not in ev:
            return False, f"evaluations[{i}] missing 'provision_id'"
        if ev.get("verdict") not in ("CONFORMS", "DEVIATES", "UNCLEAR"):
            return False, f"evaluations[{i}] invalid verdict: {ev.get('verdict')}"
    return True, None


def _try_claim_provider(provider: str) -> bool:
    """Attempt to claim a provider for this evaluator. Returns True if claimed."""
    with _claimed_lock:
        if provider in _claimed_providers:
            return False
        _claimed_providers.add(provider)
        return True


def _call_mistral_direct(
    evaluator_key: str,
    model_name: str,
    system_prompt: str,
    user_prompt: str,
    max_output_tokens: int,
    timeout_sec: float,
) -> str:
    """Call Mistral directly via its OpenAI-compatible API.

    ProviderRouter does not support 'mistral' as a provider string, so mistral
    fallback calls are made here using the openai SDK with mistral's base URL.
    Raises ProviderError if MISTRAL_API_KEY is absent or the call fails.
    """
    from cam.core.provider_router import ProviderError
    from openai import OpenAI

    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise ProviderError("MISTRAL_API_KEY not set — mistral fallback unavailable")

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.mistral.ai/v1",
        timeout=timeout_sec,
    )
    resp = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
        max_tokens=max_output_tokens,
    )
    return (resp.choices[0].message.content or "").strip()


def _call_evaluator(
    evaluator_key: str,
    evaluator_cfg: dict,
    provision_pairs_str: str,
    config: dict,
) -> Dict[str, Any]:
    """Call a single evaluator with fallback chain and provider dedup.

    Tries the primary provider first, then falls back through the chain.
    Skips providers that are degraded or already claimed by another evaluator.
    """
    health = get_health_tracker()
    prompt_template = _load_prompt_template()
    user_prompt = prompt_template.replace("{provision_pairs}", provision_pairs_str)

    system_prompt = (
        "You are a legal analyst evaluating commercial lease provisions for conformity "
        "with a standard template. You are thorough and precise. "
        "Always respond with valid JSON only."
    )

    # Inject user-defined rules (Step 140)
    try:
        import hashlib as _hashlib
        _rules_path = Path(__file__).parent.parent.parent.parent / "05 Lease Analyzer" / "data" / "user_rules.json"
        _access_code = config.get("access_code", "")
        if _access_code and _rules_path.exists():
            _code_hash = _hashlib.sha256(_access_code.encode()).hexdigest()
            _all_rules = json.loads(_rules_path.read_text())
            _user_rules = [r for r in _all_rules.get(_code_hash, []) if r.get("enabled")]
            if _user_rules:
                _rules_text = "\n".join(f"- {r['text']}" for r in _user_rules)
                system_prompt += f"\n\nUSER-DEFINED EVALUATION RULES (apply these when relevant):\n{_rules_text}"
    except Exception:
        pass

    # Build own-provider candidate list: primary + same-provider secondary
    own_candidates = [
        (evaluator_cfg["provider"], evaluator_cfg["model"], evaluator_cfg["label"]),
    ]
    for entry in evaluator_cfg.get("own_chain", []):
        own_candidates.append(entry)

    start_time = time.time()
    errors = []
    own_provider_exhausted = False

    def _try_one(provider, model_name, label, is_primary_provider):
        """Attempt a single model call. Returns result dict on success, raises on failure."""
        if not health.is_available(provider):
            raise RuntimeError(f"provider {provider} degraded, skipped")

        if not _try_claim_provider(provider):
            raise RuntimeError(f"provider {provider} already claimed by another evaluator")

        is_own = is_primary_provider
        tier = "own" if is_own else "POOL FALLBACK"
        print(f"[lease_evaluate] Evaluator {evaluator_key}: calling {model_name} ({tier})...", flush=True)

        try:
            if provider == "mistral":
                max_out = min(evaluator_cfg.get("max_output_tokens", 8000), 32_000)
                raw = _call_mistral_direct(
                    evaluator_key=evaluator_key,
                    model_name=model_name,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_output_tokens=max_out,
                    timeout_sec=evaluator_cfg.get("timeout_sec", EVALUATOR_ATTEMPT_TIMEOUT),
                )
                obj = safe_json_extract(raw)
                if obj is None:
                    raise ValueError("safe_json_extract returned None for mistral response")
                ok, why = _validate_evaluation(obj)
                if not ok:
                    raise ValueError(f"Mistral response failed validation: {why}")
                meta = {"provider": "mistral", "model": model_name}
            else:
                target = ModelTarget(
                    name=f"{provider}:{model_name}-eval-{evaluator_key}",
                    provider=provider,
                    model=model_name,
                    priority=1,
                    max_output_tokens=evaluator_cfg.get("max_output_tokens", 8000),
                    temperature=evaluator_cfg.get("temperature", 0.0),
                    timeout_sec=evaluator_cfg.get("timeout_sec", EVALUATOR_ATTEMPT_TIMEOUT),
                    reasoning_effort=evaluator_cfg.get("reasoning_effort") if is_own else None,
                )
                router = ProviderRouter([target], RouterConfig(per_request_provider_attempt_cap=2))
                obj, meta = router.call_json(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    schema_validate_fn=_validate_evaluation,
                    allowed_providers={provider},
                )

            from cam.adapters.lease_review.lease_adapter import _check_cancel
            _check_cancel(config)

            elapsed = time.time() - start_time
            return {
                "evaluator": evaluator_key,
                "label": label,
                "model": model_name,
                "provider": provider,
                "evaluations": {ev["provision_id"]: ev for ev in obj.get("evaluations", [])},
                "raw_evaluations": obj.get("evaluations", []),
                "discovered_clauses": obj.get("discovered_clauses", []),
                "elapsed_sec": round(elapsed, 2),
                "meta": meta,
                "fallback_used": not is_own,
            }

        except Exception:
            # Release claim on failure so other evaluators aren't blocked
            with _claimed_lock:
                _claimed_providers.discard(provider)
            raise

    # Phase 1: try own-provider candidates
    for cand_idx, (provider, model_name, label) in enumerate(own_candidates):
        try:
            result = _try_one(provider, model_name, label, is_primary_provider=True)
            fb_note = " (own-chain fallback)" if cand_idx > 0 else ""
            print(f"[lease_evaluate] Evaluator {evaluator_key} ({label}) succeeded in "
                  f"{result['elapsed_sec']}s{fb_note}", flush=True)
            return result
        except Exception as e:
            error_str = str(e).lower()
            is_provider_error = any(k in error_str for k in [
                "503", "connection", "refused", "unavailable", "resource_exhausted",
            ])
            if is_provider_error:
                health.mark_degraded(provider, reason=str(e)[:100])
            errors.append({"model": model_name, "error": str(e)})
            print(f"[lease_evaluate] Evaluator {evaluator_key}: {model_name} FAILED: {e}", flush=True)

    own_provider_exhausted = True
    print(f"[lease_evaluate] Evaluator {evaluator_key}: own provider exhausted, claiming from shared pool", flush=True)

    # Phase 2: claim from shared fallback pool (first-come-first-served)
    while True:
        pool_entry = _claim_from_shared_pool()
        if pool_entry is None:
            break  # pool exhausted
        provider, model_name, label = pool_entry
        try:
            result = _try_one(provider, model_name, label, is_primary_provider=False)
            print(f"[lease_evaluate] Evaluator {evaluator_key} ({label}) succeeded via pool in "
                  f"{result['elapsed_sec']}s", flush=True)
            return result
        except Exception as e:
            error_str = str(e).lower()
            is_provider_error = any(k in error_str for k in [
                "503", "connection", "refused", "unavailable", "resource_exhausted",
            ])
            if is_provider_error:
                health.mark_degraded(provider, reason=str(e)[:100])
            # Release pool claim so it's not permanently consumed by a failure
            _release_pool_claim(provider)
            errors.append({"model": model_name, "error": str(e)})
            print(f"[lease_evaluate] Evaluator {evaluator_key}: pool model {model_name} FAILED: {e}", flush=True)

    # All candidates exhausted
    raise RuntimeError(
        f"Evaluator {evaluator_key} failed on all candidates (own + pool): {errors}"
    )


def evaluate_provisions(
    extraction_provisions: List[dict],
    config: dict,
) -> Dict[str, Any]:
    """Run Stage 2: Multi-evaluator assessment on all provisions.

    Calls 3 evaluators in parallel. Each evaluator assesses all provisions.
    Uses fallback chains with provider dedup — no two evaluators use the same provider.

    Degraded mode:
    - 3/3 succeed → normal pipeline
    - 2/3 succeed → proceed with warning, triage/agreement works with 2
    - 1/3 or 0/3 → fail the pipeline with clear error

    Returns:
        Dict with:
            "evaluators": {A: {...}, B: {...}, C: {...}} — per-evaluator results
            "aggregated": [{provision_id, verdicts, agreement_pattern, ...}] — aggregated
            "meta": timing and call info
    """
    global _claimed_providers

    provision_pairs_str = _build_provision_pairs(extraction_provisions)

    stage_start = time.time()
    evaluator_results = {}

    # Reset claimed providers and shared pool for this evaluation round
    with _claimed_lock:
        _claimed_providers = set()
    with _pool_lock:
        _pool_claimed.clear()

    # Run evaluators in parallel
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {}
        for key, cfg in EVALUATORS.items():
            future = executor.submit(_call_evaluator, key, cfg, provision_pairs_str, config)
            futures[future] = key

        for future in as_completed(futures):
            key = futures[future]
            try:
                result = future.result()
                evaluator_results[key] = result
                fb_note = " (FALLBACK)" if result.get("fallback_used") else ""
                print(f"[lease_evaluate] Evaluator {key} ({result['label']}) complete in {result['elapsed_sec']}s{fb_note}", flush=True)
            except Exception as e:
                print(f"[lease_evaluate] Evaluator {key} FAILED (all fallbacks exhausted): {e}", flush=True)
                evaluator_results[key] = {
                    "evaluator": key,
                    "label": EVALUATORS[key]["label"],
                    "model": EVALUATORS[key]["model"],
                    "provider": EVALUATORS[key]["provider"],
                    "evaluations": {},
                    "raw_evaluations": [],
                    "elapsed_sec": 0,
                    "error": str(e),
                }

    # Check evaluator count
    succeeded = sum(1 for r in evaluator_results.values() if "error" not in r)
    failed_keys = [k for k, r in evaluator_results.items() if "error" in r]

    if succeeded < 2:
        raise RuntimeError(
            f"Only {succeeded}/3 evaluators succeeded (need at least 2). "
            f"Failed: {failed_keys}. Check provider availability."
        )

    if succeeded == 2:
        print(f"[lease_evaluate] WARNING: Proceeding with 2/3 evaluators (degraded mode). "
              f"Failed: {failed_keys}", flush=True)

    # Aggregate results
    aggregated = _aggregate_evaluations(extraction_provisions, evaluator_results)

    # Collect per-evaluator discoveries
    all_discoveries = {}
    for key, ev_result in evaluator_results.items():
        if "error" not in ev_result:
            all_discoveries[key] = ev_result.get("discovered_clauses", [])

    # Step 189: verify evidence_basis citations against actual clause texts
    from cam.adapters.lease_review.lease_citation_verifier import verify_all_evidence_bases
    verify_all_evidence_bases(
        aggregated_provisions=aggregated,
        extraction_provisions=extraction_provisions,
        evaluator_results=evaluator_results,
    )

    stage_elapsed = time.time() - stage_start
    return {
        "evaluators": evaluator_results,
        "aggregated": aggregated,
        "all_discoveries": all_discoveries,
        "meta": {
            "total_elapsed_sec": round(stage_elapsed, 2),
            "api_calls": succeeded,
            "evaluator_count": succeeded,
            "degraded": succeeded < 3,
        },
    }


def _aggregate_evaluations(
    provisions: List[dict],
    evaluator_results: Dict[str, dict],
) -> List[dict]:
    """Aggregate evaluator verdicts per provision.

    Handles degraded mode (2/3 evaluators) gracefully — skips evaluators
    that have no data (error'd out).
    """
    # Determine which evaluators actually succeeded
    active_keys = [k for k in ["A", "B", "C"] if "error" not in evaluator_results.get(k, {"error": True})]

    aggregated = []
    for prov in provisions:
        pid = prov["provision_id"]
        verdicts = {}
        reasoning = {}
        confidences = {}

        evidence_bases_raw = {}
        for key in ["A", "B", "C"]:
            evals = evaluator_results.get(key, {}).get("evaluations", {})
            ev = evals.get(pid, {})
            if key in active_keys:
                verdicts[key] = ev.get("verdict", "UNCLEAR")
                reasoning[key] = ev.get("reasoning", "")
                confidences[key] = ev.get("confidence", 0.0)
                evidence_bases_raw[key] = ev.get("evidence_basis", "structural_inference")
            else:
                # Evaluator failed — mark as absent
                verdicts[key] = None
                reasoning[key] = "(evaluator unavailable)"
                confidences[key] = 0.0
                evidence_bases_raw[key] = None

        # Compute agreement pattern using only active evaluators
        active_verdicts = {k: v for k, v in verdicts.items() if v is not None}
        verdict_counts = {}
        for v in active_verdicts.values():
            verdict_counts[v] = verdict_counts.get(v, 0) + 1

        num_active = len(active_verdicts)
        if num_active == 0:
            majority_verdict = "UNCLEAR"
            pattern = "no evaluators"
        elif len(verdict_counts) == 1:
            majority_verdict = list(verdict_counts.keys())[0]
            pattern = f"{num_active}-0 {majority_verdict}"
        elif max(verdict_counts.values()) >= 2:
            majority_verdict = max(verdict_counts, key=verdict_counts.get)
            minority_count = num_active - max(verdict_counts.values())
            pattern = f"{max(verdict_counts.values())}-{minority_count} {majority_verdict}"
        elif num_active == 2:
            # 2 active, split 1-1
            majority_verdict = "UNCLEAR"
            pattern = "1-1 split"
        else:
            majority_verdict = "UNCLEAR"
            pattern = "3-way split"

        aggregated.append({
            "provision_id": pid,
            "provision_name": prov.get("provision_name", pid),
            "verdicts": verdicts,
            "confidences": confidences,
            "reasoning": reasoning,
            "majority_verdict": majority_verdict,
            "agreement_pattern": pattern,
            "key_differences": {
                key: evaluator_results.get(key, {}).get("evaluations", {}).get(pid, {}).get("key_differences", [])
                for key in ["A", "B", "C"]
            },
            "risk_assessments": {
                key: evaluator_results.get(key, {}).get("evaluations", {}).get(pid, {}).get("risk_assessment", "")
                for key in ["A", "B", "C"]
            },
            "evidence_bases_raw": evidence_bases_raw,
        })

    return aggregated
