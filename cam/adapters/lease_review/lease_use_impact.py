"""
Stage 5e: Use-Aware Provision Impact Assessment (Step 341b)

For each LP that is missing (applicable) or partially covered with >= 50% missing
elements, three evaluators assess whether the gap is favorable, neutral, or adverse
for the specific tenant's use. Results are stored as `use_impact` on each LP
assessment dict.

Architecture:
  - Three evaluator threads, each processes ALL flagged LPs in one batched call
  - Governance: 3/3 agree → assert, 2/3 agree → assert_weak, 1-1-1 split → context_dependent
  - Fallback: if use_profile absent, mark gap_impact = "context_dependent" without calling models

Output per LP (added to assessment dict):
  use_impact = {
      "gap_impact":           "favorable" | "neutral" | "adverse" | "context_dependent",
      "materiality":          "high" | "medium" | "low" | "not_applicable",
      "use_reasoning":        "...",
      "confidence":           "assert" | "assert_weak" | "context_dependent" | "no_evaluators",
      "evaluator_agreement":  "3-0" | "2-1" | "1-1-1" | None,
  }

Non-goals:
  - Does NOT change coverage_state — preserves factual record
  - Does NOT run for covered / not_applicable / review_needed
  - Compound override rule applied downstream in deriveProvisionRiskLevel (frontend)
"""

import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

logger = logging.getLogger(__name__)

# ── Feature flag ───────────────────────────────────────────────────────────────

USE_IMPACT_ENABLED = True

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

_VALID_GAP_IMPACT  = frozenset({"favorable", "neutral", "adverse", "context_dependent"})
_VALID_MATERIALITY = frozenset({"high", "medium", "low", "not_applicable"})
_PRESENT_VERDICTS  = frozenset({
    "explicitly_present", "implicitly_present",
    "covered_by_default_law", "covered_in_other_LP",
})
_MATERIALITY_RANK  = {"not_applicable": 0, "low": 1, "medium": 2, "high": 3}

# ── Eligibility filter ─────────────────────────────────────────────────────────

def _should_assess(a: dict) -> bool:
    """Return True if this LP assessment needs use_impact evaluation."""
    state = a.get("coverage_state", "")
    if state == "missing":
        return True
    if state == "partial":
        evs = a.get("element_verdicts") or []
        if not evs:
            return False
        n_present = sum(1 for e in evs if e.get("verdict") in _PRESENT_VERDICTS)
        n_total   = len(evs)
        return n_total > 0 and (n_total - n_present) / n_total >= 0.5
    return False

# ── Prompt builders ────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are a commercial real estate attorney assessing provision gaps from a specific tenant's perspective.

For each listed provision, determine whether the gap (missing or significantly partial coverage) is favorable, neutral, or adverse for THIS tenant — given their specific use of the space.

Return a JSON object with one key per LP ID containing exactly these fields:
{
  "LP-XX": {
    "gap_impact":    "favorable" | "neutral" | "adverse" | "context_dependent",
    "materiality":   "high" | "medium" | "low" | "not_applicable",
    "use_reasoning": "One sentence grounding the answer in the tenant's specific use — not generic lease risk."
  }
}

