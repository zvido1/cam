"""
Stage 5e: Use-Aware Provision Impact Assessment (Step 341b, extended Step 345)

For each LP that is:
  - missing (applicable)
  - partially covered with >= 50% missing elements  [narrow/default gate]
    OR any partial LP when _WIDEN_PARTIAL_ELIGIBILITY / cfg["widen_partial"] is True
  - review_needed (evaluators could not resolve coverage)

three evaluators assess whether the gap or uncertainty is favorable, neutral, or adverse
for the specific tenant's use. Results are stored as `use_impact` on each LP
assessment dict.

Architecture:
  - Flagged LPs are split into chunks of _CHUNK_SIZE (~11 per chunk) so the batched
    response stays within max_output_tokens=3000 per evaluator call.
  - Three evaluator threads process each chunk in parallel; per-chunk lp_output dicts
    are merged across chunks before _merge_verdicts runs.
  - Governance: 3/3 agree → assert, 2/3 agree → assert_weak, 1-1-1 split → context_dependent
  - Fallback: if use_profile absent, mark gap_impact = "context_dependent" without calling models

Output per LP (added to assessment dict):
  use_impact = {
      "use_consequence":      "beneficial" | "neutral" | "harmful" | "context_dependent",
      "materiality":          "high" | "medium" | "low" | "not_applicable",
      "use_reasoning":        "...",
      "confidence":           "assert" | "assert_weak" | "context_dependent" | "no_evaluators",
      "evaluator_agreement":  "3-0" | "2-1" | "1-1-1" | None,
  }

Non-goals:
  - Does NOT change coverage_state — preserves factual record
  - Does NOT run for covered / not_applicable
  - Compound override rule applied downstream in deriveProvisionRiskLevel (frontend)
"""

import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

logger = logging.getLogger(__name__)

# ── Feature flags ──────────────────────────────────────────────────────────────

USE_IMPACT_ENABLED = True

# Step 406 diagnostic flag: when True, _should_assess admits ALL partial LPs
# regardless of the present/absent element ratio (removes the >=50% missing gate).
# Default is False — the narrow 50% behaviour is the production baseline.
# Override at call time via cfg={"widen_partial": True}; this constant is the
# module-level default and can be changed for a session-scoped experiment.
_WIDEN_PARTIAL_ELIGIBILITY: bool = False

# Chunk size for batched evaluator calls.  405 §5 established that ~20-25 LPs of
# {use_consequence, materiality, use_reasoning} output can exceed
# max_output_tokens=3000 per evaluator.  Chunking to <=11 LPs per call keeps each
# response well within the ceiling; results are merged before _merge_verdicts runs.
_CHUNK_SIZE: int = 11

# ── Evaluator lineup (mirrors lease_use_aware_coverage.py) ────────────────────

from cam.adapters.lease_review.model_config import (  # noqa: E402
    EVALUATOR_A_PRIMARY, EVALUATOR_A_FALLBACK,
    EVALUATOR_B_PRIMARY, EVALUATOR_B_FALLBACK,
    EVALUATOR_C_PRIMARY, EVALUATOR_C_FALLBACK,
    EVALUATOR_A_LABEL, EVALUATOR_B_LABEL, EVALUATOR_C_LABEL,
    EVALUATOR_A_FALLBACK_LABEL, EVALUATOR_B_FALLBACK_LABEL, EVALUATOR_C_FALLBACK_LABEL,
)

_EVALUATOR_LINEUP: dict[str, dict] = {
    "A": {
        "provider": EVALUATOR_A_PRIMARY[0], "model": EVALUATOR_A_PRIMARY[1],
        "label": EVALUATOR_A_LABEL, "max_output_tokens": 3000, "timeout_sec": 240.0,
        "own_chain": [(EVALUATOR_A_FALLBACK[0], EVALUATOR_A_FALLBACK[1], EVALUATOR_A_FALLBACK_LABEL)],
    },
    "B": {
        "provider": EVALUATOR_B_PRIMARY[0], "model": EVALUATOR_B_PRIMARY[1],
        "label": EVALUATOR_B_LABEL, "max_output_tokens": 3000, "timeout_sec": 240.0,
        "own_chain": [(EVALUATOR_B_FALLBACK[0], EVALUATOR_B_FALLBACK[1], EVALUATOR_B_FALLBACK_LABEL)],
    },
    "C": {
        "provider": EVALUATOR_C_PRIMARY[0], "model": EVALUATOR_C_PRIMARY[1],
        "label": EVALUATOR_C_LABEL, "max_output_tokens": 3000, "timeout_sec": 240.0,
        "own_chain": [(EVALUATOR_C_FALLBACK[0], EVALUATOR_C_FALLBACK[1], EVALUATOR_C_FALLBACK_LABEL)],
    },
}

