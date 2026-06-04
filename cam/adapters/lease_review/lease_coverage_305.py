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

# ── Step 372c: budget sizing + B-prompt-split constants ───────────────────────
# Per-mechanism budget fix (NOT one-size). A (Sonnet) truncates because its verbose
# reasoning + section_ref + quote per element needs ~500–700 output tokens/element;
# the old 300/elem floor was too low. Raise the per-element output rate so A's full
# output fits (compute-from-output-need principle).
PER_ELEMENT_OUTPUT_TOKENS = 600
BASE_OUTPUT_OVERHEAD = 1000
# B (gpt-5.x) does NOT fail on output size — it reasoning-token-exhausts on INPUT
# complexity (many elements → more thinking before output). More max_output_tokens
# does not help; the prompt must be split into smaller element batches so each
# sub-call's reasoning load fits. Split is B-specific (gated on gpt-5.x); A and C
# never split. Shape-preserving: one verdict per element, merged by element_id.
B_SPLIT_BATCH_SIZE = 8


def _compute_output_budget(evaluator_cfg: dict, n_elements: int) -> int:
    """Output-token budget computed from output need (Step 372c).

    Floored at the evaluator's configured default so we never shrink below the
    prior baseline. Raising the ceiling is prevention-only and (at temperature 0)
    does not change a completion that already fit — verdicts stay byte-identical
    on a clean no-truncation run.
    """
    return max(evaluator_cfg.get("max_output_tokens", 3000),
               n_elements * PER_ELEMENT_OUTPUT_TOKENS + BASE_OUTPUT_OVERHEAD)


def _is_split_model(model: str) -> bool:
    """B-split gate: only gpt-5.x evaluators batch their prompt (Step 372c)."""
    return (model or "").lower().startswith("gpt-5")


