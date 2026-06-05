"""
Stage 5e (Finding-Scope): G-cand Consequence Provenance (Step 375E-COV-A)

Attaches use_consequence provenance to cross_provision_findings records:
  - directional_mismatch findings: G-cand lane → finding-scoped 5e consequence assessment
  - compound_risk findings: compound_consequence_source = "not_assessed" (structurally forced)

POPULATE/RECORD only. Does NOT change routing, buckets, or lawyer-visible output.
COV-B (separate, later) will consume these fields to change lawyer-facing landing.

G-cand gate:
  Every adverse-directional CANDIDATE (Pass-1 candidate, verification-agnostic)
  lacking assessed consequence → finding-scoped 5e.
  NOT gated on Pass-2 verification (vote-wobble re-import risk per 375D-2/375-R).
  NOT gated on current Risk routing (circular per 375O Q3 — floor-promoted without assessed
  consequence, so gating consequence-assessment on that output is the snake eating its audit log).

Finding-scope vs LP-scope:
  On the current lease, finding↔LP is 1:1 for directional findings (per 375P precheck).
  Build finding-scoped output plainly; do NOT build LP-reuse-guard machinery.
  Reuse-safety is DEFERRED/UNEXERCISED (many-to-many only arises in compound layer).

5e prompt for G-cand findings:
  Stage 7 direction is FIXED INPUT. Evaluators assess use_consequence and materiality ONLY.
  They must not re-litigate whether the finding is adverse — Stage 7 owns sign, 5e owns consequence.

Provenance fields added to directional findings:
  stage7_direction:        "tenant_unprotected" (always, for adverse directional findings)
  use_consequence:         "beneficial"|"neutral"|"harmful"|"context_dependent"
  materiality:             "high"|"medium"|"low"|"not_applicable"
  use_consequence_source:  "assessed"|"absent"
  materiality_source:      "assessed"|"absent"
  assessment_scope:        "finding_linked_lp"

Provenance field added to compound findings:
  compound_consequence_source: "not_assessed"
  (Structurally forced — no single LP consequence is correct for multi-LP compound findings)

use_consequence_source values used in COV-A:
  "assessed"  — verdict produced (either copied from LP-scope use_impact or from new 5e run)
  "absent"    — no use_profile provided, or all evaluators failed
  ("defaulted_floor" and "not_eligible" are reserved for COV-B annotations on existing findings)
"""

import logging
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

logger = logging.getLogger(__name__)

# ── Feature flag ───────────────────────────────────────────────────────────────

FINDING_CONSEQUENCE_ENABLED = True

# ── Evaluator lineup (mirrors lease_use_impact.py) ────────────────────────────

from cam.adapters.lease_review.model_config import (  # noqa: E402
    EVALUATOR_A_PRIMARY, EVALUATOR_A_FALLBACK,
    EVALUATOR_B_PRIMARY, EVALUATOR_B_FALLBACK,
    EVALUATOR_C_PRIMARY, EVALUATOR_C_FALLBACK,
    EVALUATOR_A_LABEL, EVALUATOR_B_LABEL, EVALUATOR_C_LABEL,
    EVALUATOR_A_FALLBACK_LABEL, EVALUATOR_B_FALLBACK_LABEL, EVALUATOR_C_FALLBACK_LABEL,
)