Definitions:
  favorable:         The absence or weakness of this provision benefits THIS client given their use
  neutral:           This gap has little practical effect on this client's operations
  adverse:           This gap creates meaningful risk or cost for this client given their use
  context_dependent: Cannot determine without more information about the specific situation

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
        if evs:
            n_present = sum(1 for e in evs if e.get("verdict") in _PRESENT_VERDICTS)
            status = f"partially covered — {n_present} of {len(evs)} elements present"
        else:
            status = "missing from lease"
        lines.append(f"  {pid} [{name}]: {status}")

    lines += ["", "Return JSON only with gap_impact, materiality, and use_reasoning for each LP."]
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
                provider=provider, model=model,
                max_output_tokens=ev_cfg["max_output_tokens"],
                temperature=0.0, timeout_sec=ev_cfg["timeout_sec"],
            )
            router  = ProviderRouter([target], RouterConfig())
            adapter = router._get_adapter(target)
            raw     = adapter.call(_SYSTEM_PROMPT, user_prompt, target).strip()
            parsed  = safe_json_extract(raw, expect_type=dict)
            if parsed and isinstance(parsed, dict):
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
      3/3 same gap_impact → assert
      2/3 same gap_impact → assert_weak (use majority)
      1-1-1 split → context_dependent
    Materiality: 3/3 same → use; else use most conservative (lowest rank).
    """
    completed = [r for r in results if r.get("completed") and r.get("lp_output")]
    n_ok = len(completed)

    if n_ok == 0:
        # All evaluators failed — return context_dependent for all
        return {
            a.get("issue_area_id") or a.get("provision_id") or "": {
                "gap_impact": "context_dependent", "materiality": "low",
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
            gi = (lp_out.get("gap_impact") or "").lower().strip()
            mt = (lp_out.get("materiality") or "").lower().strip()
            rs = (lp_out.get("use_reasoning") or "").strip()
            if gi in _VALID_GAP_IMPACT:
                impacts.append(gi)
            if mt in _VALID_MATERIALITY:
                materialities.append(mt)
            if rs:
                reasonings.append(rs)

        if not impacts:
            merged[pid] = {
                "gap_impact": "context_dependent", "materiality": "low",
                "use_reasoning": "No valid evaluator verdict.",
                "confidence": "no_evaluators", "evaluator_agreement": None,
            }
            continue

        # gap_impact governance
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

        # use_reasoning: prefer reasoning from the evaluator whose gap_impact won;
        # fall back to first available
        reasoning = reasonings[0] if reasonings else "No reasoning provided."
        # Try to match reasoning to the winning impact
        for r in completed:
            lp_out = r["lp_output"].get(pid) or {}
            if (lp_out.get("gap_impact") or "").lower().strip() == gap_impact:
                cand = (lp_out.get("use_reasoning") or "").strip()
                if cand:
                    reasoning = cand
                    break

        merged[pid] = {
            "gap_impact": gap_impact,
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

    Flags: coverage_state = "missing" (applicable) OR "partial" with >= 50% missing elements.
    If use_profile is None / empty, marks all flagged LPs as context_dependent without API calls.
    Returns the same coverage_assessment list with use_impact added where applicable.
    """
    cfg = cfg or {}

    flagged = [a for a in coverage_assessment if _should_assess(a)]
    if not flagged:
        logger.info("[lease_use_impact] No flagged LPs — skipping use_impact stage")
        return coverage_assessment

    # No use_profile → can't assess; mark context_dependent without API calls
    if not use_profile:
        logger.warning("[lease_use_impact] No use_profile — marking all flagged as context_dependent")
        _ca_by_id = {(a.get("issue_area_id") or a.get("provision_id") or ""): a for a in coverage_assessment}
        for a in flagged:
            a["use_impact"] = {
                "gap_impact": "context_dependent", "materiality": "low",
                "use_reasoning": "No use profile available — cannot assess tenant-specific impact.",
                "confidence": "no_evaluators", "evaluator_agreement": None,
            }
        return coverage_assessment

    print(
        f"[lease_use_impact] Stage 5e: assessing {len(flagged)} flagged LP(s) via 3 evaluators...",
        flush=True,
    )

    user_prompt     = _build_user_prompt(flagged, use_profile, perspective)
    claimed_providers: set = set()
    claimed_lock    = threading.Lock()

    # Run 3 evaluators in parallel (each gets the same batched prompt)
    results: list[dict] = []
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
                results.append(fut.result())
            except Exception as e:
                role = futures[fut]
                logger.error(f"[lease_use_impact] Eval-{role} raised: {e}")
                results.append({"role": role, "lp_output": None, "completed": False, "error": str(e)})

    merged = _merge_verdicts(results, flagged)

    # Attach use_impact to each flagged assessment in place
    for a in coverage_assessment:
        pid = a.get("issue_area_id") or a.get("provision_id") or ""
        if pid in merged:
            a["use_impact"] = merged[pid]

    n_favorable = sum(1 for v in merged.values() if v["gap_impact"] == "favorable")
    n_adverse   = sum(1 for v in merged.values() if v["gap_impact"] == "adverse")
    n_neutral   = sum(1 for v in merged.values() if v["gap_impact"] == "neutral")
    n_ctx       = sum(1 for v in merged.values() if v["gap_impact"] == "context_dependent")
    print(
        f"[lease_use_impact] Stage 5e complete: "
        f"{n_favorable} favorable, {n_adverse} adverse, {n_neutral} neutral, {n_ctx} context_dependent",
        flush=True,
    )
    return coverage_assessment
