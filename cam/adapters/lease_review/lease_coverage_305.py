"""
Step 305: Per-element multi-evaluator coverage assessment for pilot LPs.

Replaces the single-pass LP-level keyword assessment with a three-evaluator
per-element analysis for LP-09, LP-11, LP-22, LP-26, LP-27.

Feature flag: STEP_305_ENABLED = False until variance acceptance test passes.
Set to True only after 3-run variance test produces identical element-level
verdicts for all pilot LPs.

Architecture:
- Three evaluators (Claude Sonnet 4.6, GPT-5.5, Grok-4) run in parallel.
- Each evaluator reads the full LP text and returns one verdict per expected element.
- Merge function applies deterministic rules per element (2-of-3 consensus, citation check).
- LP-level coverage_state derived deterministically from merged element verdicts.
- Output is returned to lease_coverage.py which wraps it in the standard assessment dict
  and applies covered_unfavorable/potentially_unenforceable pattern checks on top.

Claim mapping (patent):
- Claim 5: three-evaluator structured assertion per element with policy merge
- Claim 7: element-level unclear routes to review_needed; citation-absent downgrades presence
- Claim 11: per-element verdicts with citation and disagreement trail in audit output
- Claim 12: same multi-eval + deterministic-merge pattern as Stage 5d (architectural homology)
"""

import json
import logging
import threading
import time
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

logger = logging.getLogger(__name__)

# ── Feature flag ───────────────────────────────────────────────────────────────
# Variance acceptance test passed 2026-05-11 on LP-state stability criterion.
# LP-11, LP-26, LP-27 ship; LP-09 and LP-22 remain on legacy path pending element fixes.
# Controlled by _ENABLED_305_LPS in lease_coverage.py.
STEP_305_ENABLED = True

# ── Verdict constants ──────────────────────────────────────────────────────────
VALID_VERDICTS = frozenset({
    "explicitly_present",
    "implicitly_present",
    "covered_by_default_law",
    "covered_in_other_LP",
    "missing",
    "unclear",
})
PRESENCE_VERDICTS = frozenset({
    "explicitly_present",
    "implicitly_present",
    "covered_by_default_law",
    "covered_in_other_LP",
})

# ── Evaluator lineup (mirrors lease_use_aware_coverage.py EVALUATOR_LINEUP) ───
from cam.adapters.lease_review.model_config import (  # noqa: E402
    EVALUATOR_A_PRIMARY, EVALUATOR_A_FALLBACK,
    EVALUATOR_B_PRIMARY, EVALUATOR_B_FALLBACK,
    EVALUATOR_C_PRIMARY, EVALUATOR_C_FALLBACK,
    EVALUATOR_A_LABEL, EVALUATOR_B_LABEL, EVALUATOR_C_LABEL,
    EVALUATOR_A_FALLBACK_LABEL, EVALUATOR_B_FALLBACK_LABEL, EVALUATOR_C_FALLBACK_LABEL,
)

EVALUATOR_LINEUP_305: dict[str, dict] = {
    "A": {
        "provider": EVALUATOR_A_PRIMARY[0],
        "model": EVALUATOR_A_PRIMARY[1],
        "label": EVALUATOR_A_LABEL,
        "max_output_tokens": 3000,
        "temperature": 0.0,
        "timeout_sec": 300.0,
        "own_chain": [(EVALUATOR_A_FALLBACK[0], EVALUATOR_A_FALLBACK[1], EVALUATOR_A_FALLBACK_LABEL)],
    },
    "B": {
        "provider": EVALUATOR_B_PRIMARY[0],
        "model": EVALUATOR_B_PRIMARY[1],
        "label": EVALUATOR_B_LABEL,
        "max_output_tokens": 3000,
        "temperature": 0.0,
        "timeout_sec": 300.0,
        "own_chain": [(EVALUATOR_B_FALLBACK[0], EVALUATOR_B_FALLBACK[1], EVALUATOR_B_FALLBACK_LABEL)],
    },
    "C": {
        "provider": EVALUATOR_C_PRIMARY[0],
        "model": EVALUATOR_C_PRIMARY[1],
        "label": EVALUATOR_C_LABEL,
        "max_output_tokens": 3000,
        "temperature": 0.0,
        "timeout_sec": 300.0,
        "own_chain": [],  # grok-3 retired 2026-05-15; no same-provider fallback
    },
}