# ── Constants ──────────────────────────────────────────────────────────────────

_VALID_USE_CONSEQUENCE = frozenset({"beneficial", "neutral", "harmful", "context_dependent"})
_VALID_MATERIALITY = frozenset({"high", "medium", "low", "not_applicable"})
_PRESENT_VERDICTS  = frozenset({
    "explicitly_present", "implicitly_present",
    "covered_by_default_law", "covered_in_other_LP",
})
_MATERIALITY_RANK  = {"not_applicable": 0, "low": 1, "medium": 2, "high": 3}

# ── Eligibility filter ─────────────────────────────────────────────────────────

def _should_assess(a: dict, widen_partial: bool = False) -> bool:
    """Return True if this LP assessment needs use_impact evaluation.

    widen_partial=False (default/production): partial LPs admitted only when
      ≥50% of element_verdicts are non-present (the original coverage gate).
    widen_partial=True (Step 406 diagnostic): ALL partial LPs admitted
      regardless of present/absent ratio; missing/review_needed unchanged.
    """
    state = a.get("coverage_state", "")
    if state == "missing":
        return True
    if state == "review_needed":
        return True
    if state == "partial":
        evs = a.get("element_verdicts") or []
        if not evs:
            return False          # no element data in either mode — nothing for 5e to assess
        if widen_partial:
            return True           # wide: admit all partial LPs that have element data
        n_present = sum(1 for e in evs if e.get("verdict") in _PRESENT_VERDICTS)
        n_total   = len(evs)
        return n_total > 0 and (n_total - n_present) / n_total >= 0.5
    return False


def _chunk_list(lst: list, size: int) -> list[list]:
    """Split lst into sub-lists of at most `size` items (no item repeated or lost)."""
    return [lst[i:i + size] for i in range(0, len(lst), size)]

# ── Prompt builders ────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are a commercial real estate attorney assessing provision gaps from a specific tenant's perspective.

For each listed provision, determine whether the gap (missing or significantly partial coverage) is favorable, neutral, or adverse for THIS tenant — given their specific use of the space.

Return a JSON object with one key per LP ID containing exactly these fields:
{
  "LP-XX": {
    "use_consequence": "beneficial" | "neutral" | "harmful" | "context_dependent",
    "materiality":   "high" | "medium" | "low" | "not_applicable",
    "use_reasoning": "One sentence grounding the answer in the tenant's specific use — not generic lease risk."
  }
}

Definitions:
  beneficial:        The absence or weakness of this provision benefits THIS client given their use
  neutral:           This gap has little practical effect on this client's operations
  harmful:           This gap creates meaningful risk or cost for this client given their use
  context_dependent: Cannot determine without more information about the specific situation

Absence ≠ adverse by default. When a restriction is MISSING, ask: does the absence give the tenant
MORE freedom or MORE exposure? For operational tenants (warehousing, distribution, manufacturing,
logistics), a missing permitted use or use restriction clause means the landlord CANNOT restrict
the tenant's activities by claiming they violate the use clause. This is favorable — not adverse.
Example: LP-05 Permitted Use absent for a warehouse tenant → tenant has maximum operational
flexibility; landlord cannot claim tenant violates an undefined use restriction. Use consequence: beneficial.
Only mark absent use clauses as harmful if the tenant's specific operations require an affirmative
landlord commitment (e.g., exclusive use rights, specific permitted use carve-outs for licensing).

Materiality:
  high:           Directly affects the tenant's core business operations
  medium:         Relevant but not operationally critical
  low:            Minor relevance to this tenant's use
  not_applicable: This provision is irrelevant to this use case