_EVALUATOR_LINEUP: dict = {
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
_MATERIALITY_RANK = {"not_applicable": 0, "low": 1, "medium": 2, "high": 3}

# ── System prompt (finding-scoped, direction FIXED) ────────────────────────────

_FINDING_SYSTEM_PROMPT = """You are a commercial real estate attorney assessing how a lease provision directional finding affects a specific tenant's operations.

Stage 7 cross-provision analysis has already established that a directional mismatch exists — the landlord's lease terms are adverse to the tenant's protected position on each listed provision. The finding direction is FIXED. DO NOT reassess whether each finding is valid or whether the direction is correct. Accept the adverse direction as a settled fact.

Your role is to assess ONLY:
1. use_consequence: given THIS tenant's specific use of the space, how consequential is the adverse direction in practice?
2. materiality: how significant is this finding for THIS tenant's core business operations?

Return a JSON object with one key per finding ID (e.g. "Dir-01", "Dir-02"):
{
  "Dir-NN": {
    "use_consequence": "beneficial" | "neutral" | "harmful" | "context_dependent",
    "materiality": "high" | "medium" | "low" | "not_applicable",
    "use_reasoning": "One sentence grounding the assessment in the tenant's specific use — not generic lease risk."
  }
}

Definitions:
  use_consequence:
    harmful:           The adverse finding creates meaningful practical risk or cost for this tenant given their use
    neutral:           The finding has little practical effect on this tenant's operations despite the adverse direction
    beneficial:        Despite the adverse direction in the abstract, the finding is net-positive for this tenant
                       given their specific use (requires a concrete operational justification — not assumed)
    context_dependent: Cannot determine without more information about this tenant's specific situation

  materiality:
    high:           Directly affects the tenant's core business operations or creates significant financial exposure
    medium:         Relevant but not operationally critical for this specific tenant
    low:            Minor relevance to this tenant's use case
    not_applicable: This provision is irrelevant to this tenant's specific use and operations

Rules:
  - DO NOT question or re-examine the directional finding — accept it as given
  - "harmful because the direction is adverse" is not sufficient reasoning — ground the answer in what this means for THIS tenant's specific use type
  - Must return a verdict for every finding ID listed — no omissions
  - Return only the JSON object, no markdown fences"""


# ── Normalizer for legacy gap_impact fields (pre-375M artifacts) ───────────────

def _normalize_consequence(use_impact_dict: dict) -> dict:
    """Normalize legacy gap_impact → use_consequence for reading pre-375M artifacts.

    Post-375M write path already writes use_consequence. This normalizer handles
    frozen artifacts produced before a939b01 (the 375M deploy commit).
    """
    if not use_impact_dict:
        return {}
    result = dict(use_impact_dict)
    if "use_consequence" not in result and "gap_impact" in result:
        gi = result.pop("gap_impact", None) or ""
        mapping = {"favorable": "beneficial", "adverse": "harmful"}
        result["use_consequence"] = mapping.get(gi.lower(), gi)
    return result


# ── Already-assessed detection ─────────────────────────────────────────────────

def _is_already_assessed(lp_assessment: dict) -> bool:
    """Return True if this LP already has a valid use_consequence from LP-scope 5e.

    Uses the normalizer to handle pre-375M artifacts (gap_impact field).
    """
    ui = _normalize_consequence(lp_assessment.get("use_impact") or {})
    return ui.get("use_consequence") in _VALID_USE_CONSEQUENCE


# ── Prompt builder ─────────────────────────────────────────────────────────────

def _build_finding_user_prompt(
    findings_to_assess: list,
    coverage_by_lp: dict,
    use_profile: dict,
    perspective: str,
) -> str:
    """Build a batched user prompt covering all unassessed directional findings."""
    biz = use_profile.get("business_type") or "unspecified"
    deps = use_profile.get("operational_dependencies") or []
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

    lines += [
        "",
        "DIRECTIONAL FINDINGS TO ASSESS:",
        "(Direction is FIXED as adverse/tenant_unprotected per Stage 7. DO NOT re-examine direction.)",
        "",
    ]

    for f in findings_to_assess:
        fid = f.get("finding_id", "")
        lp_ids = f.get("implicated_lps") or []
        lp_id = lp_ids[0] if lp_ids else ""
        lp = coverage_by_lp.get(lp_id, {})
        lp_name = lp.get("issue_area_name") or lp.get("provision_name") or lp_id
        headline = (f.get("headline") or "").strip()
        detail = (f.get("detail") or "").strip()

        lines.append(f"  {fid} [LP: {lp_id} — {lp_name}]")
        lines.append(f"    Stage 7 finding (FIXED direction — adverse): {headline}")
        if detail and detail != headline:
            # Truncate long details to keep prompt manageable
            detail_excerpt = detail[:300] + "…" if len(detail) > 300 else detail
            lines.append(f"    Detail: {detail_excerpt}")
        lines.append("")

    lines.append(
        "Return JSON only with use_consequence, materiality, and use_reasoning "
        "for each finding ID (e.g. Dir-01, Dir-02, …)."
    )
    return "\n".join(lines)


# ── Evaluator call ─────────────────────────────────────────────────────────────

def _call_finding_evaluator(
    role: str,
    ev_cfg: dict,
    user_prompt: str,
    claimed_providers: set,
    claimed_lock: threading.Lock,
) -> dict:
    """Call one evaluator with the finding-scoped system prompt.

    Mirrors _call_evaluator in lease_use_impact.py but uses _FINDING_SYSTEM_PROMPT.
    """
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
                name=f"{provider}:{model}-use5ef-{role}",
                provider=provider, model=model,
                max_output_tokens=ev_cfg["max_output_tokens"],
                temperature=0.0, timeout_sec=ev_cfg["timeout_sec"],
            )
            router = ProviderRouter([target], RouterConfig())
            adapter = router._get_adapter(provider)
            raw = adapter.call(_FINDING_SYSTEM_PROMPT, user_prompt, target).strip()
            parsed = safe_json_extract(raw)
            if not isinstance(parsed, dict):
                raise ValueError(f"Response is not a dict (got {type(parsed).__name__})")
            if parsed:
                logger.info(
                    f"[lease_finding_consequence] Eval-{role}: {label} succeeded "
                    f"in {round(time.time() - start, 1)}s, {len(parsed)} finding(s)"
                )
                return {
                    "role": role, "label": label, "finding_output": parsed,
                    "completed": True, "elapsed_sec": round(time.time() - start, 2),
                    "error": None,
                }
        except Exception as e:
            logger.warning(f"[lease_finding_consequence] Eval-{role} {label} failed: {e}")
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

    logger.error(f"[lease_finding_consequence] Eval-{role}: all attempts failed")
    return {
        "role": role, "label": ev_cfg["label"], "finding_output": None,
        "completed": False, "elapsed_sec": round(time.time() - start, 2),
        "error": "all attempts failed",
    }


