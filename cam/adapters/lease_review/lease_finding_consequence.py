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

5e prompt for G-cand findings (Step 375E-COV-A2 fix):
  Evaluators receive CLAUSE FACTS + tenant use profile — NOT the Stage-7 adversarial title or
  direction label. Stage 7 direction is stored as stage7_direction provenance on the finding but
  is NOT fed to 5e as a leading frame (A1 confirmed that doing so contaminates consequence
  assessment — LP-11 inverted from beneficial to harmful under the old framing).
  5e owns consequence; Stage 7 owns sign. Separation enforced by prompt, not just by doctrine.

Provenance fields added to directional findings:
  stage7_direction:        Stage 7's actual directionality value (f["directionality"]), or None if absent.
                           NOT hardcoded — records what Stage 7 actually produced.
  stage7_direction_source: "stage7" if directionality was present; "absent" if None/missing.
                           No fallback to "tenant_unprotected" (Step 375E-COV-A2b fix).
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
_PRESENT_VERDICTS = frozenset({
    "explicitly_present", "implicitly_present",
    "covered_by_default_law", "covered_in_other_LP",
})

# ── System prompt (finding-scoped, consequence-independent — Step 375E-COV-A2) ──
#
# Fix: removed the Stage-7-direction-FIXED leading frame that caused contamination
# (A1 confirmed: LP-11 inverted from beneficial to harmful under the old framing).
# Now uses the variant-B shape: clause facts + use profile, no adverse pre-framing.
# stage7_direction is stored on the finding as provenance but NOT fed to 5e here.

