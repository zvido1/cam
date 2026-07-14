"""
Step 423C — Element-guided, non-exclusive span elicitation.

Supersedes the LP-blind approach of 423B
(build_log/423B_lp_blind_segmentation_proposal.md) for the reasons in
build_log/423C_element_guided_elicitation.md: LP-blindness stopped
partitioning, which was correct, but it also gave the model no target,
which produced coarse multi-parameter blobs and missed a declared element
entirely. 423B's module (`lease_segmentation.py`) is left in place,
untouched — it is not deleted or modified; this module supersedes it going
forward but takes no destructive action against it.

Doctrine, unchanged from 423 spec §2 and carried forward from 423B:
evidence belongs to the lease first; LPs cite into verified source evidence
later. Guided elicitation is NOT a return to partitioning — read this
distinction carefully, it is the whole point of this slice:

  - The PROMPT is element-aware: for each of a batch of elements, it asks
    the model to quote every passage bearing on THAT element, over the
    WHOLE document, and explicitly requires repetition — the model must
    quote the same passage again for a second element if it bears on that
    element too, and must not withhold a passage because it was already
    used.
  - The ARTIFACT stays LP-unassigned: a span's identity is its resolved
    (start_char, end_char) offset, never the element that elicited it.
    Two elements eliciting the identical passage produce ONE span with TWO
    `elicited_by` provenance entries — not two spans.
  - The model NEVER sees or emits an `element_id` or any provision/LP
    identifier. Elements are presented as neutral, ordinal targets
    ("Target 1", "Target 2", ...) built from each element's
    `element_label`/`synonyms`. The mapping from "Target N" back to a real
    `element_id` happens entirely in code, in `resolve_elicited_spans`,
    after the model has already responded. Batching several elements from
    the same LP into one call is a COST decision only (see
    build_log/423C_element_guided_elicitation.md for the batching
    rationale) — the model is never told these targets are grouped under a
    provision, so batching does not reintroduce partitioning.

`elicited_by` is an audit/provenance field ONLY, populated after the fact
by `dedupe_elicited_spans`. No downstream code may branch on it or use it
as a lookup/routing key — the only key used for span identity anywhere in
this module is the resolved `(start_char, end_char)` offset pair (and, for
non-verified records, nothing — they are never merged with anything).
Relevance is the selection panel's job (423 spec §6, a later, unauthorized
slice).

This module is a SIDECAR, exactly as 423B was: not wired into the live
Mode C / Stage 5 pipeline. See build_log/423C_element_guided_elicitation.md
for the full list of what remains unwired.
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


class ElicitationIntegrityError(Exception):
    """Raised when canonical elicitation fails and fallback would silently
    substitute. Same doctrine as ExtractionIntegrityError (421B) /
    SegmentationIntegrityError (423B): in canonical mode, a failed primary
    must abort, never silently degrade to an empty or substituted result.
    """
    def __init__(self, message: str, errors: list = None, attempt_chain: list = None):
        super().__init__(message)
        self.errors = errors or []
        self.attempt_chain = attempt_chain or []


KNOWLEDGE_SCHEMA_PATH = Path(__file__).parent / "schemas" / "retail_lease_knowledge.json"
PROMPT_PATH = Path(__file__).parent / "prompts" / "element_elicitation.txt"
OUTPUT_SCHEMA_PATH = Path(__file__).parent / "schemas" / "element_elicitation_schema.json"

# Single-primary elicitation chain, same reasoning as 423B: no fallback
# provider is implemented in this slice. Reuses EXTRACTION_CHAIN[0] rather
# than declaring a new model constant.
ELICITATION_PRIMARY = EXTRACTION_CHAIN[0]

ELICITATION_TIMEOUT = 300.0
ELICITATION_MAX_TOKENS = 16_000  # Bounded — sidecar/smoke path, not a production ceiling.


# ── Element loading (read-only; retail_lease_knowledge.json is never modified) ─

def load_expected_elements_by_lp(schema_path: Optional[Path] = None) -> Dict[str, dict]:
    """Read `expected_elements_305` per LP from the knowledge schema.

    Returns {lp_id: {"lp_name": str, "elements": [{"element_id", "element_label",
    "synonyms"}, ...]}}. Only LPs that declare `expected_elements_305` are
    included (32 of the schema's issue areas at time of writing).
    """
    path = schema_path or KNOWLEDGE_SCHEMA_PATH
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    result = {}
    for area in data.get("issue_areas", []):
        elements = area.get("expected_elements_305")
        if not elements:
            continue
        lp_id = area["id"]
        result[lp_id] = {
            "lp_name": area.get("name", lp_id),
            "elements": [
                {
                    "element_id": e["element_id"],
                    "element_label": e.get("element_label", ""),
                    "synonyms": e.get("synonyms", []),
                }
                for e in elements
            ],
        }
    return result


# ── Prompt / schema plumbing ────────────────────────────────────────────────────

def _load_prompt_template() -> str:
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()


def _load_output_schema() -> dict:
    with open(OUTPUT_SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _prompt_hash(prompt_text: str) -> str:
    return hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()[:16]


def _config_hash(config: dict) -> str:
    return hashlib.sha256(json.dumps(config, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def _build_target_list_text(elements: List[dict]) -> str:
    """Render elements as a NEUTRAL, ordinal target list for the prompt.
    Never includes element_id or any provision/LP identifier — only the
    human-readable label and search-phrase synonyms."""
    lines = []
    for i, e in enumerate(elements, start=1):
        synonyms = "; ".join(e.get("synonyms", []))
        line = f"Target {i}: {e['element_label']}"
        if synonyms:
            line += f"\n  Related phrasing to watch for: {synonyms}"
        lines.append(line)
    return "\n".join(lines)


def validate_elicitation_output(obj: dict) -> Tuple[bool, Optional[str]]:
    """Validate raw elicitation output against the schema.
    `additionalProperties: false` on both levels is the structural
    enforcement: a provision id, verdict, or risk field fails validation
    rather than being silently accepted."""
    try:
        import jsonschema
        schema = _load_output_schema()
        jsonschema.validate(instance=obj, schema=schema)
        return True, None
    except ImportError:
        pass
    except Exception as e:
        return False, str(e)

    if "target_matches" not in obj or not isinstance(obj["target_matches"], list):
        return False, "Missing or invalid 'target_matches' array"
    allowed_keys = {"target", "quotes"}
    for i, m in enumerate(obj["target_matches"]):
        if "target" not in m or "quotes" not in m:
            return False, f"target_matches[{i}] missing required field"
        extra = set(m.keys()) - allowed_keys
        if extra:
            return False, f"target_matches[{i}] has disallowed fields: {sorted(extra)}"
    return True, None


def _extract_elicitation_json(raw: str) -> dict:
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```\s*$", "", text)
    text = text.strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and "target_matches" in obj:
            return obj
    except json.JSONDecodeError:
        pass
    from cam.core.json_extract import safe_json_extract
    obj = safe_json_extract(raw)
    if isinstance(obj, dict) and "target_matches" in obj:
        return obj
    raise ValueError("Could not find {'target_matches': [...]} in elicitation response")


# ── The elicitation call ─────────────────────────────────────────────────────────

def elicit_spans_for_targets(
    tenant_text: str,
    elements: List[dict],
    canonical: bool = True,
    max_output_tokens: int = ELICITATION_MAX_TOKENS,
) -> Dict[str, Any]:
    """Call the element-guided elicitation model for a batch of elements.

    The model receives a neutral, ordinal target list built from each
    element's `element_label`/`synonyms` — never `element_id`, never an LP
    identifier. Returns raw `target_matches` (still keyed by "Target N")
    plus integrity metadata. Mapping "Target N" back to `element_id` and
    resolving quotes through the 423A substrate both happen afterward, in
    `resolve_elicited_spans` — never inside this function.

    Segmentation-call integrity, same doctrine as 423B: before calling the
    model, constructs the outbound params dict the Google adapter builds
    internally and asserts it via `_check_generation_integrity()` (imported
    from cam.core.provider_router, not modified). `canonical` is an
    EXPLICIT parameter written to an explicit metadata field — never
    inferred from `fallback_used` (the 422D bug class).
    """
    provider, model_name = ELICITATION_PRIMARY
    prompt_template = _load_prompt_template()
    prompt_hash = _prompt_hash(prompt_template)
    target_list_text = _build_target_list_text(elements)
    user_prompt = prompt_template.replace("{tenant_text}", tenant_text).replace("{target_list}", target_list_text)
    system_prompt = (
        "You are a document search assistant. You locate and quote candidate "
        "source passages that bear on a list of independent search targets. "
        "You do not classify passages into any external taxonomy, you do not "
        "form legal conclusions, and you do not decide coverage, risk, or "
        "favorability. Always respond with valid JSON only."
    )

    target = ModelTarget(
        name=f"{provider}:{model_name}-elicitation",
        provider=provider,
        model=model_name,
        priority=1,
        max_output_tokens=max_output_tokens,
        temperature=0.0,
        timeout_sec=ELICITATION_TIMEOUT,
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

            outbound_params = {
                "temperature": target.temperature,
                "max_tokens": target.max_output_tokens,
            }
            integrity_metadata = _check_generation_integrity(target, outbound_params)

            raw = adapter.call(system_prompt, user_prompt, target)
            attempt_chain.append({"model": model_name, "provider": provider, "outcome": "call_returned"})

            parsed = _extract_elicitation_json(raw)
            ok, why = validate_elicitation_output(parsed)
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
        "target_count": len(elements),
    }

    if obj is None:
        failure_reason = errors[-1]["error"] if errors else "unknown"
        if canonical:
            raise ElicitationIntegrityError(
                f"Elicitation integrity failure: primary elicitor ({provider}/{model_name}) "
                f"failed and canonical mode prohibits silent fallback (no fallback elicitor "
                f"is implemented in this slice). Errors: {errors}",
                errors=errors,
                attempt_chain=attempt_chain,
            )
        return {
            "target_matches": [],
            "meta": {
                **base_meta,
                "provider": "none",
                "model": "none",
                "degraded": True,
                "parse_or_validation_failure_reason": failure_reason,
            },
        }

    return {
        "target_matches": obj.get("target_matches", []),
        "meta": {
            **base_meta,
            "provider": provider,
            "model": model_name,
            "degraded": False,
            "parse_or_validation_failure_reason": None,
        },
    }


# ── Resolution and deduplication ────────────────────────────────────────────────

def resolve_elicited_spans(
    canonical_source: CanonicalSource,
    elements: List[dict],
    elicitation_result: dict,
) -> List[dict]:
    """Resolve every (target, quote) pair from ONE elicitation call through
    the unmodified 423A resolver. Returns one RAW record per quote — no
    deduplication here; see `dedupe_elicited_spans`.

    "Target N" is mapped back to its `element_id` here, in code, using the
    SAME `elements` list (same order) that was passed to
    `elicit_spans_for_targets`. The model never sees or returns an
    `element_id`.
    """
    target_to_element = {f"Target {i}": e["element_id"] for i, e in enumerate(elements, start=1)}
    records: List[dict] = []
    counter = 0
    for match in elicitation_result.get("target_matches", []):
        target_label = match.get("target", "")
        element_id = target_to_element.get(target_label, target_label)
        for quote in match.get("quotes", []):
            counter += 1
            span = resolve_span(canonical_source, quote=quote, evidence_span_id=f"EV-raw-{counter:06d}")

            failure_reason = None
            if span.verification_status == UNVERIFIED:
                failure_reason = "quote not found in canonical source (exact or whitespace-flexible match)"
            elif span.verification_status == AMBIGUOUS:
                failure_reason = "quote matched multiple locations; no anchor supplied in this slice"

            records.append({
                "verification_status": span.verification_status,
                "start_char": span.start_char,
                "end_char": span.end_char,
                "span_text": span.span_text,
                "source_document_hash": span.source_document_hash,
                "canonical_text_hash": span.canonical_text_hash,
                "span_text_hash": span.span_text_hash,
                "elicited_by": [element_id],           # provenance only — never a lookup key
                "quote_variants": [quote],
                "failure_reason": failure_reason,
                "usable_in_canonical_stage5": is_usable_in_canonical_stage5(span),
            })
    return records


def dedupe_elicited_spans(raw_records: List[dict]) -> List[dict]:
    """Deduplicate raw elicited-span records by resolved offset.

    Two records are the SAME span if and only if both are `verified` and
    their `(start_char, end_char)` are identical. Merging combines
    `elicited_by` (union, order-preserving, first-seen order) and
    `quote_variants` (union) into one record with one fresh
    `evidence_span_id`. Overlapping-but-not-identical ranges are NEVER
    merged — containment is not identity, and this function performs no
    containment check of any kind.

    `ambiguous`/`unverified` records have no offsets to key on (both are
    `None`) and are therefore never merged with anything, including each
    other — each stays its own record. This is a scoping choice, not an
    oversight: only `verified` spans have a concrete offset to dedupe by.

    `elicited_by` is provenance ONLY. The only value this function ever
    compares for span identity is `(start_char, end_char)` — nothing here
    reads or branches on `elicited_by`'s contents to decide identity.
    """
    by_offset: Dict[Tuple[int, int], dict] = {}
    ordered_keys: List[Tuple[int, int]] = []
    unresolved: List[dict] = []

    for r in raw_records:
        if r["verification_status"] != VERIFIED:
            unresolved.append(dict(r))
            continue
        key = (r["start_char"], r["end_char"])
        if key in by_offset:
            entry = by_offset[key]
            for eid in r["elicited_by"]:
                if eid not in entry["elicited_by"]:
                    entry["elicited_by"].append(eid)
            for q in r["quote_variants"]:
                if q not in entry["quote_variants"]:
                    entry["quote_variants"].append(q)
        else:
            by_offset[key] = dict(r)
            ordered_keys.append(key)

    deduped: List[dict] = []
    counter = 0
    for key in ordered_keys:
        counter += 1
        entry = by_offset[key]
        entry["evidence_span_id"] = f"EV-{counter:06d}"
        deduped.append(entry)
    deduped.extend(unresolved)
    return deduped


# ── LP-batched driver ────────────────────────────────────────────────────────────

def elicit_and_resolve_for_lp(
    canonical_source: CanonicalSource,
    lp_id: str,
    elements_by_lp: Dict[str, dict],
    canonical: bool = True,
) -> Tuple[dict, List[dict]]:
    """Run one elicitation call for all of `lp_id`'s declared elements
    (batched into a single call — see module/report for the batching
    rationale) and resolve every quote it returns. Returns
    (elicitation_result, raw_resolved_records) — NOT deduplicated; callers
    combining multiple LPs should pass all raw records from all calls
    through one `dedupe_elicited_spans` call so cross-LP duplicates
    collapse too.
    """
    lp_entry = elements_by_lp[lp_id]
    elements = lp_entry["elements"]
    result = elicit_spans_for_targets(canonical_source.canonical_text, elements, canonical=canonical)
    raw_records = resolve_elicited_spans(canonical_source, elements, result)
    return result, raw_records


# ── Sidecar artifact ─────────────────────────────────────────────────────────────

def build_elicitation_sidecar(
    canonical_source: CanonicalSource,
    elicitation_results_by_lp: Dict[str, dict],
    deduped_records: List[dict],
    raw_record_count: int,
) -> dict:
    """Assemble the sidecar artifact dict (423C).

    Not live pipeline input. Nothing in Stage 5, `assess_coverage`, Mode C,
    or downstream report generation reads it.
    """
    verified = [r for r in deduped_records if r["verification_status"] == VERIFIED]
    not_verified = [r for r in deduped_records if r["verification_status"] != VERIFIED]
    dedup_ratio = round(raw_record_count / len(deduped_records), 3) if deduped_records else 0.0

    return {
        "_artifact_type": "423C_span_universe_sidecar",
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
        "batching": (
            "per-LP: one call per LP with expected_elements_305, all of that "
            "LP's elements presented in one call as neutral ordinal targets "
            "(Target 1, Target 2, ...). Batching is a cost decision only — "
            "the model is never told the targets are grouped under a provision."
        ),
        "lps_run": list(elicitation_results_by_lp.keys()),
        "elicitation_meta_by_lp": {lp: r["meta"] for lp, r in elicitation_results_by_lp.items()},
        "raw_elicited_span_count": raw_record_count,
        "deduped_span_count": len(deduped_records),
        "dedup_ratio": dedup_ratio,
        "count_verified": len(verified),
        "count_ambiguous": sum(1 for r in deduped_records if r["verification_status"] == AMBIGUOUS),
        "count_unverified": sum(1 for r in deduped_records if r["verification_status"] == UNVERIFIED),
        "elicited_by_is_provenance_not_routing": True,
        "verified_spans": [
            {
                "evidence_span_id": r["evidence_span_id"],
                "start_char": r["start_char"],
                "end_char": r["end_char"],
                "excerpt": r["span_text"][:200],
                "elicited_by": r["elicited_by"],
            }
            for r in verified
        ],
        "ambiguous_or_unverified_spans": [
            {
                "quote_variants_excerpt": [q[:200] for q in r["quote_variants"]],
                "verification_status": r["verification_status"],
                "failure_reason": r["failure_reason"],
                "elicited_by": r["elicited_by"],
            }
            for r in not_verified
        ],
    }
