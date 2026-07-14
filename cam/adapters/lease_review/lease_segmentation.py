"""
Step 423B — LP-blind span proposal / segmentation.

Doctrine (423 spec §2): evidence belongs to the lease first; LPs cite into
verified source evidence later. This module proposes candidate evidence
spans from a single lease document WITHOUT any LP taxonomy in its prompt or
output schema, then resolves each proposal through the 423A verified-span
substrate (cam.adapters.lease_review.lease_evidence_spans).

This module is a SIDECAR. It is a dead-end diagnostic artifact by design:
nothing in Stage 5, assess_coverage, Mode C, or downstream report generation
reads its output. No live pipeline file imports this module — see the seam
tests in tests/test_423b_lp_blind_segmentation.py. The first component that
consumes verified spans for evaluation must be built in a later, explicitly
authorized slice.

423B does NOT make LP-07 see the 100% tenant share. That requires later
global-parameter/dependency-map and many-to-many assignment slices (423 spec
§5, §6). See build_log/423B_lp_blind_segmentation_proposal.md for the full
deferred list.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from cam.core.provider_router import ModelTarget, FatalProviderError, _check_generation_integrity
from cam.core.provider_health import get_health_tracker
from cam.adapters.lease_review.model_config import EXTRACTION_CHAIN
from cam.adapters.lease_review.lease_evidence_spans import (
    CanonicalSource,
    build_canonical_source,
    resolve_span,
    is_usable_in_canonical_stage5,
    VERIFIED,
    AMBIGUOUS,
    UNVERIFIED,
)


class SegmentationIntegrityError(Exception):
    """Raised when canonical segmentation fails and fallback would silently
    substitute. Same doctrine as ExtractionIntegrityError (421B), applied to
    the segmentation call: in canonical mode, a failed primary must abort,
    never silently degrade to an empty or substituted result.
    """
    def __init__(self, message: str, errors: list = None, attempt_chain: list = None):
        super().__init__(message)
        self.errors = errors or []
        self.attempt_chain = attempt_chain or []


SCHEMA_PATH = Path(__file__).parent / "schemas" / "segmentation_schema.json"
PROMPT_PATH = Path(__file__).parent / "prompts" / "segmentation_span_proposal.txt"

ALLOWED_SPAN_TYPES = frozenset({"clause", "table", "definition", "other"})

# Single-primary segmentation chain. No fallback provider is implemented in
# this slice (423B) — deliberately. "fallback_used" is therefore always
# False by construction today; the field exists in metadata for a future
# slice that adds a real fallback chain, not because one exists yet. Reuses
# the same primary as extraction (EXTRACTION_CHAIN[0]) rather than declaring
# a new model constant, per the brief's "no generic extra_provider_params"
# constraint.
SEGMENTATION_PRIMARY = EXTRACTION_CHAIN[0]

SEGMENTATION_TIMEOUT = 300.0
SEGMENTATION_MAX_TOKENS = 16_000  # Bounded — this is a sidecar/smoke path, not a production ceiling.


def _load_prompt_template() -> str:
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()


def _load_schema() -> dict:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _prompt_hash(prompt_text: str) -> str:
    return hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()[:16]


def _config_hash(config: dict) -> str:
    return hashlib.sha256(json.dumps(config, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def validate_segmentation_output(obj: dict) -> Tuple[bool, Optional[str]]:
    """Validate raw segmentation output against the LP-blind schema.

    `additionalProperties: false` on both the top level and each span
    object is the structural enforcement of the LP-blindness contract: an
    LP id, verdict, risk, or favorability field fails validation here
    rather than being silently accepted and carried downstream.
    """
    try:
        import jsonschema
        schema = _load_schema()
        jsonschema.validate(instance=obj, schema=schema)
        return True, None
    except ImportError:
        pass
    except Exception as e:
        return False, str(e)

    # Basic structural validation if jsonschema is not available.
    if "spans" not in obj or not isinstance(obj["spans"], list):
        return False, "Missing or invalid 'spans' array"
    allowed_keys = {"quote", "span_type", "section_hint", "page_hint", "table_hint", "neutral_label"}
    for i, s in enumerate(obj["spans"]):
        if "quote" not in s or "span_type" not in s:
            return False, f"spans[{i}] missing required field"
        if s["span_type"] not in ALLOWED_SPAN_TYPES:
            return False, f"spans[{i}] invalid span_type: {s['span_type']!r}"
        extra = set(s.keys()) - allowed_keys
        if extra:
            return False, f"spans[{i}] has disallowed fields: {sorted(extra)}"
    return True, None


def _extract_segmentation_json(raw: str) -> dict:
    """Extract the {"spans": [...]} wrapper from the model response."""
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```\s*$", "", text)
    text = text.strip()

    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and "spans" in obj:
            return obj
    except json.JSONDecodeError:
        pass

    from cam.core.json_extract import safe_json_extract
    obj = safe_json_extract(raw)
    if isinstance(obj, dict) and "spans" in obj:
        return obj
    raise ValueError("Could not find {'spans': [...]} in segmentation response")


def propose_spans(
    tenant_text: str,
    canonical: bool = True,
    max_output_tokens: int = SEGMENTATION_MAX_TOKENS,
) -> Dict[str, Any]:
    """Call the LP-blind segmentation model and return raw proposals plus
    integrity metadata. Does NOT resolve spans — see `resolve_proposed_spans`.

    Mirrors extract_provisions_single_doc()'s canonical fail-closed doctrine
    (421B): in canonical mode, a primary failure raises rather than silently
    degrading. Only a single primary is implemented in this slice (see
    SEGMENTATION_PRIMARY) — canonical=True and canonical=False differ only
    in whether that failure raises or returns a degraded, empty result;
    there is no second provider to fall back to yet.

    Segmentation-call integrity: before calling the model, this function
    constructs the same params dict the Google adapter builds internally
    (`{"temperature": ..., "max_output_tokens": ...}`) and asserts it via
    `_check_generation_integrity()` (imported from cam.core.provider_router,
    not modified) — the same 416 doctrine applied to this new call site
    without a cam/core/ change.
    """
    provider, model_name = SEGMENTATION_PRIMARY
    prompt_template = _load_prompt_template()
    prompt_hash = _prompt_hash(prompt_template)
    user_prompt = prompt_template.replace("{tenant_text}", tenant_text)
    system_prompt = (
        "You are a document segmentation assistant. You identify and quote "
        "candidate source passages from a single document. You do not "
        "classify passages into any external taxonomy, and you do not form "
        "legal conclusions. Always respond with valid JSON only."
    )

    target = ModelTarget(
        name=f"{provider}:{model_name}-segmentation",
        provider=provider,
        model=model_name,
        priority=1,
        max_output_tokens=max_output_tokens,
        temperature=0.0,
        timeout_sec=SEGMENTATION_TIMEOUT,
        max_retries=0,
    )
    declared_config = {
        "provider": provider,
        "model": model_name,
        "temperature": target.temperature,
        "max_output_tokens": target.max_output_tokens,
    }
    config_hash = _config_hash(declared_config)

    health = get_health_tracker()
    start_time = time.time()
    errors: List[dict] = []
    attempt_chain: List[dict] = []
    obj = None
    integrity_metadata = None

    if health.is_available(provider):
        try:
            from cam.adapters.lease_review.lease_extract import _get_adapter_for_provider
            adapter = _get_adapter_for_provider(provider)

            # Segmentation-call integrity check — asserted BEFORE the call,
            # against the params this call declares it will transmit.
            outbound_params = {
                "temperature": target.temperature,
                "max_tokens": target.max_output_tokens,
            }
            integrity_metadata = _check_generation_integrity(target, outbound_params)

            raw = adapter.call(system_prompt, user_prompt, target)
            attempt_chain.append({"model": model_name, "provider": provider, "outcome": "call_returned"})

            parsed = _extract_segmentation_json(raw)
            ok, why = validate_segmentation_output(parsed)
            if not ok:
                errors.append({"model": model_name, "error": f"validation: {why}"})
                attempt_chain.append({"model": model_name, "provider": provider, "outcome": f"validation_failed: {why}"})
            else:
                obj = parsed
                attempt_chain.append({"model": model_name, "provider": provider, "outcome": "success"})
        except FatalProviderError as fpe:
            errors.append({"model": model_name, "error": f"config_integrity: {fpe}"})
            attempt_chain.append({"model": model_name, "provider": provider, "outcome": f"config_integrity_violation: {fpe}"})
        except Exception as e:
            errors.append({"model": model_name, "error": f"{type(e).__name__}: {e}"})
            attempt_chain.append({"model": model_name, "provider": provider, "outcome": f"exception: {type(e).__name__}"})
    else:
        errors.append({"model": model_name, "error": f"provider {provider} degraded, skipped"})
        attempt_chain.append({"model": model_name, "provider": provider, "outcome": "skipped_degraded"})

    elapsed = time.time() - start_time

    base_meta = {
        "primary_provider": provider,
        "primary_model": model_name,
        "canonical": canonical,
        "fallback_used": False,
        "fallback_chain": [],
        "declared_generation_config": declared_config,
        "integrity_metadata": integrity_metadata,
        "prompt_hash": prompt_hash,
        "config_hash": config_hash,
        "elapsed_sec": round(elapsed, 2),
        "errors": errors,
        "attempt_chain": attempt_chain,
    }

    if obj is None:
        failure_reason = errors[-1]["error"] if errors else "unknown"
        if canonical:
            raise SegmentationIntegrityError(
                f"Segmentation integrity failure: primary segmenter ({provider}/{model_name}) "
                f"failed and canonical mode prohibits silent fallback (no fallback segmenter "
                f"is implemented in this slice). Errors: {errors}",
                errors=errors,
                attempt_chain=attempt_chain,
            )
        return {
            "spans": [],
            "meta": {
                **base_meta,
                "provider": "none",
                "model": "none",
                "degraded": True,
                "parse_or_validation_failure_reason": failure_reason,
            },
        }

    return {
        "spans": obj.get("spans", []),
        "meta": {
            **base_meta,
            "provider": provider,
            "model": model_name,
            "degraded": False,
            "parse_or_validation_failure_reason": None,
        },
    }


def resolve_proposed_spans(
    canonical_source: CanonicalSource,
    proposals: List[dict],
) -> List[dict]:
    """Resolve each LP-blind proposed span through the 423A substrate.

    Hints (section_hint/page_hint/table_hint) are used ONLY to help the
    423A resolver disambiguate a multiply-matched quote — mapped to
    `section_ref`/`source_anchor`, the two optional fields the 423A
    EvidenceSpan schema already declares for exactly this purpose. They are
    never persisted as a new canonical address field: the persisted
    EvidenceSpan's identity remains exactly the 423A schema (offsets +
    hashes). `page_hint`/`table_hint` are recorded on the returned record
    for sidecar/audit purposes only — nothing adds a `page_ref` or
    `table_ref` to `lease_evidence_spans.py`.

    Returns one record per proposal: proposed quote, proposed structural
    type, optional neutral label, hints used during resolution, resolved
    evidence span id, verification status, offsets if verified, hashes,
    failure reason if ambiguous/unverified.
    """
    records = []
    for i, p in enumerate(proposals, start=1):
        quote = p.get("quote", "")
        span_type = p.get("span_type", "other")
        neutral_label = p.get("neutral_label")
        section_hint = p.get("section_hint")
        table_or_page_hint = p.get("table_hint") or p.get("page_hint")

        span = resolve_span(
            canonical_source,
            quote=quote,
            evidence_span_id=f"EV-{i:06d}",
            section_ref=section_hint,
            source_anchor=table_or_page_hint,
        )

        failure_reason = None
        if span.verification_status == UNVERIFIED:
            failure_reason = "quote not found in canonical source (exact or whitespace-flexible match)"
        elif span.verification_status == AMBIGUOUS:
            failure_reason = "quote matched multiple locations; hints did not uniquely disambiguate"

        records.append({
            "proposed_quote": quote,
            "proposed_span_type": span_type,
            "neutral_label": neutral_label,             # provenance only — never a routing key
            "hints": {                                    # non-canonical, resolution-only
                "section_hint": section_hint,
                "page_hint": p.get("page_hint"),
                "table_hint": p.get("table_hint"),
            },
            "evidence_span_id": span.evidence_span_id,
            "verification_status": span.verification_status,
            "start_char": span.start_char,
            "end_char": span.end_char,
            "source_document_hash": span.source_document_hash,
            "canonical_text_hash": span.canonical_text_hash,
            "span_text_hash": span.span_text_hash,
            "failure_reason": failure_reason,
            "usable_in_canonical_stage5": is_usable_in_canonical_stage5(span),
        })
    return records


def build_span_universe_sidecar(
    canonical_source: CanonicalSource,
    segmentation_result: dict,
    resolved_records: List[dict],
) -> dict:
    """Assemble the sidecar artifact dict (423B Part 5).

    The 423B sidecar is not live pipeline input. Nothing in Stage 5,
    assess_coverage, Mode C, or downstream report generation reads it.
    """
    by_type: Dict[str, int] = {}
    for r in resolved_records:
        by_type[r["proposed_span_type"]] = by_type.get(r["proposed_span_type"], 0) + 1

    verified = [r for r in resolved_records if r["verification_status"] == VERIFIED]
    not_verified = [r for r in resolved_records if r["verification_status"] != VERIFIED]

    return {
        "_artifact_type": "423B_span_universe_sidecar",
        "_not_live_pipeline_input": True,
        "_warning": (
            "This sidecar is a diagnostic artifact only. Nothing in Stage 5, "
            "assess_coverage, Mode C, or downstream report generation reads it. "
            "The first component that consumes verified spans for evaluation "
            "must be built in a later, explicitly authorized slice."
        ),
        "source_document_hash": canonical_source.source_document_hash,
        "canonical_text_hash": canonical_source.canonical_text_hash,
        "normalization_profile": canonical_source.normalization_profile,
        "run_id": canonical_source.run_id,
        "segmentation_meta": segmentation_result["meta"],
        "total_proposed_spans": len(resolved_records),
        "count_verified": len(verified),
        "count_ambiguous": sum(1 for r in resolved_records if r["verification_status"] == AMBIGUOUS),
        "count_unverified": sum(1 for r in resolved_records if r["verification_status"] == UNVERIFIED),
        "counts_by_structural_type": by_type,
        "neutral_label_is_non_routing_provenance": True,
        "hints_are_non_canonical_resolution_aids_only": True,
        "verified_spans": [
            {
                "evidence_span_id": r["evidence_span_id"],
                "start_char": r["start_char"],
                "end_char": r["end_char"],
                "span_type": r["proposed_span_type"],
                "excerpt": r["proposed_quote"][:200],
                "neutral_label": r["neutral_label"],
            }
            for r in verified
        ],
        "ambiguous_or_unverified_spans": [
            {
                "proposed_quote_excerpt": r["proposed_quote"][:200],
                "span_type": r["proposed_span_type"],
                "verification_status": r["verification_status"],
                "failure_reason": r["failure_reason"],
                "neutral_label": r["neutral_label"],
            }
            for r in not_verified
        ],
    }