_SHARED_FALLBACK_POOL = [
    ("google",  "gemini-2.5-pro",       "Gemini 2.5 Pro"),
    ("mistral", "mistral-large-latest", "Mistral Large"),
]

# ── Prompts ────────────────────────────────────────────────────────────────────
# Locked design paragraph reproduced verbatim from architecture spec §3.
_LOCKED_DESIGN = (
    "Step 305 will not treat negative-space regex output as final evidence. "
    "Regex output is candidate evidence only. Each coverage evaluator must independently "
    "read the full LP text, assess every expected element, determine explicit, implicit, "
    "default-law, or cross-provision coverage, verify or reject regex candidates, and cite "
    "supporting lease text for each element-level verdict. Final LP coverage state is "
    "derived deterministically from per-element evaluator outputs, not from raw regex signals, "
    "not from exposure text, and not from a direct LP-state vote. Any material element-level "
    "assertion without a supporting citation must be downgraded to `unclear` or `review_needed`. "
    "Citation may be a section number reference or a quoted text fragment; bare assertions of "
    "presence without textual grounding do not constitute valid assertion."
)

_SYSTEM_PROMPT = f"""You are a commercial real estate attorney performing per-element coverage analysis of a lease provision.

{_LOCKED_DESIGN}

For each expected element, return exactly one verdict object in the output JSON array:
{{
  "element_id": "<exact element_id from input>",
  "verdict": "<explicitly_present | implicitly_present | covered_by_default_law | covered_in_other_LP | missing | unclear>",
  "citation": {{
    "section_ref": "<section or article reference, or null>",
    "quote": "<short quoted fragment from the lease text, or null>",
    "citation_quality": "<section_and_quote | section_only | none>"
  }},
  "reasoning": "<1-3 sentences explaining your verdict>",
  "confidence": "<high | medium | low>"
}}

Verdict semantics:
- explicitly_present: The element appears as literal or near-literal text. Citation (section_and_quote preferred) is mandatory.
- implicitly_present: Same-LP text functionally satisfies the element without using expected phrasing. Citation required. Only valid when implicit_coverage_acceptable is true.
- covered_by_default_law: Absent from lease but applies by background law per schema annotation. Only valid when default_law_covers is true or "jurisdiction-dependent".
- covered_in_other_LP: Addressed by explicit text in another LP listed in cross_LP_coverage. Citation must name the other LP and its section. Only valid when cross_LP_coverage is non-null.
- missing: Genuinely absent with no coverage path.
- unclear: Text is ambiguous, citation is insufficient, or you cannot reliably determine coverage.

Hard rules:
1. If must_be_explicit is true: only explicitly_present, missing, or unclear are valid verdicts.
2. If implicit_coverage_acceptable is false: implicitly_present is not valid.
3. If default_law_covers is false: covered_by_default_law is not valid.
4. If cross_LP_coverage is null: covered_in_other_LP is not valid.
5. Any presence verdict (explicitly_present, implicitly_present, covered_by_default_law, covered_in_other_LP) requires section_ref in the citation. If section_ref is null, use unclear instead.
6. Your response MUST start with `[` and end with `]`. Do not wrap in an outer object like {{"verdicts": [...]}}. Do not use markdown code fences. No preamble, no text outside the JSON array. Start immediately with `[`."""