def _classify_failure(error_msg: str, model: str) -> str:
    """Classify why a primary evaluator call failed (Step 372c observability).

    Mapping (per spec): empty content → reasoning_exhaustion for gpt-5.x; unclosed
    array → truncation; HTTP/timeout/rate → api_error. Recorded where the fallback
    fires so budget pressure is queryable from run metadata, not a future probe.
    """
    m = (error_msg or "").lower()
    if "degraded" in m or "already claimed" in m:
        return "provider_unavailable"
    if ("_error:" in m or "timeout" in m or "timed out" in m or "rate" in m
            or "429" in m or "connection" in m or "unauthorized" in m
            or "401" in m or " 500" in m or " 502" in m or " 503" in m):
        return "api_error"
    if "empty_content" in m or "empty content" in m:
        return "reasoning_exhaustion" if _is_split_model(model) else "empty_response"
    if "truncation" in m:
        return "truncation"
    if "malformed" in m or "not a list" in m or "nonetype" in m:
        return "reasoning_exhaustion" if _is_split_model(model) else "malformed_response"
    return "unknown"


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
    # Step 372c: per-attempt failure classifications, so a fallback can record WHY
    # the primary failed (reasoning_exhaustion / truncation / api_error / ...).
    attempt_failures: list[dict] = []

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

    def _parse_verdict_list(raw: str, truncated: bool, model: str) -> list:
        """Parse one adapter response into a verdict list (shared by all sub-calls)."""
        if raw == "":
            # gpt-5.x returns empty when reasoning-token-exhausted; others = empty_response.
            raise ValueError("empty_content: model returned no output")
        # Try json.loads first: safe_json_extract extracts the last JSON object it finds,
        # which mangles a bare array by returning only the final element. json.loads
        # correctly parses arrays; fall back to safe_json_extract only for responses that
        # need object-hunting (malformed/prefixed responses).
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            parsed = safe_json_extract(raw)
        # All major model families sometimes wrap the verdict array in an outer object.
        #   Pattern 1: {"verdicts": [...]} — dict with a list value; extract that list.
        #   Pattern 2: {"LP-09.elem1": {...}, ...} — dict-of-dicts; convert to list.
        if isinstance(parsed, dict):
            _unwrapped = None
            for _val in parsed.values():
                if isinstance(_val, list) and _val and isinstance(_val[0], dict):
                    _unwrapped = _val
                    break
            if _unwrapped is None:
                for _val in parsed.values():
                    if isinstance(_val, list):
                        _unwrapped = _val
                        break
            if _unwrapped is None:
                _dict_vals = list(parsed.values())
                if _dict_vals and all(isinstance(v, dict) for v in _dict_vals):
                    _unwrapped = _dict_vals
            if _unwrapped is not None:
                parsed = _unwrapped
        if not isinstance(parsed, list):
            # Distinguish truncation (unclosed structure) from reasoning exhaustion so
            # _classify_failure can attribute the fallback correctly (Step 372c).
            if truncated:
                raise ValueError(f"truncation: response not a list (unclosed, got {type(parsed).__name__})")
            raise ValueError(f"malformed: response not a list (got {type(parsed).__name__})")
        return parsed

    def _do_single_call(provider: str, model: str, batch_elements: list, prompt: str) -> tuple:
        """One adapter call + parse for one element batch. Returns (parsed_list, sub_meta).

        sub_meta carries per-call observability: requested_budget, raw_char_len,
        truncated, and real usage from the adapter (Step 372c) when available.
        """
        budget = _compute_output_budget(evaluator_cfg, len(batch_elements))
        target = ModelTarget(
            name=f"{provider}:{model}-305-{role}-{pid}",
            provider=provider,
            model=model,
            max_output_tokens=budget,
            temperature=evaluator_cfg.get("temperature", 0.0),
            timeout_sec=evaluator_cfg.get("timeout_sec", 300.0),
        )
        router = ProviderRouter([target], RouterConfig())
        adapter = router._get_adapter(provider)
        raw = (adapter.call(_SYSTEM_PROMPT, prompt, target) or "").strip()
        raw_char_len = len(raw)
        # Step 372c: real token usage if the adapter surfaced it (None → estimate later)
        usage = getattr(adapter, "last_usage", None)
        # Strip markdown code fences (Gemini and some models wrap in ```json ... ```)
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```\s*$", "", raw)
            raw = raw.strip()
        empty = (raw == "")
        # Truncation: a complete array/object ends with ] or }; if not, it was cut off.
        truncated = (not empty) and not (raw.endswith("]") or raw.endswith("}"))
        parsed = _parse_verdict_list(raw, truncated, model)
        sub_meta = {
            "requested_budget": budget,
            "raw_char_len": raw_char_len,
            "truncated": truncated,
            "usage": usage,
        }
        return parsed, sub_meta

    def _try_call(provider: str, model: str, label: str) -> tuple:
        """Attempt one evaluator call (possibly split into element batches for gpt-5.x).

        Returns (merged parsed verdict list, call_meta dict). The B-split is invisible
        to the merge layer: sub-call verdict arrays are concatenated by element_id, so
        the result is shape-identical to an unsplit call (one verdict per element).

        call_meta carries admin-side budget observability (Step 372a/372c):
        requested_budget, actual_output_tokens (real when the adapter surfaces usage,
        else a char/4 estimate flagged by usage_source), budget_utilization_pct,
        truncated, n_subcalls, split_applied.
        """
        if not health.is_available(provider):
            raise RuntimeError(f"provider {provider} degraded")
        if not _try_claim(provider):
            raise RuntimeError(f"provider {provider} already claimed by another evaluator")
        print(f"[lease_coverage_305] Eval-{role} ({pid}): calling {model} ({provider})...", flush=True)
        try:
            # Step 372c: B (gpt-5.x) splits long element lists into ≤ B_SPLIT_BATCH_SIZE
            # batches to bound reasoning load. A and C never split. Each sub-call shares
            # the SAME system prompt + lease text; only the element subset differs.
            split_applied = _is_split_model(model) and len(elements_305) > B_SPLIT_BATCH_SIZE
            if split_applied:
                batches = [elements_305[i:i + B_SPLIT_BATCH_SIZE]
                           for i in range(0, len(elements_305), B_SPLIT_BATCH_SIZE)]
                print(f"[lease_coverage_305] Eval-{role} ({pid}): splitting {len(elements_305)} "
                      f"elements into {len(batches)} batches of <={B_SPLIT_BATCH_SIZE} for {model}", flush=True)
            else:
                batches = [elements_305]

            all_verdicts: list = []
            agg_raw_char = 0
            agg_truncated = False
            agg_requested = 0
            agg_out_tokens = 0
            any_real_usage = False
            for batch in batches:
                sub_prompt = (user_prompt if not split_applied
                              else _build_user_prompt(pid, lp_name, tenant_text, batch,
                                                      ns_candidates, governing_law,
                                                      cross_lp_texts=cfg.get("_cross_lp_texts")))
                parsed, sub_meta = _do_single_call(provider, model, batch, sub_prompt)
                all_verdicts.extend(parsed)
                agg_raw_char += sub_meta["raw_char_len"]
                agg_truncated = agg_truncated or sub_meta["truncated"]
                agg_requested += sub_meta["requested_budget"]
                _u = sub_meta["usage"]
                if _u and _u.get("output_tokens") is not None:
                    any_real_usage = True
                    agg_out_tokens += _u["output_tokens"]

            # Budget utilization: real usage when surfaced, else a char/4 token estimate.
            if any_real_usage:
                actual_out = agg_out_tokens
                usage_source = "adapter"
            else:
                actual_out = max(1, round(agg_raw_char / 4))  # ~4 chars/token heuristic
                usage_source = "estimate_char4"
            util_pct = round(100.0 * actual_out / agg_requested, 1) if agg_requested else None
            call_meta = {
                "requested_budget": agg_requested,
                "max_output_tokens": agg_requested,           # 372a-compatible alias
                "actual_output_tokens": actual_out,
                "budget_utilization_pct": util_pct,
                # 372a fields: only populate the "used"/"utilization" pair from REAL usage
                "output_tokens_used": agg_out_tokens if any_real_usage else None,
                "output_utilization": (round(agg_out_tokens / agg_requested, 4)
                                       if (any_real_usage and agg_requested) else None),
                "usage_source": usage_source,
                "finish_reason": None,
                "truncated": agg_truncated,
                "raw_char_len": agg_raw_char,
                "n_subcalls": len(batches),
                "split_applied": split_applied,
            }
            return all_verdicts, call_meta
        except Exception as e:
            _release_claim(provider)
            attempt_failures.append({
                "provider": provider, "model": model,
                "reason": _classify_failure(str(e), model), "error": str(e),
            })
            raise

    # Phase 1: own-provider chain (primary + fallback)
    own_candidates = [(evaluator_cfg["provider"], evaluator_cfg["model"], evaluator_cfg["label"])]
    for entry in evaluator_cfg.get("own_chain", []):
        own_candidates.append(entry)

    for _idx, (provider, model, label) in enumerate(own_candidates):
        try:
            verdicts, call_meta = _try_call(provider, model, label)
            elapsed = time.time() - start_time
            logger.info(f"[lease_coverage_305] Eval-{role} ({pid}, {label}) succeeded in {elapsed:.1f}s")
            # Step 372c: if this was NOT the primary, record why the primary fell back.
            _fb_reason = attempt_failures[0]["reason"] if (_idx > 0 and attempt_failures) else None
            _fb_stage = "305" if _idx > 0 else None
            return {
                "role": role, "model": model, "provider": provider, "label": label,
                "completed": True, "elapsed_sec": round(elapsed, 2),
                "element_verdicts": verdicts, "error": None,
                "fallback_reason": _fb_reason, "fallback_trigger_stage": _fb_stage,
                **call_meta,
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
            verdicts, call_meta = _try_call(provider, model, label)
            elapsed = time.time() - start_time
            _fb_reason = attempt_failures[0]["reason"] if attempt_failures else None
            return {
                "role": role, "model": model, "provider": provider, "label": label,
                "completed": True, "elapsed_sec": round(elapsed, 2),
                "element_verdicts": verdicts, "error": None,
                "fallback_reason": _fb_reason, "fallback_trigger_stage": "305",
                **call_meta,
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
        # Step 372a/372c: no successful call — record the budget that would have been used.
        "requested_budget": _compute_output_budget(evaluator_cfg, len(elements_305)),
        "max_output_tokens": _compute_output_budget(evaluator_cfg, len(elements_305)),
        "actual_output_tokens": None, "budget_utilization_pct": None,
        "output_tokens_used": None, "output_utilization": None,
        "usage_source": None, "n_subcalls": 0, "split_applied": False,
        "finish_reason": None, "truncated": False,
        "fallback_reason": attempt_failures[0]["reason"] if attempt_failures else None,
        "fallback_trigger_stage": "305",
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
        # Step 372a: carry the REAL answering model/label onto every per-evaluator
        # verdict. `role` (A/B/C) is the stable SLOT; `actual_model`/`actual_label`
        # are what actually answered (a fallback returns the fallback's model/label).
        # The displayed `label` is now the real one, not the static lineup label —
        # this is the line that was previously laundering a fallback's verdict under
        # the primary's name ("GPT-5.5").
        _primary_model = EVALUATOR_LINEUP_305.get(role, {}).get("model")
        _actual_model = result.get("model")
        _actual_label = result.get("label")
        _is_fallback = bool(_actual_model) and _actual_model != _primary_model
        _real_label = _actual_label or EVALUATOR_LINEUP_305.get(role, {}).get("label", f"Evaluator {role}")

        if not result.get("completed") or not result.get("element_verdicts"):
            verdicts.append({
                "role": role,
                "label": _real_label,
                "actual_model": _actual_model,
                "actual_label": _actual_label,
                "is_fallback": _is_fallback,
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
                "label": _real_label,
                "actual_model": _actual_model,
                "actual_label": _actual_label,
                "is_fallback": _is_fallback,
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
            "label": _real_label,
            "actual_model": _actual_model,
            "actual_label": _actual_label,
            "is_fallback": _is_fallback,
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
    # Step 372D2-fix: derived, NON-authoritative display aid. On disagreement paths the
    # authoritative merged `citation` STAYS None (correct epistemic behavior — the merge
    # declines to pick one citation when there's no consensus). But the per-evaluator
    # citations already exist in `verdicts`; collect the cited (section_ref-bearing) ones
    # so the UI can show "the section was CITED but the element is CONTESTED" instead of
    # nothing. Pure surfacing — does NOT change verdict/confidence/coverage_state.
    def _collect_disagreement_citations(vs: list[dict]):
        out = [
            {"role": v.get("role"), "actual_label": v.get("actual_label"),
             "verdict": v.get("verdict"), "citation": v.get("citation")}
            for v in vs
            if isinstance(v.get("citation"), dict) and v["citation"].get("section_ref")
        ]
        return out or None

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
            "disagreement_citations": _collect_disagreement_citations(verdicts),  # Step 372D2-fix
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
            "disagreement_citations": _collect_disagreement_citations(verdicts),  # Step 372D2-fix
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
                "disagreement_citations": _collect_disagreement_citations(verdicts),  # Step 372D2-fix
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

_OPPOSITE_PARTY = {"tenant": "landlord", "landlord": "tenant"}


def derive_lp_state(element_results: list[dict], elements_305: list[dict],
                    perspective: str = "tenant") -> str:
    """Derive LP-level coverage_state from merged element verdicts per architecture spec §7.

    Does NOT apply covered_unfavorable or potentially_unenforceable — those are
    applied by the caller (lease_coverage.py routing) using the existing pattern checks.

    Step 374Z (C3 polarity correction): a missing element whose absence is adverse to the
    OPPOSITE party (``absence_adverse_to == opposite_party``) is NOT a gap for the selected
    perspective — a missing *burden* on the perspective party is favorable/non-adverse, not a
    missing protection. Such absences are excluded from adverse-missing scoring (so they cannot,
    on their own, push the LP to partial/missing or flag a high-severity gap). Elements whose
    absence is adverse to the selected perspective, ``both``, ``null``, or context-dependent stay
    ADVERSE/reviewable (conservative — only clear opposite-polarity flips; this is why C3 beat C2
    on the null-polarity LP-01 case). This consumes the schema's ``absence_adverse_to`` field as
    designed (374W found it was dead data). NOT a numeric offset — favorable absences are simply
    not counted as gaps; they are retained separately by the caller.
    """
    if not element_results:
        return "review_needed"

    opposite = _OPPOSITE_PARTY.get((perspective or "tenant").lower())
    polarity_by_id = {e.get("element_id"): e.get("absence_adverse_to") for e in elements_305}

    def _is_favorable_absence(r: dict) -> bool:
        # Only a clearly-missing, clearly-opposite-polarity element is non-adverse for this
        # perspective. Disputed (evaluators disagree) and null/both stay adverse/reviewable.
        return (opposite is not None
                and r["verdict"] == "missing"
                and polarity_by_id.get(r["element_id"]) == opposite)

    high_severity_ids = {
        e["element_id"] for e in elements_305
        if e.get("absence_severity") == "high"
    }

    any_unclear = any(r["verdict"] == "unclear" for r in element_results)
    # Step 374Z: a favorable (opposite-polarity) absence counts as satisfied/non-adverse for the
    # selected perspective, so an LP whose only non-present elements are favorable absences is
    # "covered" for this perspective (not a gap).
    all_non_adverse = all(
        r["verdict"] in PRESENCE_VERDICTS or _is_favorable_absence(r)
        for r in element_results
    )
    # Supplement #21 Phase 1: treat disputed as missing for LP-state derivation
    # (conservative; Phase 3 will add criticality-gated propagation to Review Needed).
    # Step 374Z: exclude favorable (opposite-polarity) absences from the adverse-missing set.
    missing_or_disputed = [
        r for r in element_results
        if r["verdict"] in ("missing", "disputed") and not _is_favorable_absence(r)
    ]
    high_severity_missing = any(r["element_id"] in high_severity_ids for r in missing_or_disputed)

    if any_unclear:
        return "review_needed"

    if all_non_adverse:
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
            "lp_meta": {"fallback_used": False, "fallbacks": None},  # Step 372a
        }

    # Step 374Z (C3 polarity correction): selected perspective + opposite party. A missing element
    # whose absence is adverse to the OPPOSITE party is a favorable/non-adverse absence for this
    # perspective (a missing burden, not a missing protection) — it is kept OUT of elements_missing
    # (so it is never narrated/scored as a gap) and retained separately as a favorable candidate.
    _perspective = ((cfg or {}).get("perspective") or "tenant").lower()
    _opposite_party = _OPPOSITE_PARTY.get(_perspective)

    # ── 2. Merge per-element verdicts ─────────────────────────────────────────
    element_verdicts_merged = []
    elements_present = []
    elements_missing = []
    favorable_absences = []  # Step 374Z: opposite-polarity missing — candidate favorable/non-adverse context
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
            # Step 372D2-fix: derived, non-authoritative cited-but-contested sections
            # (None on consensus paths). Merged `citation` above stays None on disagreement.
            "disagreement_citations": merged.get("disagreement_citations"),
        }
        element_verdicts_merged.append(verdict_record)

        if merged["verdict"] in PRESENCE_VERDICTS:
            elements_present.append(element_label)
        elif merged["verdict"] == "missing":
            # Step 374Z (C3): clear opposite-polarity absence → favorable/non-adverse candidate, NOT a
            # gap. Only the perspective-adverse / both / null missing elements stay in elements_missing
            # (which feeds coverage_state, materiality, exposure prose, and the "Missing:" display).
            if _opposite_party and element.get("absence_adverse_to") == _opposite_party:
                favorable_absences.append({
                    "element_id": element_id,
                    "element_label": element_label,
                    "absence_adverse_to": element.get("absence_adverse_to"),
                    "absence_severity": element.get("absence_severity"),
                    # Step 374Z: cross-document dependency caveat (e.g. LP-27 lender-cure → SNDA/LP-22)
                    # so a later favorable-position surface can qualify the advantage, not assert it.
                    "cross_LP_coverage": element.get("cross_LP_coverage") or None,
                })
            else:
                elements_missing.append(element_label)
        elif merged["verdict"] == "disputed":
            elements_disputed.append(element_label)
            if criticality == "critical":        # Step 355: track criticality of disputed elements
                elements_disputed_critical += 1
            elif criticality == "important":
                elements_disputed_important += 1

    # ── 3. Derive LP-level coverage state ─────────────────────────────────────
    coverage_state_baseline = derive_lp_state(element_verdicts_merged, elements_305, _perspective)

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

    # Step 372a: evaluator_meta now records the REAL answering model, an explicit
    # fallback flag, and admin-side token-utilization fields. `model`/`actual_model`
    # are the real answering model; the static slot model lives in EVALUATOR_LINEUP_305.
    evaluator_meta = {
        role: {
            "completed": r["completed"],
            "model": r["model"],
            "actual_model": r.get("model"),
            "actual_label": r.get("label"),
            "is_fallback": bool(r.get("model")) and r.get("model") != EVALUATOR_LINEUP_305.get(role, {}).get("model"),
            "elapsed_sec": r["elapsed_sec"],
            "error": r.get("error"),
            # Token-utilization observability (admin-side only — never lawyer-facing)
            "max_output_tokens": r.get("max_output_tokens"),
            "output_tokens_used": r.get("output_tokens_used"),
            "output_utilization": r.get("output_utilization"),
            "finish_reason": r.get("finish_reason"),
            "truncated": r.get("truncated"),
            # Step 372c: budget-pressure + fallback-cause fields (queryable from data)
            "requested_budget": r.get("requested_budget"),
            "actual_output_tokens": r.get("actual_output_tokens"),
            "budget_utilization_pct": r.get("budget_utilization_pct"),
            "usage_source": r.get("usage_source"),
            "n_subcalls": r.get("n_subcalls"),
            "split_applied": r.get("split_applied"),
            "fallback_reason": r.get("fallback_reason"),
            "fallback_trigger_stage": r.get("fallback_trigger_stage"),
        }
        for role, r in evaluator_results.items()
    }

    # Step 372a: LP-level fallback flag for a quiet, audit-surface-only confidence
    # tick. Records which slot(s) fell back and to what — NOT a lawyer-facing alarm.
    _fallbacks = [
        {"role": role, "actual_model": r.get("model"), "actual_label": r.get("label")}
        for role, r in evaluator_results.items()
        if bool(r.get("model")) and r.get("model") != EVALUATOR_LINEUP_305.get(role, {}).get("model")
    ]
    lp_meta = {
        "fallback_used": bool(_fallbacks),
        "fallbacks": _fallbacks or None,
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
        # Step 374Z (C3): opposite-polarity absences — retained as candidate favorable/non-adverse
        # context (data slot only; NOT surfaced as a UI bucket and NEVER offsets Risk numerically).
        "favorable_or_non_adverse_absences": favorable_absences,
        "elements_disputed": elements_disputed,          # Supplement #21 Phase 1
        "elements_disputed_critical": elements_disputed_critical,   # Step 355 Phase 2
        "elements_disputed_important": elements_disputed_important, # Step 355 Phase 2
        "negative_space_candidates_reviewed": negative_space_candidates,
        "evaluator_meta": evaluator_meta,
        "lp_meta": lp_meta,  # Step 372a: LP-level fallback_used flag (audit surface only)
        "api_calls": succeeded,  # Step 335: number of evaluator API calls made for this LP
        # Step 351: Architecture A Phase 2 — verdict distance at LP layer
        "verdict_distance": verdict_distance,
        "lp_confidence_base": lp_confidence_base,
        "per_evaluator_lp_verdicts": per_evaluator_lp_verdicts,
    }