# ── Governance merge ───────────────────────────────────────────────────────────

def _merge_finding_verdicts(
    results: list,
    findings: list,
) -> dict:
    """Merge 3 evaluator outputs into one verdict per finding.

    Agreement rules (mirrors _merge_verdicts in lease_use_impact.py):
      3/3 same use_consequence → assert (confidence field carried in meta but not in provenance)
      2/3 same use_consequence → assert_weak (use majority)
      1-1-1 split → context_dependent
    Materiality: 3/3 same → use; else use most conservative (lowest rank).
    """
    completed = [r for r in results if r.get("completed") and r.get("finding_output")]
    n_ok = len(completed)

    if n_ok == 0:
        # All evaluators failed — return context_dependent for all findings
        return {
            f.get("finding_id", ""): {
                "use_consequence": "context_dependent",
                "materiality": "low",
                "use_reasoning": "Evaluators unavailable — cannot assess use consequence.",
                "confidence": "no_evaluators",
                "evaluator_agreement": None,
            }
            for f in findings
        }

    merged: dict = {}
    for f in findings:
        fid = f.get("finding_id", "")

        consequences = []
        materialities = []
        reasonings = []
        for r in completed:
            out = r["finding_output"].get(fid) or {}
            uc = (out.get("use_consequence") or "").lower().strip()
            mt = (out.get("materiality") or "").lower().strip()
            rs = (out.get("use_reasoning") or "").strip()
            if uc in _VALID_USE_CONSEQUENCE:
                consequences.append(uc)
            if mt in _VALID_MATERIALITY:
                materialities.append(mt)
            if rs:
                reasonings.append(rs)

        if not consequences:
            merged[fid] = {
                "use_consequence": "context_dependent",
                "materiality": "low",
                "use_reasoning": "No valid evaluator verdict for this finding.",
                "confidence": "no_evaluators",
                "evaluator_agreement": None,
            }
            continue

        # use_consequence governance
        uc_counts = Counter(consequences)
        most_common_uc, most_common_count = uc_counts.most_common(1)[0]

        if most_common_count == len(consequences):   # all agree
            final_uc = most_common_uc
            confidence = "assert"
            agree_str = f"{len(consequences)}-0"
        elif most_common_count >= 2:                  # 2/3 majority
            final_uc = most_common_uc
            confidence = "assert_weak"
            agree_str = "2-1"
        else:                                         # 1-1-1 split
            final_uc = "context_dependent"
            confidence = "context_dependent"
            agree_str = "1-1-1"

        # materiality: most conservative of reported values
        mat = min(materialities, key=lambda m: _MATERIALITY_RANK.get(m, 1)) if materialities else "low"

        # use_reasoning: prefer the reasoning from the evaluator whose consequence won
        reasoning = reasonings[0] if reasonings else "No reasoning provided."
        for r in completed:
            out = r["finding_output"].get(fid) or {}
            if (out.get("use_consequence") or "").lower().strip() == final_uc:
                cand = (out.get("use_reasoning") or "").strip()
                if cand:
                    reasoning = cand
                    break

        merged[fid] = {
            "use_consequence": final_uc,
            "materiality": mat,
            "use_reasoning": reasoning,
            "confidence": confidence,
            "evaluator_agreement": agree_str,
        }

    return merged