def _build_user_prompt(
    pid: str,
    lp_name: str,
    tenant_text: str,
    elements_305: list,
    ns_candidates: list,
    governing_law: Optional[str],
    cross_lp_texts: Optional[dict] = None,
) -> str:
    """Build the per-LP evaluator user prompt."""
    # Serialize elements with fields the evaluator needs
    elements_for_prompt = []
    for el in elements_305:
        elements_for_prompt.append({
            "element_id": el.get("element_id"),
            "element_label": el.get("element_label"),
            "synonyms": el.get("synonyms", []),
            "must_be_explicit": el.get("must_be_explicit", False),
            "implicit_coverage_acceptable": el.get("implicit_coverage_acceptable", False),
            "default_law_covers": el.get("default_law_covers", False),
            "cross_LP_coverage": el.get("cross_LP_coverage"),
            "absence_severity": el.get("absence_severity"),
        })

    # Step 320: GPT-5.5 returns empty output when the provision is absent from the lease.
    # Detect absent text and add an explicit instruction before the element list.
    if not tenant_text or len(tenant_text.strip()) < 50:
        empty_note = (
            "NOTE: No provision text was found for this issue area. "
            "The lease is silent on this topic. Return verdict 'missing' for every "
            "element. Do not return an empty response — a complete JSON array is required."
        )
    else:
        empty_note = ""

    lines = [
        f"LP: {pid} -- {lp_name}",
        f"GOVERNING LAW: {governing_law or 'Not specified'}",
        "",
    ]
    if empty_note:
        lines += [empty_note, ""]
    lines += [
        f"EXPECTED ELEMENTS ({len(elements_305)} total):",
        json.dumps(elements_for_prompt, indent=2),
        "",
    ]

    if ns_candidates:
        ns_summary = [
            {"signal_type": s.get("signal_type"), "evidence": s.get("evidence", "")[:80]}
            for s in ns_candidates[:10]
        ]
        lines += [
            "NEGATIVE SPACE CANDIDATES (candidate evidence only -- verify against lease text):",
            json.dumps(ns_summary, indent=2),
            "",
        ]

    lines += [
        "LEASE PROVISION TEXT:",
        tenant_text or "(no provision text extracted)",
        "",
    ]

    if cross_lp_texts:
        lines += [
            "CROSS-PROVISION REFERENCE TEXT:",
            "The following provision text is provided because one or more elements in this",
            "assessment may be covered by a different provision. Use this text to evaluate",
            "cross-LP coverage where the element's cross_LP_coverage field references these LPs.",
            "",
        ]
        for ref_pid, ref_text in cross_lp_texts.items():
            lines += [f"{ref_pid}: {(ref_text or '')[:1200]}", ""]

    lines += [
        f"Return a JSON array of exactly {len(elements_305)} verdict objects, one per element "
        f"in the order listed above.",
    ]
    return "\n".join(lines)


# ── Single-evaluator call (mirrors Stage 5d _call_single_evaluator) ────────────

