"""
CAM Lease Review — Stage Fallback Chain Helper

Shared utility for single-API-call pipeline stages (challenge, cascade, severity).
Each stage has a fallback chain: tries models in order, with 30s timeouts and
provider health tracking.
"""

import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from cam.core.provider_router import (
    ModelTarget,
    ProviderRouter,
    RouterConfig,
)
from cam.core.provider_health import get_health_tracker


# Default fallback chain for single-model stages — imported from central model config
# Note: mistral omitted — ProviderRouter does not support the 'mistral' provider string.
from cam.adapters.lease_review.model_config import SINGLE_STAGE_CHAIN  # noqa: E402

# Per-attempt timeout
STAGE_ATTEMPT_TIMEOUT = 300.0


def call_with_fallback(
    stage_name: str,
    system_prompt: str,
    user_prompt: str,
    validate_fn: Callable,
    chain: List[Tuple[str, str]] = None,
    max_output_tokens: int = 4000,
    reasoning_effort: str = None,
    timeout_sec: float = STAGE_ATTEMPT_TIMEOUT,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Call an API with a fallback chain across providers.

    Tries each provider/model in the chain. Skips degraded providers.
    Marks providers as degraded on provider-level failures.

    Args:
        stage_name: For logging, e.g. "lease_challenge"
        system_prompt: System prompt for the API call
        user_prompt: User prompt for the API call
        validate_fn: Schema validation function (obj) -> (ok, why)
        chain: List of (provider, model) tuples. Defaults to SINGLE_STAGE_CHAIN.
        max_output_tokens: Max output tokens
        reasoning_effort: Reasoning effort for models that support it (primary only)
        timeout_sec: Per-attempt timeout

    Returns:
        (parsed_json_obj, meta_dict) where meta includes model/provider used

    Raises:
        RuntimeError if all models in the chain fail
    """
    if chain is None:
        chain = SINGLE_STAGE_CHAIN

    health = get_health_tracker()
    errors = []
    start_time = time.time()

    for chain_idx, (provider, model_name) in enumerate(chain):
        # Skip degraded providers
        if not health.is_available(provider):
            print(f"[{stage_name}] Skipping {model_name} ({provider} degraded)", flush=True)
            errors.append({"model": model_name, "error": f"provider {provider} degraded"})
            continue

        target = ModelTarget(
            name=f"{provider}:{model_name}-{stage_name}",
            provider=provider,
            model=model_name,
            priority=chain_idx + 1,
            max_output_tokens=max_output_tokens,
            temperature=0.0,
            timeout_sec=timeout_sec,
            # Only use reasoning_effort for the primary model
            reasoning_effort=reasoning_effort if chain_idx == 0 else None,
        )

        router = ProviderRouter([target], RouterConfig(per_request_provider_attempt_cap=2))

        label = "primary" if chain_idx == 0 else "FALLBACK"
        print(f"[{stage_name}] calling {model_name} ({label})...", flush=True)

        try:
            obj, meta = router.call_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema_validate_fn=validate_fn,
                allowed_providers={provider},
            )
            elapsed = time.time() - start_time

            meta["fallback_used"] = chain_idx > 0
            meta["model"] = model_name
            meta["provider"] = provider
            meta["elapsed_sec"] = round(elapsed, 2)
            meta["chain_errors"] = errors

            print(f"[{stage_name}] {model_name} succeeded in {round(elapsed, 1)}s ({label})", flush=True)
            return obj, meta

        except Exception as e:
            error_str = str(e).lower()
            is_provider_error = any(k in error_str for k in [
                "503", "connection", "refused", "unavailable",
                "resource_exhausted",
            ])

            errors.append({"model": model_name, "error": str(e)})

            if is_provider_error:
                health.mark_degraded(provider, reason=str(e)[:100])

            elapsed_so_far = time.time() - start_time
            print(f"[{stage_name}] {model_name} FAILED ({type(e).__name__}, "
                  f"{round(elapsed_so_far, 1)}s elapsed)", flush=True)
            continue

    raise RuntimeError(f"[{stage_name}] All models failed: {errors}")