# ── Public entry point ─────────────────────────────────────────────────────────

def assess_finding_consequence(
    cross_provision_findings: list,
    coverage_assessment: list,
    use_profile: Optional[dict],
    perspective: str,
    cfg: Optional[dict] = None,
) -> tuple:
    """Attach finding-scoped consequence provenance to cross_provision_findings.

    POPULATE/RECORD only — does NOT change routing, buckets, or current_bucket field.
    COV-A adds new fields; COV-B (separate) decides lawyer-facing landing.

    Args:
        cross_provision_findings: Stage 7 output — list of finding dicts.
            Modified IN PLACE (new provenance fields added; existing fields untouched).
        coverage_assessment: Stage 5 output — list of LP assessment dicts.
            Read-only — used to detect already-assessed LPs and copy their use_impact.
        use_profile: Tenant use profile dict. If None/empty, marks unassessed findings
            as use_consequence_source="absent" without model calls (keyless mode).
        perspective: "tenant" or "landlord".
        cfg: Optional pipeline config dict.

    Returns:
        (cross_provision_findings, meta) — the same list (modified in place) plus a
        metadata dict carrying assessed/newly_assessed/absent counts and reason.
    """
    cfg = cfg or {}

    # ── Build LP lookup (by issue_area_id or provision_id) ────────────────────
    coverage_by_lp: dict = {}
    for a in coverage_assessment:
        pid = a.get("issue_area_id") or a.get("provision_id") or ""
        if pid:
            coverage_by_lp[pid] = a

    # ── Annotate compound findings (structurally forced — no LP consequence) ──
    n_compound = 0
    for f in cross_provision_findings:
        if f.get("finding_type") == "compound_risk":
            f["compound_consequence_source"] = "not_assessed"
            n_compound += 1

    # ── Identify G-cand directional findings ──────────────────────────────────
    # Gate: finding_type == "directional_mismatch" (Pass-1 candidate, verification-agnostic).
    # NOT gated on verification (vote-wobble risk). NOT gated on current Risk routing (circular).
    # In practice, all directional_mismatch findings carry directionality="tenant_unprotected";
    # finding_type alone is the gate — directionality is provenance, not an entry filter.
    directional = [
        f for f in cross_provision_findings
        if f.get("finding_type") == "directional_mismatch"
    ]

    already_assessed_pairs = []   # (finding, lp_assessment) — LP already has use_impact
    needs_assessment_pairs = []   # (finding, lp_assessment) — LP has no use_impact

    for f in directional:
        # Field is "implicated_lps" in Stage 7 output (not "all_implicated_lps")
        lp_ids = f.get("implicated_lps") or []
        lp_id = lp_ids[0] if lp_ids else ""
        lp = coverage_by_lp.get(lp_id, {})
        if _is_already_assessed(lp):
            already_assessed_pairs.append((f, lp))
        else:
            needs_assessment_pairs.append((f, lp))

    print(
        f"[lease_finding_consequence] G-cand lane: {len(directional)} directional finding(s) — "
        f"{len(already_assessed_pairs)} already-assessed (copy), "
        f"{len(needs_assessment_pairs)} unassessed (new 5e), "
        f"{n_compound} compound (not_assessed)",
        flush=True,
    )

    # ── Annotate already-assessed findings (copy from LP-scope use_impact) ────
    for f, lp in already_assessed_pairs:
        ui = _normalize_consequence(lp.get("use_impact") or {})
        f["stage7_direction"] = "tenant_unprotected"
        f["use_consequence"] = ui.get("use_consequence", "context_dependent")
        f["materiality"] = ui.get("materiality", "low")
        f["use_consequence_source"] = "assessed"
        f["materiality_source"] = "assessed"
        f["assessment_scope"] = "finding_linked_lp"

    # ── No use_profile → keyless mode, mark unassessed findings as absent ─────
    if not use_profile:
        logger.warning(
            "[lease_finding_consequence] No use_profile — marking unassessed findings as absent"
        )
        for f, _ in needs_assessment_pairs:
            f["stage7_direction"] = "tenant_unprotected"
            f["use_consequence"] = "context_dependent"
            f["materiality"] = "low"
            f["use_consequence_source"] = "absent"
            f["materiality_source"] = "absent"
            f["assessment_scope"] = "finding_linked_lp"
        meta = {
            "assessed": len(already_assessed_pairs),
            "newly_assessed": 0,
            "absent": len(needs_assessment_pairs),
            "total_directional": len(directional),
            "total_compound": n_compound,
            "reason": "no_use_profile",
        }
        return cross_provision_findings, meta

    # ── Run finding-scoped 5e on unassessed findings ──────────────────────────
    findings_to_assess = [f for f, _ in needs_assessment_pairs]

    if not findings_to_assess:
        meta = {
            "assessed": len(already_assessed_pairs),
            "newly_assessed": 0,
            "absent": 0,
            "total_directional": len(directional),
            "total_compound": n_compound,
            "reason": "all_already_assessed",
        }
        return cross_provision_findings, meta

    print(
        f"[lease_finding_consequence] Stage 5e-F: assessing {len(findings_to_assess)} "
        f"finding(s) via 3 evaluators...",
        flush=True,
    )

    user_prompt = _build_finding_user_prompt(
        findings_to_assess, coverage_by_lp, use_profile, perspective
    )

    claimed_providers: set = set()
    claimed_lock = threading.Lock()

    evaluator_results: list = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(
                _call_finding_evaluator,
                role, ev_cfg, user_prompt,
                claimed_providers, claimed_lock,
            ): role
            for role, ev_cfg in _EVALUATOR_LINEUP.items()
        }
        for fut in as_completed(futures):
            try:
                evaluator_results.append(fut.result())
            except Exception as e:
                role = futures[fut]
                logger.error(f"[lease_finding_consequence] Eval-{role} raised: {e}")
                evaluator_results.append({
                    "role": role, "finding_output": None,
                    "completed": False, "error": str(e),
                })

    merged = _merge_finding_verdicts(evaluator_results, findings_to_assess)

    # ── Attach provenance to newly-assessed findings ───────────────────────────
    n_newly_assessed = 0
    n_absent = 0
    for f, _ in needs_assessment_pairs:
        fid = f.get("finding_id", "")
        verdict = merged.get(fid, {})
        f["stage7_direction"] = "tenant_unprotected"
        if verdict.get("use_consequence") in _VALID_USE_CONSEQUENCE:
            f["use_consequence"] = verdict["use_consequence"]
            f["materiality"] = verdict.get("materiality", "low")
            f["use_consequence_source"] = "assessed"
            f["materiality_source"] = "assessed"
            n_newly_assessed += 1
        else:
            f["use_consequence"] = "context_dependent"
            f["materiality"] = "low"
            f["use_consequence_source"] = "absent"
            f["materiality_source"] = "absent"
            n_absent += 1
        f["assessment_scope"] = "finding_linked_lp"

    # ── Stage-level fallback visibility ───────────────────────────────────────
    fallbacks = [
        {"role": r.get("role"), "label": r.get("label")}
        for r in evaluator_results
        if r.get("completed") and r.get("label")
        and r.get("label") != _EVALUATOR_LINEUP.get(r.get("role"), {}).get("label")
    ]
    fallback_note = " (FALLBACK fired)" if fallbacks else ""

    n_harmful = sum(1 for f in findings_to_assess if f.get("use_consequence") == "harmful")
    n_neutral = sum(1 for f in findings_to_assess if f.get("use_consequence") == "neutral")
    n_beneficial = sum(1 for f in findings_to_assess if f.get("use_consequence") == "beneficial")
    n_ctx = sum(1 for f in findings_to_assess if f.get("use_consequence") == "context_dependent")
    print(
        f"[lease_finding_consequence] Stage 5e-F complete: "
        f"{n_harmful} harmful, {n_neutral} neutral, {n_beneficial} beneficial, "
        f"{n_ctx} context_dependent; {n_absent} absent{fallback_note}",
        flush=True,
    )

    meta = {
        "assessed": len(already_assessed_pairs) + n_newly_assessed,
        "newly_assessed": n_newly_assessed,
        "absent": n_absent,
        "total_directional": len(directional),
        "total_compound": n_compound,
        "fallback_used": bool(fallbacks),
        "fallbacks": fallbacks or None,
        "status": "applied",
    }
    return cross_provision_findings, meta