_FINDING_SYSTEM_PROMPT = """You are a commercial real estate attorney assessing how specific lease provision gaps affect a tenant's day-to-day operations.

For each listed provision, assess:
1. use_consequence: given THIS tenant's specific business and operational context, what is the practical consequence of this clause situation?
2. materiality: how significant is this for THIS tenant's core business operations?

INDEPENDENCE REQUIREMENT: Absence or structural incompleteness does NOT equal adverse by default.
Ask: does this gap give the tenant MORE operational freedom or MORE exposure? A structurally
incomplete provision may have beneficial, neutral, or harmful use consequence depending on this
specific tenant's operations. Assess consequence independently from any directional concern.

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
    beneficial:        The gap or clause situation is net-positive for this tenant given their use
                       (e.g., absence of a restriction gives the tenant MORE operational freedom)
    neutral:           The gap has little practical effect on this tenant's operations
    harmful:           The gap creates meaningful risk, cost, or constraint for this tenant given their use
    context_dependent: Cannot determine without more information about this tenant's specific situation

  materiality:
    high:           Directly affects the tenant's core business operations or creates significant financial exposure
    medium:         Relevant but not operationally critical for this specific tenant
    low:            Minor relevance to this tenant's use case
    not_applicable: This provision is irrelevant to this tenant's specific use and operations

Rules:
  - Absence does NOT equal adverse by default — ask whether the gap gives the tenant more freedom or more exposure
  - For an operational tenant (warehousing, distribution, light assembly): a missing restriction typically means
    the landlord CANNOT restrict the tenant's activities — that is favorable, not adverse
  - Ground every answer in THIS tenant's specific business type and operational dependencies
  - "harmful because something is missing" is not sufficient — explain the actual operational impact
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
    """Build a batched user prompt covering all unassessed directional findings.

    Step 375E-COV-A2 fix: passes clause facts from the LP assessment instead of
    the Stage-7 adversarial title/headline/direction. stage7_direction is stored
    on the finding as provenance but is NOT fed here as a leading frame.
    """
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
        "LEASE PROVISIONS TO ASSESS (clause facts only):",
        "",
    ]

    for f in findings_to_assess:
        fid = f.get("finding_id", "")
        lp_ids = f.get("implicated_lps") or []
        lp_id = lp_ids[0] if lp_ids else ""
        lp = coverage_by_lp.get(lp_id, {})
        lp_name = lp.get("issue_area_name") or lp.get("provision_name") or lp_id

        # ── Clause facts from the LP assessment (neutral framing) ──────────────
        coverage_state = lp.get("coverage_state", "")
        evs = lp.get("element_verdicts") or []
        present_labels = []
        missing_labels = []
        for ev in evs:
            if not isinstance(ev, dict):
                continue
            label = (
                ev.get("element_label")
                or ev.get("element_name")
                or ev.get("description")
            )
            if not label:
                eid = ev.get("element_id") or ""
                label = eid.split(".")[-1].replace("_", " ") if eid else None
            verdict = ev.get("verdict", "")
            if verdict in _PRESENT_VERDICTS:
                if label:
                    present_labels.append(label)
            elif verdict in {"missing", "unclear"}:
                if label:
                    missing_labels.append(label)

        if coverage_state == "review_needed":
            cov_desc = "uncertain — evaluators could not reach agreement on whether this provision is adequately addressed"
        elif coverage_state == "partial":
            cov_desc = (
                f"partial — {len(present_labels)} element(s) confirmed in lease, "
                f"{len(missing_labels)} element(s) not confirmed"
            )
        elif coverage_state == "missing":
            cov_desc = "not present in lease"
        else:
            cov_desc = coverage_state or "status unknown"

        tenant_text = (lp.get("tenant_text") or "").strip()

        lines.append(f"  {fid} [LP: {lp_id} — {lp_name}]")
        lines.append(f"    Provision coverage: {cov_desc}")
        if present_labels:
            lines.append("    Elements confirmed in lease: " + "; ".join(present_labels[:6]))
        if missing_labels:
            lines.append("    Elements not confirmed in lease: " + "; ".join(missing_labels[:4]))
        if tenant_text:
            excerpt = tenant_text[:400] + "…" if len(tenant_text) > 400 else tenant_text
            lines.append(f"    Relevant lease language: {excerpt}")
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
            # F8d (intentional): provider is claimed before the API call and is NOT
            # released on failure. This preserves evaluator independence: if role A claims
            # provider X and fails, role B cannot silently retry on the same provider (which
            # would make A and B effectively the same evaluator, defeating 3-way independence).
            # Own-chain fallback uses fb_provider (a different provider), so each role's
            # own retry is unaffected. The cost is that a provider that is healthy for B is
            # blocked after A's failure. Doctrine decision: independence requirement outweighs
            # coverage recovery. Do not remove this claim-before-call pattern.
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

    DEF-003 (F1) — Consequence support floor:
      Expected evaluator count = 3 (fixed lineup).
      3 valid, all agree → "assert" (true 3/3)
      3 valid, 2 agree   → "assert_weak" (2/3 majority)
      2 valid, both agree → "assert_duo" (reduced confidence; NOT full assert)
      1 valid            → "insufficient_support" (cannot assert; prevents Risk routing)
      0 valid            → "no_evaluators"
      1-1-1 split        → "context_dependent"
    Provenance: expected_evaluator_count, valid_evaluator_count, vote_distribution,
                consequence_support_label stored on each verdict.

    DEF-004 (F2) — Materiality majority merge:
      {high,high,low} → high (majority), not low (strict-min rejected).
      2/3 majority → majority value; minority preserved in materiality_votes.
      high↔low spread → materiality_disputed=True.
      No-majority (e.g. {high,medium,low}) → consequence_source NOT "assessed";
        route_to_review_needed=True signals caller to force Review Needed.
      0 valid materiality values → materiality_source="no_valid_materiality".

    F8c — 1-1-1 split reasoning:
      On a genuine 3-way split (no evaluator adopted the synthesized "context_dependent"),
      store null reasoning rather than attributing the first evaluator's reasoning.
    """
    _N_EXPECTED = 3  # fixed 3-evaluator lineup
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
                "expected_evaluator_count": _N_EXPECTED,
                "valid_evaluator_count": 0,
                "vote_distribution": {},
                "consequence_support_label": "no_evaluators",
                "materiality_votes": [],
                "materiality_support": "no_valid_materiality",
                "materiality_agreement": None,
                "materiality_disputed": False,
                "materiality_source": "no_valid_materiality",
                "route_to_review_needed": False,  # already routes via no_evaluators path
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

        n_valid_uc = len(consequences)
        vote_dist = dict(Counter(consequences))

        if not consequences:
            merged[fid] = {
                "use_consequence": "context_dependent",
                "materiality": "low",
                "use_reasoning": "No valid evaluator verdict for this finding.",
                "confidence": "no_evaluators",
                "evaluator_agreement": None,
                "expected_evaluator_count": _N_EXPECTED,
                "valid_evaluator_count": 0,
                "vote_distribution": vote_dist,
                "consequence_support_label": "no_evaluators",
                "materiality_votes": materialities,
                "materiality_support": "no_valid_materiality" if not materialities else "assessed",
                "materiality_agreement": None,
                "materiality_disputed": False,
                "materiality_source": "no_valid_materiality" if not materialities else "assessed",
                "route_to_review_needed": False,
            }
            continue

        # ── use_consequence governance (DEF-003) ─────────────────────────────
        uc_counts = Counter(consequences)
        most_common_uc, most_common_count = uc_counts.most_common(1)[0]

        if n_valid_uc == _N_EXPECTED and most_common_count == _N_EXPECTED:
            # True 3/3 unanimous
            final_uc = most_common_uc
            confidence = "assert"
            agree_str = "3-0"
            support_label = "full_assert"
        elif n_valid_uc == _N_EXPECTED and most_common_count >= 2:
            # 2/3 majority (all 3 responded, 2 agree)
            final_uc = most_common_uc
            confidence = "assert_weak"
            agree_str = "2-1"
            support_label = "majority_assert"
        elif n_valid_uc == 2 and most_common_count == 2:
            # 2 valid evaluators, both agree (1 failed); reduced confidence, NOT full assert
            final_uc = most_common_uc
            confidence = "assert_duo"
            agree_str = "2-0-1f"  # 2 agree, 0 dissent, 1 failed
            support_label = "duo_assert"
        elif n_valid_uc >= 2 and most_common_count >= 2:
            # General 2+ majority with some valid failures
            final_uc = most_common_uc
            confidence = "assert_weak"
            agree_str = f"{most_common_count}-{n_valid_uc - most_common_count}"
            support_label = "majority_assert"
        elif n_valid_uc == 1:
            # DEF-003: single valid evaluator — insufficient support for assert
            # Preserve verdict as diagnostic; must NOT route Risk on consequence alone
            final_uc = most_common_uc  # preserve for audit; routing gates on support_label
            confidence = "insufficient_support"
            agree_str = "1-0-2f"  # 1 valid, 0 dissent, 2 failed
            support_label = "insufficient_support"
        else:
            # 1-1-1 split (all 3 valid, no majority)
            final_uc = "context_dependent"
            confidence = "context_dependent"
            agree_str = "1-1-1"
            support_label = "split"

        # ── materiality merge (DEF-004) ───────────────────────────────────────
        n_valid_mat = len(materialities)
        materiality_disputed = False
        mat_source = "assessed"
        route_to_review_needed = False

        if n_valid_mat == 0:
            # No valid materiality from any evaluator
            mat = "low"
            mat_source = "no_valid_materiality"
            mat_support = "no_valid_materiality"
            mat_agreement = None
        elif n_valid_mat == 1:
            mat = materialities[0]
            mat_support = "singleton"
            mat_agreement = f"1-of-{n_valid_mat}"
        else:
            mat_counts = Counter(materialities)
            most_common_mat, mat_majority_count = mat_counts.most_common(1)[0]
            mat_ranks = [_MATERIALITY_RANK.get(m, 1) for m in materialities]
            has_high = "high" in materialities
            has_low = "low" in materialities

            if mat_majority_count >= 2:
                # 2+ evaluators agree on materiality → majority wins (DEF-004)
                mat = most_common_mat
                mat_support = f"majority_{mat_majority_count}-of-{n_valid_mat}"
                mat_agreement = f"{mat_majority_count}-{n_valid_mat - mat_majority_count}"
                if has_high and has_low:
                    materiality_disputed = True
            else:
                # No majority (e.g. {high, medium, low}) — cannot assert materiality
                # DEF-004 PINNED: route Review Needed; do NOT select minimum
                mat = "low"  # store defensively but routing is gated by route_to_review_needed
                mat_source = "no_majority"
                mat_support = "no_majority"
                mat_agreement = "1-1-1"
                route_to_review_needed = True

        # ── use_reasoning (F8c fix) ───────────────────────────────────────────
        # On a 1-1-1 split, no evaluator said "context_dependent" — store null
        # rather than misattributing the first evaluator's reasoning.
        if support_label == "split":
            # True 3-way split: synthesized context_dependent, no adopter
            reasoning = None
        else:
            reasoning = None
            for r in completed:
                out = r["finding_output"].get(fid) or {}
                if (out.get("use_consequence") or "").lower().strip() == final_uc:
                    cand = (out.get("use_reasoning") or "").strip()
                    if cand:
                        reasoning = cand
                        break
            if reasoning is None and reasonings:
                # Only fallback to reasonings[0] when the adopted verdict had a matching evaluator
                # (don't use it on splits where we set reasoning=None above)
                reasoning = reasonings[0] if support_label not in ("split",) else None

        merged[fid] = {
            "use_consequence": final_uc,
            "materiality": mat,
            "use_reasoning": reasoning,
            "confidence": confidence,
            "evaluator_agreement": agree_str,
            # DEF-003 provenance
            "expected_evaluator_count": _N_EXPECTED,
            "valid_evaluator_count": n_valid_uc,
            "vote_distribution": vote_dist,
            "consequence_support_label": support_label,
            # DEF-004 provenance
            "materiality_votes": materialities,
            "materiality_support": mat_support if n_valid_mat > 0 else "no_valid_materiality",
            "materiality_agreement": mat_agreement,
            "materiality_disputed": materiality_disputed,
            "materiality_source": mat_source,
            "route_to_review_needed": route_to_review_needed,
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
    # DEF-001: LP-scope use_impact (from lease_use_impact.py) carries use_reasoning,
    # confidence, and evaluator_agreement — copy them alongside the consequence fields.
    for f, lp in already_assessed_pairs:
        ui = _normalize_consequence(lp.get("use_impact") or {})
        _s7d = f.get("directionality")
        f["stage7_direction"] = _s7d
        f["stage7_direction_source"] = "stage7" if _s7d is not None else "absent"
        f["use_consequence"] = ui.get("use_consequence", "context_dependent")
        f["use_consequence_source"] = "assessed"
        # DEF-005 (F3): materiality_source tracks the materiality value's OWN provenance,
        # independent of consequence provenance. Only "assessed" if a valid materiality
        # value was actually present in the LP-scope use_impact.
        _lp_mat = ui.get("materiality")
        if _lp_mat in _VALID_MATERIALITY:
            f["materiality"] = _lp_mat
            f["materiality_source"] = "assessed"
        else:
            f["materiality"] = "low"
            f["materiality_source"] = "defaulted_low"  # no valid materiality from LP-scope
        f["assessment_scope"] = "finding_linked_lp"
        # DEF-001 fix — persist reasoning provenance from LP-scope assessment
        f["use_consequence_reasoning"]       = ui.get("use_reasoning")
        f["consequence_confidence"]          = ui.get("confidence")
        f["consequence_evaluator_agreement"] = ui.get("evaluator_agreement")

    # ── No use_profile → keyless mode, mark unassessed findings as absent ─────
    if not use_profile:
        logger.warning(
            "[lease_finding_consequence] No use_profile — marking unassessed findings as absent"
        )
        for f, _ in needs_assessment_pairs:
            _s7d = f.get("directionality")
            f["stage7_direction"] = _s7d
            f["stage7_direction_source"] = "stage7" if _s7d is not None else "absent"
            f["use_consequence"] = "context_dependent"
            f["materiality"] = "low"
            f["use_consequence_source"] = "absent"
            f["materiality_source"] = "absent"
            f["assessment_scope"] = "finding_linked_lp"
            # DEF-001 fix — no evaluator ran; persist null/boilerplate honestly
            f["use_consequence_reasoning"]       = None
            f["consequence_confidence"]          = "no_evaluators"
            f["consequence_evaluator_agreement"] = None
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
        _s7d = f.get("directionality")
        f["stage7_direction"] = _s7d
        f["stage7_direction_source"] = "stage7" if _s7d is not None else "absent"

        uc = verdict.get("use_consequence")
        support_label = verdict.get("consequence_support_label", "no_evaluators")

        # DEF-003: "assessed" source requires at least duo support (2+ valid evaluators).
        # insufficient_support (1 valid) is preserved as diagnostic but NOT stamped "assessed".
        # This ensures Rule 1a (csrc != "assessed") fires in P2'', routing Review Needed.
        if uc in _VALID_USE_CONSEQUENCE and support_label not in ("no_evaluators", "insufficient_support"):
            f["use_consequence"] = uc
            f["use_consequence_source"] = "assessed"

            # DEF-004 + DEF-005: materiality_source tracks materiality's OWN provenance.
            # route_to_review_needed=True (no-majority) also forces non-"assessed" source.
            _mat_src = verdict.get("materiality_source", "assessed")
            _route_rnr = verdict.get("route_to_review_needed", False)
            if _route_rnr:
                # No-majority materiality → cannot assert material tier; force Review Needed path
                f["materiality"] = verdict.get("materiality", "low")
                f["materiality_source"] = "no_majority"
                # Override consequence source to prevent Rule 3 (Risk routing)
                f["use_consequence_source"] = "no_majority_materiality"
            elif _mat_src not in ("assessed",):
                # Zero valid materiality returns or other non-assessed provenance
                f["materiality"] = verdict.get("materiality", "low")
                f["materiality_source"] = _mat_src  # "no_valid_materiality", "defaulted_low", etc.
            else:
                f["materiality"] = verdict.get("materiality", "low")
                f["materiality_source"] = "assessed"

            # DEF-003: persist all consequence support provenance fields
            f["consequence_support_label"]       = support_label
            f["expected_evaluator_count"]        = verdict.get("expected_evaluator_count", 3)
            f["valid_evaluator_count"]           = verdict.get("valid_evaluator_count", 0)
            f["vote_distribution"]               = verdict.get("vote_distribution", {})
            # DEF-004: persist materiality provenance fields
            f["materiality_votes"]               = verdict.get("materiality_votes", [])
            f["materiality_support"]             = verdict.get("materiality_support")
            f["materiality_agreement"]           = verdict.get("materiality_agreement")
            f["materiality_disputed"]            = verdict.get("materiality_disputed", False)
            # DEF-001 fix — persist reasoning provenance from merged verdict
            f["use_consequence_reasoning"]       = verdict.get("use_reasoning")
            f["consequence_confidence"]          = verdict.get("confidence")
            f["consequence_evaluator_agreement"] = verdict.get("evaluator_agreement")
            n_newly_assessed += 1

        elif uc in _VALID_USE_CONSEQUENCE and support_label == "insufficient_support":
            # DEF-003: 1 valid evaluator — preserve verdict as diagnostic, but NOT "assessed"
            # P2'' Rule 1a will fire (csrc != "assessed") → Review Needed
            f["use_consequence"] = uc
            f["use_consequence_source"] = "insufficient_consequence_support"
            f["materiality"] = verdict.get("materiality", "low")
            f["materiality_source"] = verdict.get("materiality_source", "no_valid_materiality")
            f["consequence_support_label"]       = support_label
            f["expected_evaluator_count"]        = verdict.get("expected_evaluator_count", 3)
            f["valid_evaluator_count"]           = verdict.get("valid_evaluator_count", 0)
            f["vote_distribution"]               = verdict.get("vote_distribution", {})
            f["materiality_votes"]               = verdict.get("materiality_votes", [])
            f["materiality_support"]             = verdict.get("materiality_support")
            f["materiality_agreement"]           = verdict.get("materiality_agreement")
            f["materiality_disputed"]            = verdict.get("materiality_disputed", False)
            f["use_consequence_reasoning"]       = verdict.get("use_reasoning")
            f["consequence_confidence"]          = verdict.get("confidence")
            f["consequence_evaluator_agreement"] = verdict.get("evaluator_agreement")
            n_absent += 1  # counts as not fully assessed for routing purposes

        else:
            f["use_consequence"] = "context_dependent"
            f["materiality"] = "low"
            f["use_consequence_source"] = "absent"
            f["materiality_source"] = "absent"
            f["consequence_support_label"]       = "no_evaluators"
            f["expected_evaluator_count"]        = 3
            f["valid_evaluator_count"]           = 0
            f["vote_distribution"]               = {}
            f["materiality_votes"]               = []
            f["materiality_support"]             = "no_valid_materiality"
            f["materiality_agreement"]           = None
            f["materiality_disputed"]            = False
            # DEF-001 fix — no valid verdict; persist null/boilerplate honestly
            f["use_consequence_reasoning"]       = None
            f["consequence_confidence"]          = "no_evaluators"
            f["consequence_evaluator_agreement"] = None
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