def _call_single_evaluator_305(
    role: str,
    evaluator_cfg: dict,
    pid: str,
    lp_name: str,
    tenant_text: str,
    elements_305: list,
    ns_candidates: list,
    governing_law: Optional[str],
    cfg: dict,
    claimed_providers: set,
    claimed_lock: threading.Lock,
    pool_claimed: list,
    pool_lock: threading.Lock,
) -> dict:
    """Call one evaluator and return per-element verdict array.

    Returns:
        {role, model, provider, label, completed, elapsed_sec,
         element_verdicts (list|None), error (str|None)}
    """
    from cam.core.provider_router import ModelTarget, ProviderRouter, RouterConfig
    from cam.core.json_extract import safe_json_extract
    from cam.core.provider_health import get_health_tracker

    health = get_health_tracker()
    start_time = time.time()
    errors: list[str] = []

    user_prompt = _build_user_prompt(pid, lp_name, tenant_text, elements_305, ns_candidates, governing_law, cross_lp_texts=cfg.get("_cross_lp_texts"))

    def _try_claim(provider: str) -> bool:
        with claimed_lock:
            if provider in claimed_providers:
                return False
            claimed_providers.add(provider)
            return True

    def _release_claim(provider: str) -> None:
        with claimed_lock:
            claimed_providers.discard(provider)

    def _try_call(provider: str, model: str, label: str) -> list:
        """Attempt one model call. Returns parsed list of verdict dicts."""
        if not health.is_available(provider):
            raise RuntimeError(f"provider {provider} degraded")
        if not _try_claim(provider):
            raise RuntimeError(f"provider {provider} already claimed by another evaluator")
        print(f"[lease_coverage_305] Eval-{role} ({pid}): calling {model} ({provider})...", flush=True)
        try:
            # Scale token budget with element count: ~300 tokens per verdict + 500 overhead.
            # LP-11 has 17 elements; 3000 tokens was too small and caused truncation.
            _tokens = max(evaluator_cfg.get("max_output_tokens", 3000),
                         len(elements_305) * 300 + 500)
            target = ModelTarget(
                name=f"{provider}:{model}-305-{role}-{pid}",
                provider=provider,
                model=model,
                max_output_tokens=_tokens,
                temperature=evaluator_cfg.get("temperature", 0.0),
                timeout_sec=evaluator_cfg.get("timeout_sec", 300.0),
            )
            router = ProviderRouter([target], RouterConfig())
            adapter = router._get_adapter(provider)
            raw = adapter.call(_SYSTEM_PROMPT, user_prompt, target).strip()
            # Strip markdown code fences (Gemini and some models wrap in ```json ... ```)
            if raw.startswith("```"):
                raw = re.sub(r"^```(?:json)?\s*", "", raw)
                raw = re.sub(r"\s*```\s*$", "", raw)
            # Try json.loads first: safe_json_extract extracts the last JSON object
            # it finds, which mangles a bare array by returning only the final element.
            # json.loads correctly parses arrays; fall back to safe_json_extract only
            # for responses that need object-hunting (malformed/prefixed responses).
            try:
                parsed = json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                parsed = safe_json_extract(raw)
            # All major model families wrap the verdict array in an outer object.
            # Handle two observed patterns:
            #   Pattern 1: {"verdicts": [...], "element_verdicts": [...]}
            #              — dict with a list value; extract that list.
            #   Pattern 2: {"LP-09.elem1": {verdict_dict}, "LP-09.elem2": {...}}
            #              — dict-of-dicts where every value is a verdict object;
            #                convert to list of values.
            if isinstance(parsed, dict):
                _unwrapped = None
                # Pattern 1a: find the first value that is a non-empty list of dicts
                for _val in parsed.values():
                    if isinstance(_val, list) and _val and isinstance(_val[0], dict):
                        _unwrapped = _val
                        break
                # Pattern 1b: any list value (even empty)
                if _unwrapped is None:
                    for _val in parsed.values():
                        if isinstance(_val, list):
                            _unwrapped = _val
                            break
                # Pattern 2: dict-of-dicts — every value is a verdict object
                if _unwrapped is None:
                    _dict_vals = list(parsed.values())
                    if _dict_vals and all(isinstance(v, dict) for v in _dict_vals):
                        _unwrapped = _dict_vals
                if _unwrapped is not None:
                    parsed = _unwrapped
            if not isinstance(parsed, list):
                raise ValueError(f"Response is not a list (got {type(parsed).__name__})")
            return parsed
        except Exception:
            _release_claim(provider)
            raise

    # Phase 1: own-provider chain (primary + fallback)
    own_candidates = [(evaluator_cfg["provider"], evaluator_cfg["model"], evaluator_cfg["label"])]
    for entry in evaluator_cfg.get("own_chain", []):
        own_candidates.append(entry)

    for provider, model, label in own_candidates:
        try:
            verdicts = _try_call(provider, model, label)
            elapsed = time.time() - start_time
            logger.info(f"[lease_coverage_305] Eval-{role} ({pid}, {label}) succeeded in {elapsed:.1f}s")
            return {
                "role": role, "model": model, "provider": provider, "label": label,
                "completed": True, "elapsed_sec": round(elapsed, 2),
                "element_verdicts": verdicts, "error": None,
            }
        except Exception as e:
            errors.append(f"{model}: {e}")
            print(f"[lease_coverage_305] Eval-{role} ({pid}): {model} FAILED: {e}", flush=True)

    # Phase 2: shared fallback pool
    print(f"[lease_coverage_305] Eval-{role} ({pid}): own chain exhausted, trying shared pool", flush=True)
    while True:
        pool_entry = None
        with pool_lock:
            for entry in _SHARED_FALLBACK_POOL:
                if entry[0] not in pool_claimed:
                    pool_claimed.append(entry[0])
                    pool_entry = entry
                    break
        if pool_entry is None:
            break
        provider, model, label = pool_entry
        try:
            verdicts = _try_call(provider, model, label)
            elapsed = time.time() - start_time
            return {
                "role": role, "model": model, "provider": provider, "label": label,
                "completed": True, "elapsed_sec": round(elapsed, 2),
                "element_verdicts": verdicts, "error": None,
            }
        except Exception as e:
            errors.append(f"pool/{model}: {e}")
            print(f"[lease_coverage_305] Eval-{role} ({pid}): pool/{model} FAILED: {e}", flush=True)

    elapsed = time.time() - start_time
    logger.warning(f"[lease_coverage_305] Eval-{role} ({pid}): all attempts failed: {errors}")
    return {
        "role": role, "model": evaluator_cfg["model"], "provider": evaluator_cfg["provider"],
        "label": evaluator_cfg["label"],
        "completed": False, "elapsed_sec": round(elapsed, 2),
        "element_verdicts": None, "error": "; ".join(errors),
    }


