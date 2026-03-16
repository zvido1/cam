"""
CAM Lease Review — Stage 1: Provision Extraction & Alignment

One Gemini API call that:
1. Takes both documents (template + tenant) in full
2. Takes the list of provisions to check
3. Extracts relevant clause text from each document per provision
4. Aligns them side by side
5. Notes if a provision is missing or differs

Uses cam/core/provider_router.py for the API call.
Uses cam/core/schema_validator.py for output validation.
Uses cam/core/json_extract.py for parsing model responses.
"""

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from cam.core.provider_router import (
    GoogleGenAIAdapter,
    ModelTarget,
    ProviderRouter,
    RouterConfig,
    ProviderError,
)
from cam.core.json_extract import safe_json_extract
from cam.core.provider_health import get_health_tracker

# Schema path for validation
SCHEMA_PATH = Path(__file__).parent / "schemas" / "extraction_schema.json"
PROMPT_PATH = Path(__file__).parent / "prompts" / "provision_extraction.txt"


def _load_schema() -> dict:
    """Load the extraction output JSON schema."""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_prompt_template() -> str:
    """Load the provision extraction prompt template."""
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()


def _build_provision_list(provisions: List[dict]) -> str:
    """Format the provision list for the prompt."""
    lines = []
    for p in provisions:
        hints = ", ".join(p.get("search_hints", []))
        lines.append(
            f"- {p['id']}: {p['name']}\n"
            f"  Description: {p['description']}\n"
            f"  Search hints: {hints}"
        )
    return "\n".join(lines)


def _validate_extraction(obj: dict) -> Tuple[bool, Optional[str]]:
    """Validate extraction output against schema."""
    try:
        import jsonschema
        schema = _load_schema()
        jsonschema.validate(instance=obj, schema=schema)
        return True, None
    except ImportError:
        # jsonschema not available — basic validation only
        pass
    except Exception as e:
        return False, str(e)

    # Basic structural validation if jsonschema is not available
    if "provisions" not in obj:
        return False, "Missing 'provisions' key"
    if not isinstance(obj["provisions"], list):
        return False, "'provisions' must be an array"
    for i, p in enumerate(obj["provisions"]):
        for key in ["provision_id", "provision_name", "status"]:
            if key not in p:
                return False, f"provisions[{i}] missing '{key}'"
        if p["status"] not in ("FOUND_BOTH", "TEMPLATE_ONLY", "TENANT_ONLY", "AMBIGUOUS"):
            return False, f"provisions[{i}] invalid status: {p['status']}"
    return True, None


def _repair_truncated_json(fragment: str) -> Optional[dict]:
    """Attempt to repair truncated JSON by closing open structures.

    When the model hits max_output_tokens, the JSON is cut off mid-provision.
    We try to close open strings and brackets to salvage completed provisions.
    """
    # Find the last complete provision object (ends with })
    # Work backwards to find a point where we can close the array and wrapper
    last_complete = -1
    depth = 0
    in_str = False
    esc = False

    for i, c in enumerate(fragment):
        if esc:
            esc = False
            continue
        if c == "\\":
            esc = True
            continue
        if c == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 1:
                # We just closed a provision object (depth returns to 1 = inside array)
                last_complete = i

    if last_complete < 0:
        return None

    # Take everything up to last complete provision, close array and wrapper
    truncated = fragment[: last_complete + 1] + "\n  ]\n}"
    try:
        obj = json.loads(truncated)
        if isinstance(obj, dict) and "provisions" in obj and isinstance(obj["provisions"], list):
            print(f"[lease_extract] Repaired truncated JSON: {len(obj['provisions'])} provisions recovered", flush=True)
            return obj
    except json.JSONDecodeError:
        pass
    return None