Rules:
  - Ground every answer in THIS tenant's specific business and operational context
  - Do not give generic lease-risk answers — "adverse because missing" is not sufficient
  - Must return a verdict for every LP listed — no omissions
  - Return only the JSON object, no markdown fences"""


def _build_user_prompt(
    flagged: list[dict],
    use_profile: dict,
    perspective: str,
) -> str:
    biz   = use_profile.get("business_type") or "unspecified"
    deps  = use_profile.get("operational_dependencies") or []
    other = use_profile.get("other_use_risk_factors") or []

    lines = [
        f"PERSPECTIVE: {perspective.upper()}",
        "",
        "TENANT USE CONTEXT:",
        f"  Business type: {biz}",
    ]
    if deps:
        lines.append("  Key operational dependencies: " + "; ".join(str(d) for d in deps))
    if other:
        lines.append("  Other risk factors: " + "; ".join(str(r) for r in other))
    lines += ["", "PROVISION GAPS TO ASSESS:"]

    for a in flagged:
        pid   = a.get("issue_area_id") or a.get("provision_id") or ""
        name  = a.get("issue_area_name") or a.get("provision_name") or pid
        state = a.get("coverage_state", "")
        evs   = a.get("element_verdicts") or []
        if state == "review_needed":
            status = "coverage uncertain — evaluators disagree on whether this provision is addressed. Treat the unfavorable plausible reading as the risk case."
        elif evs:
            n_present = sum(1 for e in evs if e.get("verdict") in _PRESENT_VERDICTS)
            status = f"partially covered — {n_present} of {len(evs)} elements present"
        else:
            status = "missing from lease"
        lines.append(f"  {pid} [{name}]: {status}")

    lines += ["", "Return JSON only with use_consequence, materiality, and use_reasoning for each LP."]
    return "\n".join(lines)

# ── Evaluator call ─────────────────────────────────────────────────────────────

def _call_evaluator(
    role: str,
    ev_cfg: dict,
    user_prompt: str,
    claimed_providers: set,
    claimed_lock: threading.Lock,
) -> dict:
    from cam.core.provider_router import ModelTarget, ProviderRouter, RouterConfig
    from cam.core.json_extract import safe_json_extract

    start = time.time()

    def _try(provider: str, model: str, label: str) -> Optional[dict]:
        with claimed_lock:
            if provider in claimed_providers:
                return None
            claimed_providers.add(provider)
        try:
            target = ModelTarget(
                name=f"{provider}:{model}-use5e-{role}",
                provider=provider, model=model,
                max_output_tokens=ev_cfg["max_output_tokens"],
                temperature=0.0, timeout_sec=ev_cfg["timeout_sec"],
            )
            router  = ProviderRouter([target], RouterConfig())
            adapter = router._get_adapter(provider)
            raw     = adapter.call(_SYSTEM_PROMPT, user_prompt, target).strip()
            parsed  = safe_json_extract(raw)
            if not isinstance(parsed, dict):
                raise ValueError(f"Response is not a dict (got {type(parsed).__name__})")
            if parsed:
                logger.info(f"[lease_use_impact] Eval-{role}: {label} succeeded in {round(time.time()-start,1)}s, {len(parsed)} LP(s)")
                return {"role": role, "label": label, "lp_output": parsed, "completed": True,
                        "elapsed_sec": round(time.time() - start, 2), "error": None}
        except Exception as e:
            logger.warning(f"[lease_use_impact] Eval-{role} {label} failed: {e}")
        return None

    # Primary
    res = _try(ev_cfg["provider"], ev_cfg["model"], ev_cfg["label"])
    if res:
        return res
    # Own-chain fallback
    for fb_provider, fb_model, fb_label in ev_cfg.get("own_chain", []):
        res = _try(fb_provider, fb_model, fb_label)
        if res:
            return res

    logger.error(f"[lease_use_impact] Eval-{role}: all attempts failed")
    return {"role": role, "label": ev_cfg["label"], "lp_output": None, "completed": False,
            "elapsed_sec": round(time.time() - start, 2), "error": "all attempts failed"}

# ── Governance merge ───────────────────────────────────────────────────────────

def _merge_verdicts(
    results: list[dict],
    flagged: list[dict],
) -> dict[str, dict]:
    """Merge 3 evaluator outputs into one use_impact per LP.

    Agreement rules:
      3/3 same use_consequence → assert
      2/3 same use_consequence → assert_weak (use majority)
      1-1-1 split → context_dependent
    Materiality: 3/3 same → use; else use most conservative (lowest rank).
    """
    completed = [r for r in results if r.get("completed") and r.get("lp_output")]
    n_ok = len(completed)

    if n_ok == 0:
        # All evaluators failed — return context_dependent for all
        return {
            a.get("issue_area_id") or a.get("provision_id") or "": {
                "use_consequence": "context_dependent", "materiality": "low",
                "use_reasoning": "Evaluators unavailable — cannot assess use impact.",
                "confidence": "no_evaluators", "evaluator_agreement": None,
            }
            for a in flagged
        }

    merged: dict[str, dict] = {}
    for a in flagged:
        pid = a.get("issue_area_id") or a.get("provision_id") or ""

        # Collect per-evaluator verdict for this LP
        impacts     = []
        materialities = []
        reasonings  = []
        for r in completed:
            lp_out = r["lp_output"].get(pid) or {}
            gi = (lp_out.get("use_consequence") or "").lower().strip()
            mt = (lp_out.get("materiality") or "").lower().strip()
            rs = (lp_out.get("use_reasoning") or "").strip()
            if gi in _VALID_USE_CONSEQUENCE:
                impacts.append(gi)
            if mt in _VALID_MATERIALITY:
                materialities.append(mt)
            if rs:
                reasonings.append(rs)

        if not impacts:
            merged[pid] = {
                "use_consequence": "context_dependent", "materiality": "low",
                "use_reasoning": "No valid evaluator verdict.",
                "confidence": "no_evaluators", "evaluator_agreement": None,
            }
            continue

        # use_consequence governance
        from collections import Counter
        gi_counts = Counter(impacts)
        most_common_gi, most_common_count = gi_counts.most_common(1)[0]

        if most_common_count == len(impacts):         # all agree (or only 1 evaluator)
            gap_impact  = most_common_gi
            confidence  = "assert"
            agree_str   = f"{len(impacts)}-0"
        elif most_common_count >= 2:                   # 2/3 majority
            gap_impact  = most_common_gi
            confidence  = "assert_weak"
            agree_str   = "2-1"
        else:                                          # 1-1-1 split
            gap_impact  = "context_dependent"
            confidence  = "context_dependent"
            agree_str   = "1-1-1"

        # materiality: most conservative of reported values
        if materialities:
            mat = min(materialities, key=lambda m: _MATERIALITY_RANK.get(m, 1))
        else:
            mat = "low"

        # use_reasoning: prefer reasoning from the evaluator whose use_consequence won;
        # fall back to first available
        reasoning = reasonings[0] if reasonings else "No reasoning provided."
        # Try to match reasoning to the winning consequence
        for r in completed:
            lp_out = r["lp_output"].get(pid) or {}
            if (lp_out.get("use_consequence") or "").lower().strip() == gap_impact:
                cand = (lp_out.get("use_reasoning") or "").strip()
                if cand:
                    reasoning = cand
                    break

        merged[pid] = {
            "use_consequence": gap_impact,
            "materiality": mat,
            "use_reasoning": reasoning,
            "confidence": confidence,
            "evaluator_agreement": agree_str,
        }

    return merged

# ── Public entry point ─────────────────────────────────────────────────────────

def assess_use_impact(
    coverage_assessment: list,
    use_profile: Optional[dict],
    perspective: str,
    cfg: Optional[dict] = None,
) -> list:
    """Add use_impact to flagged LP assessments via 3 parallel evaluators.

    Eligibility (cfg["widen_partial"] or _WIDEN_PARTIAL_ELIGIBILITY controls scope):
      narrow (default): missing/review_needed always; partial only if >=50% missing elements.
      wide (Step 406):  missing/review_needed always; ALL partial LPs admitted.

    Batched calls are split into chunks of _CHUNK_SIZE LPs per evaluator to stay within
    max_output_tokens=3000.  Per-chunk lp_output dicts are merged before _merge_verdicts
    runs; _merge_verdicts semantics are unchanged.

    If use_profile is None / empty, marks all flagged LPs as context_dependent without API calls.

    Returns:
        (coverage_assessment, use_impact_meta) — the same list with use_impact added where
        applicable, plus a Step 372b stage-meta dict carrying fallback_used / fallbacks
        (admin observability; mirrors Stage 5d's governance_record). Metadata only — the
        merged use_impact verdicts are unchanged.
    """
    cfg = cfg or {}
    widen_partial: bool = cfg.get("widen_partial", _WIDEN_PARTIAL_ELIGIBILITY)

    flagged = [a for a in coverage_assessment if _should_assess(a, widen_partial=widen_partial)]
    if not flagged:
        logger.info("[lease_use_impact] No flagged LPs — skipping use_impact stage")
        return coverage_assessment, {"fallback_used": False, "fallbacks": None, "status": "no_flagged_lps"}

    # No use_profile → can't assess; mark context_dependent without API calls
    if not use_profile:
        logger.warning("[lease_use_impact] No use_profile — marking all flagged as context_dependent")
        for a in flagged:
            a["use_impact"] = {
                "use_consequence": "context_dependent", "materiality": "low",
                "use_reasoning": "No use profile available — cannot assess tenant-specific impact.",
                "confidence": "no_evaluators", "evaluator_agreement": None,
            }
        return coverage_assessment, {"fallback_used": False, "fallbacks": None, "status": "no_use_profile"}

    chunks = _chunk_list(flagged, _CHUNK_SIZE)
    n_chunks = len(chunks)
    gate_label = "wide(all-partial)" if widen_partial else "narrow(>=50%)"
    print(
        f"[lease_use_impact] Stage 5e: {len(flagged)} flagged LP(s) [{gate_label}], "
        f"{n_chunks} chunk(s) of <={_CHUNK_SIZE}, 3 evaluators...",
        flush=True,
    )

    # Accumulated per-evaluator lp_output across chunks; role → {pid: verdict_dict}
    per_ev_lp_output: dict[str, dict] = {role: {} for role in _EVALUATOR_LINEUP}
    # Last completed result metadata per evaluator (for fallback detection)
    per_ev_last_meta: dict[str, dict] = {}
    # Track every label used per evaluator (for accurate fallback detection across chunks)
    per_ev_labels: dict[str, list] = {role: [] for role in _EVALUATOR_LINEUP}

    for chunk_idx, chunk in enumerate(chunks, 1):
        user_prompt  = _build_user_prompt(chunk, use_profile, perspective)
        claimed_providers: set  = set()   # fresh per chunk — roles compete within a chunk
        claimed_lock = threading.Lock()

        print(
            f"[lease_use_impact]   chunk {chunk_idx}/{n_chunks}: "
            f"{len(chunk)} LP(s) ({chunk[0].get('issue_area_id','')}…{chunk[-1].get('issue_area_id','')})",
            flush=True,
        )

        chunk_results: list[dict] = []
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(
                    _call_evaluator,
                    role, ev_cfg, user_prompt,
                    claimed_providers, claimed_lock,
                ): role
                for role, ev_cfg in _EVALUATOR_LINEUP.items()
            }
            for fut in as_completed(futures):
                try:
                    chunk_results.append(fut.result())
                except Exception as e:
                    role = futures[fut]
                    logger.error(f"[lease_use_impact] Eval-{role} chunk {chunk_idx} raised: {e}")
                    chunk_results.append({
                        "role": role, "lp_output": None,
                        "completed": False, "error": str(e),
                    })

        # Merge chunk output into per-evaluator accumulators
        for r in chunk_results:
            role = r.get("role") or ""
            if not role:
                continue
            if r.get("completed") and r.get("lp_output"):
                per_ev_lp_output[role].update(r["lp_output"])
            label = r.get("label")
            if label:
                per_ev_labels[role].append(label)
            # Overwrite with last-seen meta for this role (captures fallback label if any)
            per_ev_last_meta[role] = r

    # Reconstruct the flat results list that _merge_verdicts expects
    results: list[dict] = []
    for role, ev_cfg in _EVALUATOR_LINEUP.items():
        lp_out = per_ev_lp_output[role]
        meta   = per_ev_last_meta.get(role, {})
        results.append({
            "role":        role,
            "label":       meta.get("label", ev_cfg["label"]),
            "lp_output":   lp_out if lp_out else None,
            "completed":   bool(lp_out),
            "elapsed_sec": meta.get("elapsed_sec"),
            "error":       meta.get("error") if not lp_out else None,
        })

    merged = _merge_verdicts(results, flagged)

    # Attach use_impact to each flagged assessment in place
    for a in coverage_assessment:
        pid = a.get("issue_area_id") or a.get("provision_id") or ""
        if pid in merged:
            a["use_impact"] = merged[pid]

    # Step 372b: stage-level fallback visibility.
    # A fallback fired if any label used for a role differs from the primary label.
    _stage5e_fallbacks = []
    for role, ev_cfg in _EVALUATOR_LINEUP.items():
        primary = ev_cfg["label"]
        non_primary = [l for l in per_ev_labels.get(role, []) if l != primary]
        if non_primary:
            _stage5e_fallbacks.append({"role": role, "label": non_primary[0]})

    use_impact_meta = {
        "fallback_used": bool(_stage5e_fallbacks),
        "fallbacks": _stage5e_fallbacks or None,
        "status": "applied",
        "chunks": n_chunks,
        "widen_partial": widen_partial,
    }

    n_favorable = sum(1 for v in merged.values() if v["use_consequence"] == "beneficial")
    n_adverse   = sum(1 for v in merged.values() if v["use_consequence"] == "harmful")
    n_neutral   = sum(1 for v in merged.values() if v["use_consequence"] == "neutral")
    n_ctx       = sum(1 for v in merged.values() if v["use_consequence"] == "context_dependent")
    _fb_note = " (FALLBACK fired)" if _stage5e_fallbacks else ""
    print(
        f"[lease_use_impact] Stage 5e complete: "
        f"{n_favorable} favorable, {n_adverse} adverse, {n_neutral} neutral, "
        f"{n_ctx} context_dependent | {n_chunks} chunk(s){_fb_note}",
        flush=True,
    )
    return coverage_assessment, use_impact_meta