def _run_three_evaluators_305(
    pid: str,
    lp_name: str,
    tenant_text: str,
    elements_305: list,
    ns_candidates: list,
    governing_law: Optional[str],
    cfg: dict,
) -> dict[str, dict]:
    """Run three Step 305 evaluators in parallel for one LP.

    Returns dict keyed by role ("A", "B", "C").
    """
    claimed_providers: set = set()
    claimed_lock = threading.Lock()
    pool_claimed: list = []
    pool_lock = threading.Lock()
    results: dict[str, dict] = {}

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(
                _call_single_evaluator_305,
                role, cfg_ev, pid, lp_name, tenant_text, elements_305,
                ns_candidates, governing_law, cfg,
                claimed_providers, claimed_lock, pool_claimed, pool_lock,
            ): role
            for role, cfg_ev in EVALUATOR_LINEUP_305.items()
        }
        for future in as_completed(futures):
            role = futures[future]
            try:
                results[role] = future.result()
            except Exception as e:
                results[role] = {
                    "role": role, "model": EVALUATOR_LINEUP_305[role]["model"],
                    "provider": EVALUATOR_LINEUP_305[role]["provider"],
                    "label": EVALUATOR_LINEUP_305[role]["label"],
                    "completed": False, "elapsed_sec": 0.0,
                    "element_verdicts": None, "error": str(e),
                }

    succeeded = sum(1 for r in results.values() if r["completed"])
    logger.info(f"[lease_coverage_305] {pid}: {succeeded}/3 evaluators completed")
    return results


# ── Per-element verdict normalization ──────────────────────────────────────────

def _normalize_verdict(raw_verdict: str, element: dict) -> str:
    """Normalize a raw verdict string and enforce schema constraints."""
    v = (raw_verdict or "").strip().lower()
    # Map common model mis-spellings
    _alias = {
        "explicit": "explicitly_present",
        "explicit_present": "explicitly_present",
        "implicit": "implicitly_present",
        "implicit_present": "implicitly_present",
        "default_law": "covered_by_default_law",
        "default_law_covered": "covered_by_default_law",
        "other_lp": "covered_in_other_LP",
        "cross_lp": "covered_in_other_LP",
        "covered_in_other_lp": "covered_in_other_LP",
        "absent": "missing",
        "not_present": "missing",
    }
    v = _alias.get(v, v)
    if v not in VALID_VERDICTS:
        return "unclear"

    # Enforce schema constraints
    if v == "implicitly_present" and not element.get("implicit_coverage_acceptable", False):
        return "unclear"
    if v == "covered_by_default_law" and not element.get("default_law_covers", False):
        return "unclear"
    if v == "covered_in_other_LP" and not element.get("cross_LP_coverage"):
        return "unclear"
    if v in PRESENCE_VERDICTS and element.get("must_be_explicit") and v != "explicitly_present":
        return "unclear"

    return v


def _extract_verdicts_for_element(
    evaluator_results: dict[str, dict],
    element_id: str,
    element: dict,
) -> list[dict]:
    """Extract and normalize each evaluator's verdict for one element."""
    verdicts = []
    for role, result in evaluator_results.items():
        if not result.get("completed") or not result.get("element_verdicts"):
            verdicts.append({
                "role": role,
                "label": EVALUATOR_LINEUP_305.get(role, {}).get("label", f"Evaluator {role}"),
                "verdict": "unclear",
                "citation": None,
                "reasoning": f"Evaluator {role} did not complete",
                "confidence": "low",
            })
            continue

        # Find this element in the evaluator's output
        raw_list = result["element_verdicts"]
        match = None
        for item in raw_list:
            if isinstance(item, dict) and item.get("element_id") == element_id:
                match = item
                break

        if match is None:
            verdicts.append({
                "role": role,
                "label": EVALUATOR_LINEUP_305.get(role, {}).get("label", f"Evaluator {role}"),
                "verdict": "unclear",
                "citation": None,
                "reasoning": f"Evaluator {role} did not include verdict for this element",
                "confidence": "low",
            })
            continue

        raw_verdict = match.get("verdict", "unclear")
        normalized = _normalize_verdict(raw_verdict, element)

        # Citation normalization
        citation = match.get("citation")
        if isinstance(citation, dict):
            citation = {
                "section_ref": citation.get("section_ref"),
                "quote": citation.get("quote"),
                "citation_quality": citation.get("citation_quality", "none"),
            }
        elif isinstance(citation, str):
            citation = {"section_ref": citation, "quote": None, "citation_quality": "section_only"}
        else:
            citation = None

        verdicts.append({
            "role": role,
            "label": EVALUATOR_LINEUP_305.get(role, {}).get("label", f"Evaluator {role}"),
            "verdict": normalized,
            "citation": citation,
            "reasoning": match.get("reasoning", ""),
            "confidence": match.get("confidence", "low"),
        })
    return verdicts