def _extract_provisions_json(raw: str) -> dict:
    """Extract the {"provisions": [...]} wrapper from Gemini's response.

    The core safe_json_extract picks individual provision objects over the
    wrapper because its scoring favours objects with more top-level fields.
    This function specifically looks for the provisions wrapper.
    """
    # Strip markdown code fences
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```\s*$", "", text)
    text = text.strip()

    # Fast path: whole text is valid JSON with provisions key
    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and "provisions" in obj:
            return obj
    except json.JSONDecodeError:
        pass

    # Slow path: find the outermost { that contains "provisions"
    # Walk through all opening braces and find balanced JSON objects
    for i, c in enumerate(text):
        if c != "{":
            continue
        # Use balanced brace counting
        depth = 0
        in_str = False
        esc = False
        end = -1
        for j in range(i, len(text)):
            ch = text[j]
            if esc:
                esc = False
                continue
            if ch == "\\":
                esc = True
                continue
            if ch == '"' and not esc:
                in_str = not in_str
                continue
            if in_str:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = j
                    break
        if end < 0:
            continue
        candidate = text[i : end + 1]
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict) and "provisions" in obj and isinstance(obj["provisions"], list):
                return obj
        except json.JSONDecodeError:
            continue

    # Try repairing truncated JSON (model hit max_output_tokens)
    # Find the outermost {"provisions": [ and close it
    prov_idx = text.find('"provisions"')
    if prov_idx >= 0:
        start = text.rfind("{", 0, prov_idx)
        if start >= 0:
            # Attempt to close any open strings and brackets
            fragment = text[start:]
            repaired = _repair_truncated_json(fragment)
            if repaired:
                return repaired

    # Last resort: fall back to core extractor (may pick wrong object)
    obj = safe_json_extract(raw)
    if isinstance(obj, dict) and "provisions" in obj:
        return obj

    raise ValueError("Could not find {'provisions': [...]} in Gemini response")


# Extraction fallback chain — imported from central model config
from cam.adapters.lease_review.model_config import EXTRACTION_CHAIN  # noqa: E402

# Mistral has a lower output token ceiling than other providers
MISTRAL_MAX_TOKENS = 32_000

# Timeouts — both primary and fallback use the same generous limit.
# Fallback models are invoked when primary is unavailable, meaning the API is
# likely stressed. Stressed APIs generate tokens more slowly (40-70 tok/s vs 115).
# At 50 tok/s, a 16k-token chunk response takes ~332s — 300s covers this with margin.
EXTRACTION_PRIMARY_TIMEOUT = 300.0
EXTRACTION_FALLBACK_TIMEOUT = 300.0

# Output token caps
EXTRACTION_MAX_TOKENS_SINGLE = 32_000  # Single-call path (lease ≤ CHUNK_WORD_THRESHOLD)
EXTRACTION_MAX_TOKENS_CHUNK  = 16_000  # Per-chunk path — half the provisions per call

# Tenant word count above which extraction splits into two provision-list chunks.
# Each chunk covers half the provisions against the full document text.
# Our test leases: ~5,500 words (single-call). Standard commercial: 10-20k (chunked).
CHUNK_WORD_THRESHOLD = 8_000


def _get_adapter_for_provider(provider: str):
    """Get the appropriate adapter for a provider."""
    from cam.core.provider_router import (
        GoogleGenAIAdapter, OpenAIAdapter, AnthropicAdapter, XAIAdapter,
    )
    if provider == "google":
        return GoogleGenAIAdapter()
    elif provider == "openai":
        return OpenAIAdapter()
    elif provider == "anthropic":
        return AnthropicAdapter()
    elif provider == "xai":
        return XAIAdapter()
    elif provider == "mistral":
        # Mistral uses OpenAI-compatible API
        import os
        from openai import OpenAI
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise ProviderError("MISTRAL_API_KEY missing")

        class MistralAdapter:
            def __init__(self):
                self.client = OpenAI(
                    api_key=api_key,
                    base_url="https://api.mistral.ai/v1",
                    timeout=60.0,
                )
            def call(self, system_prompt, user_prompt, target):
                resp = self.client.chat.completions.create(
                    model=target.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=target.temperature,
                    max_tokens=target.max_output_tokens,
                    timeout=target.timeout_sec,
                )
                return (resp.choices[0].message.content or "").strip()

        return MistralAdapter()
    else:
        raise ProviderError(f"Unknown provider: {provider}")


def _run_extraction_call(
    template_text: str,
    tenant_text: str,
    provisions: List[dict],
    config: dict,
    max_output_tokens: int,
    chunk_label: str = "",
) -> Dict[str, Any]:
    """Run one extraction call against the full fallback chain.

    This is the core extraction logic. Called once (single path) or twice
    (chunked path — once per provision-list half).

    Args:
        template_text: Full template document text.
        tenant_text: Full tenant lease text.
        provisions: Provision list for this call (all or half).
        config: Pipeline config dict.
        max_output_tokens: Output token cap for this call.
        chunk_label: Optional label for log messages (e.g., "chunk 1/2").

    Returns:
        Dict with keys: provisions, contract_metadata, deal_overview,
        discovered_provisions, meta.
    """
    label_prefix = f"[lease_extract{' ' + chunk_label if chunk_label else ''}]"

    # Build the prompt
    prompt_template = _load_prompt_template()
    provision_list_str = _build_provision_list(provisions)

    user_prompt = prompt_template.replace("{template_text}", template_text)
    user_prompt = user_prompt.replace("{tenant_text}", tenant_text)
    user_prompt = user_prompt.replace("{provision_list}", provision_list_str)

    system_prompt = (
        "You are a legal document analyst specializing in commercial lease agreements. "
        "You extract and align lease provisions with precision. "
        "Always respond with valid JSON only."
    )

    health = get_health_tracker()
    start_time = time.time()
    errors = []
    obj = None
    actual_model = EXTRACTION_CHAIN[0][1]
    actual_provider = EXTRACTION_CHAIN[0][0]
    fallback_used = False
    google_provider_error = False

    for chain_idx, (provider, model_name) in enumerate(EXTRACTION_CHAIN):
        if obj is not None:
            break

        # Skip degraded providers
        if not health.is_available(provider):
            print(f"{label_prefix} Skipping {model_name} ({provider} degraded), trying next...", flush=True)
            errors.append({"model": model_name, "error": f"provider {provider} degraded, skipped"})
            continue

        # Skip gemini-2.5-pro if primary Gemini failed at provider level
        if chain_idx == 1 and provider == "google" and google_provider_error:
            print(f"{label_prefix} Skipping {model_name} (google provider-level error on primary), trying next...", flush=True)
            errors.append({"model": model_name, "error": "google provider-level error, skipped"})
            continue

        # Timeout: primary Gemini gets EXTRACTION_PRIMARY_TIMEOUT,
        # Gemini fallback gets the same, all others get EXTRACTION_FALLBACK_TIMEOUT
        if chain_idx == 0:
            timeout = EXTRACTION_PRIMARY_TIMEOUT
        elif provider == "google":
            timeout = EXTRACTION_PRIMARY_TIMEOUT
        else:
            timeout = EXTRACTION_FALLBACK_TIMEOUT

        # Per-model output token cap
        current_max_output = max_output_tokens
        if provider == "mistral":
            current_max_output = min(current_max_output, MISTRAL_MAX_TOKENS)

        target = ModelTarget(
            name=f"{provider}:{model_name}-extraction",
            provider=provider,
            model=model_name,
            priority=chain_idx + 1,
            max_output_tokens=current_max_output,
            temperature=0.0,
            timeout_sec=timeout,
            max_retries=0,
        )

        call_label = "primary" if chain_idx == 0 else "FALLBACK"
        print(f"{label_prefix} calling {model_name} ({call_label})...", flush=True)

        try:
            adapter = _get_adapter_for_provider(provider)
        except Exception as e:
            errors.append({"model": model_name, "error": f"adapter init: {e}"})
            continue

        try:
            raw = adapter.call(system_prompt, user_prompt, target)

            # Cancel check immediately after API return
            from cam.adapters.lease_review.lease_adapter import _check_cancel
            _check_cancel(config)

            obj = _extract_provisions_json(raw)

            # Validate
            ok, why = _validate_extraction(obj)
            if not ok:
                errors.append({"model": model_name, "error": f"validation: {why}"})
                obj = None
                continue

            actual_model = model_name
            actual_provider = provider
            if chain_idx > 0:
                fallback_used = True

            elapsed_so_far = time.time() - start_time
            print(f"{label_prefix} {model_name} succeeded in {round(elapsed_so_far, 1)}s ({call_label})", flush=True)

        except Exception as e:
            error_str = str(e).lower()
            # NOTE: "timeout" excluded intentionally — slow ≠ down.
            # Only real outage signals warrant the degraded cooldown.
            is_provider_error = any(k in error_str for k in [
                "503", "connection", "refused", "unavailable",
                "service_unavailable", "resource_exhausted",
            ])

            errors.append({"model": model_name, "error": str(e)})

            if is_provider_error:
                health.mark_degraded(provider, reason=str(e)[:100])
                if chain_idx == 0 and provider == "google":
                    google_provider_error = True
                elapsed_so_far = time.time() - start_time
                print(f"{label_prefix} {model_name} FAILED ({type(e).__name__}, {round(elapsed_so_far, 1)}s elapsed), "
                      f"provider {provider} marked degraded", flush=True)
            else:
                elapsed_so_far = time.time() - start_time
                print(f"{label_prefix} {model_name} FAILED ({type(e).__name__}, {round(elapsed_so_far, 1)}s elapsed)", flush=True)

            continue

    elapsed = time.time() - start_time

    if obj is None:
        raise RuntimeError(f"Stage 1 extraction failed on all models{' (' + chunk_label + ')' if chunk_label else ''}: {errors}")

    call_label = "primary" if not fallback_used else "FALLBACK"
    print(f"{label_prefix} Success: {actual_model} ({call_label}) in {round(elapsed, 1)}s", flush=True)

    # Ensure all requested provisions are represented in the output
    result_ids = {p["provision_id"] for p in obj.get("provisions", [])}
    for prov in provisions:
        if prov["id"] not in result_ids:
            obj["provisions"].append({
                "provision_id": prov["id"],
                "provision_name": prov["name"],
                "template_text": "",
                "tenant_text": "",
                "template_section_ref": "",
                "tenant_section_ref": "",
                "status": "AMBIGUOUS",
                "alignment_notes": "Provision not found by extraction model.",
                "definition_changes": "",
            })

    return {
        "provisions": obj["provisions"],
        "contract_metadata": obj.get("contract_metadata", {}),
        "deal_overview": obj.get("deal_overview", {}),
        "discovered_provisions": obj.get("discovered_provisions", []),
        "meta": {
            "model": actual_model,
            "provider": actual_provider,
            "fallback_used": fallback_used,
            "elapsed_sec": round(elapsed, 2),
            "errors": errors,
        },
    }


def _extract_chunked(
    template_text: str,
    tenant_text: str,
    provisions: List[dict],
    config: dict,
) -> Dict[str, Any]:
    """Run extraction in two sequential calls, each covering half the provision list.

    Used when the tenant lease exceeds CHUNK_WORD_THRESHOLD words. Splitting the
    provision list halves the output tokens per call, making fallback models
    reliable within the standard timeout budget.

    The full document text is passed to both calls — only the provision list
    is split. contract_metadata and deal_overview are taken from the first call.
    """
    midpoint = len(provisions) // 2
    chunk_a = provisions[:midpoint]
    chunk_b = provisions[midpoint:]

    print(f"[lease_extract] Chunked extraction: {len(provisions)} provisions → "
          f"chunk 1: {len(chunk_a)}, chunk 2: {len(chunk_b)}", flush=True)

    result_a = _run_extraction_call(
        template_text, tenant_text, chunk_a, config,
        max_output_tokens=EXTRACTION_MAX_TOKENS_CHUNK,
        chunk_label="chunk 1/2",
    )

    result_b = _run_extraction_call(
        template_text, tenant_text, chunk_b, config,
        max_output_tokens=EXTRACTION_MAX_TOKENS_CHUNK,
        chunk_label="chunk 2/2",
    )

    # Merge: combine provision lists, take metadata from chunk 1
    merged_provisions = result_a["provisions"] + result_b["provisions"]
    merged_errors = result_a["meta"]["errors"] + result_b["meta"]["errors"]
    total_elapsed = result_a["meta"]["elapsed_sec"] + result_b["meta"]["elapsed_sec"]

    print(f"[lease_extract] Chunked extraction complete: "
          f"{len(merged_provisions)} provisions total, {round(total_elapsed, 1)}s combined", flush=True)

    return {
        "provisions": merged_provisions,
        "contract_metadata": result_a["contract_metadata"],
        "deal_overview": result_a["deal_overview"],
        "discovered_provisions": (
            result_a.get("discovered_provisions", []) +
            result_b.get("discovered_provisions", [])
        ),
        "meta": {
            "model": result_a["meta"]["model"],
            "provider": result_a["meta"]["provider"],
            "fallback_used": result_a["meta"]["fallback_used"] or result_b["meta"]["fallback_used"],
            "elapsed_sec": round(total_elapsed, 2),
            "errors": merged_errors,
            "chunked": True,
            "chunk_models": [result_a["meta"]["model"], result_b["meta"]["model"]],
        },
    }


def extract_provisions(
    template_text: str,
    tenant_text: str,
    provisions: List[dict],
    config: dict,
) -> Dict[str, Any]:
    """Run Stage 1: Provision extraction and alignment.

    Routes to single-call or chunked extraction based on tenant lease word count.
    Word count is read from config["tenant_word_count"] (set by lease_adapter).
    If not present, falls back to counting tenant_text directly.

    Single-call path (≤ CHUNK_WORD_THRESHOLD words):
        One API call, all provisions, max_output_tokens=EXTRACTION_MAX_TOKENS_SINGLE.

    Chunked path (> CHUNK_WORD_THRESHOLD words):
        Two sequential API calls, each with half the provision list, full document text,
        max_output_tokens=EXTRACTION_MAX_TOKENS_CHUNK per call. Results merged.

    Args:
        template_text: Full text of the standard lease template.
        tenant_text: Full text of the tenant lease.
        provisions: List of provision dicts from the taxonomy.
        config: Configuration dict with model settings.

    Returns:
        Dict with keys:
            "provisions": list of extraction results per provision
            "contract_metadata": lease metadata dict
            "deal_overview": deal overview dict
            "discovered_provisions": list of model-discovered additional provisions
            "meta": API call metadata (model used, timing, errors, chunked flag)
    """
    word_count = config.get("tenant_word_count") or len(tenant_text.split())

    if word_count > CHUNK_WORD_THRESHOLD:
        print(f"[lease_extract] Tenant lease is {word_count} words (>{CHUNK_WORD_THRESHOLD}) — "
              f"using chunked extraction", flush=True)
        return _extract_chunked(template_text, tenant_text, provisions, config)

    print(f"[lease_extract] Tenant lease is {word_count} words (≤{CHUNK_WORD_THRESHOLD}) — "
          f"using single-call extraction", flush=True)
    return _run_extraction_call(
        template_text, tenant_text, provisions, config,
        max_output_tokens=EXTRACTION_MAX_TOKENS_SINGLE,
    )


def targeted_reextract_section(
    provision_id: str,
    provision_name: str,
    missing_section_ref: str,
    tenant_text: str,
    config: dict,
) -> str:
    """Re-extract a specific missing section from the tenant lease.

    Called when the coverage audit finds an extra_subsection gap — a section
    that exists in the tenant document but was not captured in the main
    extraction pass.

    Returns the extracted text as a string, or empty string on failure.
    This is a narrow, cheap call — no full document re-processing.
    """
    system_prompt = (
        "You are a legal document analyst. Extract verbatim text from a lease document. "
        "Copy the text exactly as written — do not paraphrase, summarize, or reformat. "
        "Respond with only the extracted text, no JSON wrapper, no commentary."
    )

    user_prompt = (
        f"From the lease document below, extract the complete verbatim text of "
        f"{missing_section_ref}. This section belongs to the provision covering "
        f"'{provision_name}' ({provision_id}).\n\n"
        f"Copy the text exactly as it appears, including all subsections and "
        f"sub-paragraphs under {missing_section_ref}. Stop at the next section header.\n\n"
        f"Do not include any explanation. Return only the extracted clause text.\n\n"
        f"LEASE DOCUMENT:\n{tenant_text}"
    )

    # Use the same fallback chain as main extraction, but plain text response
    health = get_health_tracker()
    for provider, model_name in EXTRACTION_CHAIN:
        if not health.is_available(provider):
            continue
        try:
            target = ModelTarget(
                name=f"{provider}:{model_name}-reextract",
                provider=provider,
                model=model_name,
                priority=1,
                max_output_tokens=4000,
                temperature=0.0,
                timeout_sec=120.0,
                max_retries=0,
            )
            adapter = _get_adapter_for_provider(provider)
            raw = adapter.call(system_prompt, user_prompt, target)
            raw = raw.strip()
            if len(raw) > 30:  # sanity check — at least a sentence
                print(f"[lease_extract] targeted_reextract: {missing_section_ref} "
                      f"recovered ({len(raw)} chars via {model_name})", flush=True)
                return raw
        except Exception as e:
            print(f"[lease_extract] targeted_reextract: {model_name} failed: {e}", flush=True)
            continue

    print(f"[lease_extract] targeted_reextract: all models failed for {missing_section_ref}", flush=True)
    return ""


def parse_identity_block(lp00_result: dict, lp00_template_result: dict = None) -> dict:
    """
    Takes the raw LP-00 extraction result and structures it into identity fields.
    Also compares against template LP-00 result if provided.

    Returns a dict with:
        fields: list of {label, template_value, tenant_value, match, informational}
        identity_warnings: list of warning strings (landlord/property mismatches)

    NOTE: Full structured parsing is a follow-on step. For now, returns the raw
    text with a structured wrapper so the frontend can render it differently.
    """
    return {
        "provision_id": "LP-00",
        "provision_name": "Parties & Premises",
        "identity_check": True,
        "raw_tenant": lp00_result.get("tenant_text", ""),
        "raw_template": lp00_template_result.get("tenant_text", "") if lp00_template_result else "",
        "identity_warnings": [],
    }