# ── Element-level merge ────────────────────────────────────────────────────────

def merge_element_verdicts(verdicts: list[dict], element: dict) -> dict:
    """Merge 3 evaluator verdicts for one element per architecture spec §6.

    Returns merged verdict dict with confidence and disagreement trail.
    """
    # Filter out unclear for consensus calculation (unclear = abstain from consensus)
    active = [v for v in verdicts if v["verdict"] != "unclear"]

    if not active:
        return {
            "verdict": "unclear",
            "confidence": "low",
            "citation": None,
            "reason": "all_evaluators_unclear",
            "disagreements": verdicts,
        }

    counts = Counter(v["verdict"] for v in active)
    majority_verdict, majority_count = counts.most_common(1)[0]

    if majority_count < 2:
        # All three active verdicts differ
        return {
            "verdict": "unclear",
            "confidence": "low",
            "citation": None,
            "reason": "no_consensus",
            "disagreements": verdicts,
        }

    # ── Disputed gate (Supplement #21 Phase 1) ───────────────────────────────
    # If active verdicts span both presence and missing — the disagreement crosses
    # the presence/absence divide (maximally-distant ordinal split per the verdict
    # ladder). Per the action-type doctrine CAM cannot safely classify the rubric
    # criterion as met or unmet; merged verdict is `disputed` not the majority winner.
    has_presence = any(v["verdict"] in PRESENCE_VERDICTS for v in active)
    has_missing  = any(v["verdict"] == "missing" for v in active)
    if has_presence and has_missing:
        return {
            "verdict": "disputed",
            "confidence": "low",
            "citation": None,
            "reason": "distant_split_presence_missing",
            "disagreements": verdicts,  # preserve ALL evaluators (not just dissents)
        }

    # 2-of-3 or 3-of-3 consensus
    confidence = "high" if majority_count == len(verdicts) else "medium"
    majority_citations = [
        v["citation"] for v in active
        if v["verdict"] == majority_verdict and v["citation"]
    ]
    dissents = [v for v in verdicts if v["verdict"] != majority_verdict]

    # Citation-or-it-didn't-happen check (architecture spec §6)
    if majority_verdict in PRESENCE_VERDICTS:
        valid_citations = [
            c for c in majority_citations
            if c and c.get("section_ref")
        ]
        if not valid_citations:
            return {
                "verdict": "unclear",
                "confidence": "low",
                "citation": None,
                "reason": "citation_required_but_absent",
                "disagreements": verdicts,
            }
        chosen_citation = valid_citations[0]
    else:
        chosen_citation = None

    return {
        "verdict": majority_verdict,
        "confidence": confidence,
        "citation": chosen_citation,
        "reason": None,
        "disagreements": dissents if dissents else None,
    }


# ── LP-state derivation from element verdicts ─────────────────────────────────

def derive_lp_state(element_results: list[dict], elements_305: list[dict]) -> str:
    """Derive LP-level coverage_state from merged element verdicts per architecture spec §7.

    Does NOT apply covered_unfavorable or potentially_unenforceable — those are
    applied by the caller (lease_coverage.py routing) using the existing pattern checks.
    """
    if not element_results:
        return "review_needed"

    high_severity_ids = {
        e["element_id"] for e in elements_305
        if e.get("absence_severity") == "high"
    }

    any_unclear = any(r["verdict"] == "unclear" for r in element_results)
    all_positive = all(r["verdict"] in PRESENCE_VERDICTS for r in element_results)
    # Supplement #21 Phase 1: treat disputed as missing for LP-state derivation
    # (conservative; Phase 3 will add criticality-gated propagation to Review Needed).
    missing_or_disputed = [r for r in element_results if r["verdict"] in ("missing", "disputed")]
    high_severity_missing = any(r["element_id"] in high_severity_ids for r in missing_or_disputed)

    if any_unclear:
        return "review_needed"

    if all_positive:
        return "covered"

    total = len(element_results)
    n_missing = len(missing_or_disputed)

    if high_severity_missing:
        # Many missing elements → missing; some → partial
        if n_missing > total // 2:
            return "missing"
        return "partial"

    if n_missing > 0:
        return "partial"

    return "covered"


# ── Main entry point ───────────────────────────────────────────────────────────

def assess_coverage_305(
    pid: str,
    area: dict,
    tenant_text: str,
    elements_305: list,
    negative_space_candidates: list,
    governing_law: Optional[str] = None,
    cfg: Optional[dict] = None,
    all_lp_texts: Optional[dict] = None,
) -> dict:
    """Per-element multi-evaluator coverage assessment for one pilot LP.

    Returns a lightweight result dict. The caller (lease_coverage.py routing)
    wraps this in the standard assessment dict and applies pattern-check upgrades
    (covered_unfavorable, potentially_unenforceable).

    Returns:
        {
            "coverage_state_baseline": str,
            "coverage_method": "step_305_per_element",
            "evidence_summary": str,
            "element_verdicts": list[dict],
            "elements_present": list[str],     # element_label strings
            "elements_missing": list[str],      # element_label strings
            "negative_space_candidates_reviewed": list,
            "evaluator_meta": dict,
        }
    """
    if cfg is None:
        cfg = {}

    # Inject cross-LP texts into cfg so _call_single_evaluator_305 can pass them to the prompt.
    # Only include LP IDs referenced in this LP's elements' cross_LP_coverage fields.
    if all_lp_texts:
        referenced_lps = set()
        for el in elements_305:
            for ref in (el.get("cross_LP_coverage") or []):
                referenced_lps.add(ref)
        if referenced_lps:
            cfg = dict(cfg)  # don't mutate caller's dict
            cfg["_cross_lp_texts"] = {
                lp: all_lp_texts[lp] for lp in referenced_lps if lp in all_lp_texts
            }

    lp_name = area.get("name", pid)
    t0 = time.time()

    logger.info(f"[lease_coverage_305] Starting per-element assessment: {pid} ({len(elements_305)} elements)")

    # ── 1. Run three evaluators in parallel ───────────────────────────────────
    evaluator_results = _run_three_evaluators_305(
        pid=pid,
        lp_name=lp_name,
        tenant_text=tenant_text,
        elements_305=elements_305,
        ns_candidates=negative_space_candidates,
        governing_law=governing_law,
        cfg=cfg,
    )

    succeeded = sum(1 for r in evaluator_results.values() if r["completed"])
    if succeeded == 0:
        logger.error(f"[lease_coverage_305] {pid}: all 3 evaluators failed — returning review_needed")
        return {
            "coverage_state_baseline": "review_needed",
            "coverage_method": "step_305_per_element",
            "evidence_summary": "All evaluators failed; manual review required",
            "element_verdicts": [],
            "elements_present": [],
            "elements_missing": [e.get("element_label", e.get("element_id", "")) for e in elements_305],
            "negative_space_candidates_reviewed": negative_space_candidates,
            "evaluator_meta": {r: {"completed": False} for r in evaluator_results},
        }

    # ── 2. Merge per-element verdicts ─────────────────────────────────────────
    element_verdicts_merged = []
    elements_present = []
    elements_missing = []
    elements_disputed = []   # Supplement #21 Phase 1
    elements_disputed_critical = 0   # Step 355: Phase 2 criticality counters
    elements_disputed_important = 0  # Step 355: Phase 2 criticality counters

    for element in elements_305:
        element_id = element.get("element_id", "")
        element_label = element.get("element_label", element_id)
        criticality = element.get("criticality", "important")  # Phase 2 pass-through

        per_evaluator = _extract_verdicts_for_element(evaluator_results, element_id, element)
        merged = merge_element_verdicts(per_evaluator, element)

        verdict_record = {
            "element_id": element_id,
            "criticality": criticality,  # Phase 2 pass-through
            "element_label": element_label,
            "verdict": merged["verdict"],
            "confidence": merged.get("confidence", "low"),
            "citation": merged.get("citation"),
            "reason": merged.get("reason"),
            "evaluator_verdicts": per_evaluator,
            "disagreements": merged.get("disagreements"),
        }
        element_verdicts_merged.append(verdict_record)

        if merged["verdict"] in PRESENCE_VERDICTS:
            elements_present.append(element_label)
        elif merged["verdict"] == "missing":
            elements_missing.append(element_label)
        elif merged["verdict"] == "disputed":
            elements_disputed.append(element_label)
            if criticality == "critical":        # Step 355: track criticality of disputed elements
                elements_disputed_critical += 1
            elif criticality == "important":
                elements_disputed_important += 1

    # ── 3. Derive LP-level coverage state ─────────────────────────────────────
    coverage_state_baseline = derive_lp_state(element_verdicts_merged, elements_305)

    # ── 3a. Compute LP-level verdict distance (Architecture A Phase 2) ────────
    verdict_distance = None
    lp_confidence_base = "low"
    per_evaluator_lp_verdicts = {}
    try:
        from cam.adapters.lease_review.lease_verdict_distance import (
            derive_per_evaluator_lp_verdict,
            derive_disagreement_severity,
        )
        completed_roles = [role for role, r in evaluator_results.items() if r.get("completed") and r.get("element_verdicts")]
        if len(completed_roles) >= 2:
            for role in completed_roles:
                raw_list = evaluator_results[role]["element_verdicts"]
                role_verdicts = []
                for el in elements_305:
                    eid = el.get("element_id", "")
                    match = next((item for item in raw_list if isinstance(item, dict) and item.get("element_id") == eid), None)
                    if match:
                        role_verdicts.append(_normalize_verdict(match.get("verdict", "unclear"), el))
                    else:
                        role_verdicts.append("unclear")
                per_evaluator_lp_verdicts[role] = derive_per_evaluator_lp_verdict(role_verdicts)

            lp_verdict_list = list(per_evaluator_lp_verdicts.values())
            verdict_distance = derive_disagreement_severity(lp_verdict_list)

            # LP-level confidence from vote count on the LP-level verdicts
            from collections import Counter as _Counter
            _lp_counts = _Counter(lp_verdict_list)
            _majority_count = _lp_counts.most_common(1)[0][1] if _lp_counts else 1
            if _majority_count == len(lp_verdict_list):
                lp_confidence_base = "high"
            elif _majority_count >= 2:
                lp_confidence_base = "medium"
            else:
                lp_confidence_base = "low"
        else:
            verdict_distance = None
    except Exception as _vd_exc:
        logger.warning(f"[lease_coverage_305] {pid}: verdict distance computation failed: {_vd_exc}")

    # ── 4. Build evidence summary ─────────────────────────────────────────────
    n_present   = len(elements_present)
    n_missing   = len(elements_missing)
    n_disputed  = len(elements_disputed)
    n_unclear   = sum(1 for v in element_verdicts_merged if v["verdict"] == "unclear")
    elapsed     = round(time.time() - t0, 1)

    _disputed_phrase = f", {n_disputed} disputed" if n_disputed else ""
    evidence_summary = (
        f"Step 305 per-element assessment ({n_present} present, "
        f"{n_missing} missing{_disputed_phrase}, {n_unclear} unclear of {len(elements_305)} elements; "
        f"{succeeded}/3 evaluators; {elapsed}s)"
    )

    evaluator_meta = {
        role: {
            "completed": r["completed"],
            "model": r["model"],
            "elapsed_sec": r["elapsed_sec"],
            "error": r.get("error"),
        }
        for role, r in evaluator_results.items()
    }

    logger.info(
        f"[lease_coverage_305] {pid}: {coverage_state_baseline} | "
        f"{n_present} present, {n_missing} missing, {n_disputed} disputed, {n_unclear} unclear | {elapsed}s"
    )

    return {
        "coverage_state_baseline": coverage_state_baseline,
        "coverage_method": "step_305_per_element",
        "evidence_summary": evidence_summary,
        "element_verdicts": element_verdicts_merged,
        "elements_present": elements_present,
        "elements_missing": elements_missing,
        "elements_disputed": elements_disputed,          # Supplement #21 Phase 1
        "elements_disputed_critical": elements_disputed_critical,   # Step 355 Phase 2
        "elements_disputed_important": elements_disputed_important, # Step 355 Phase 2
        "negative_space_candidates_reviewed": negative_space_candidates,
        "evaluator_meta": evaluator_meta,
        "api_calls": succeeded,  # Step 335: number of evaluator API calls made for this LP
        # Step 351: Architecture A Phase 2 — verdict distance at LP layer
        "verdict_distance": verdict_distance,
        "lp_confidence_base": lp_confidence_base,
        "per_evaluator_lp_verdicts": per_evaluator_lp_verdicts,
    }
