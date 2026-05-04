"""
Stage 5d: Use-Aware Coverage Classification (Step 301)

Adjusts coverage states based on the tenant's stated permitted use, providing the
third declared-external-context dimension in CAM's compositional governance architecture
(after jurisdiction / Stage 5b and perspective / exposure layer).

Architecture:
  - Two model calls (gpt-5.5, low temperature)
  - Call 1: generate a structured use profile from the permitted_use string
  - Call 2: batched classification — one call covers all 32 LPs
  - Never touches potentially_unenforceable, missing, not_applicable, or broken_xref
  - No downgrades in v1 — only escalates or holds

Baseline preservation:
  Every CA entry gets `coverage_state_baseline` at initial assessment time (set in
  lease_coverage._build_assessment). Stage 5d sets `use_adjusted` and
  `use_adjustment_reason` on each entry it touches.

Usage:
    from cam.adapters.lease_review.lease_use_aware_coverage import (
        should_run_use_analysis,
        generate_use_profile,
        assess_use_aware_coverage,
    )
"""

import json
import logging
import re

logger = logging.getLogger(__name__)

# ── Feature flag ───────────────────────────────────────────────────────────────

# Step 301a: Gated pending multi-evaluator replacement (Step 302).
# Single-evaluator Stage 5d showed unacceptable variance during 2026-05-04 testing
# (3/4/0 adjustments across runs of identical file). Re-enable when Step 302 ships.
STAGE_5D_ENABLED = False

# ── Constants ──────────────────────────────────────────────────────────────────

# States Stage 5d never touches — already at top of severity stack or absent
_SKIP_STATES = frozenset({
    "potentially_unenforceable", "missing", "not_applicable", "broken_xref",
})

# Allowed target states per source state. Empty set = reason only, no state change.
_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "covered":             {"covered_unfavorable"},
    "partial":             {"covered_unfavorable"},
    "covered_unfavorable": set(),   # reason recorded; state unchanged
    "review_needed":       {"covered_unfavorable"},
    "ambiguous":           set(),
}

# Generic / non-specific use phrases that don't justify a use analysis
_GENERIC_PATTERNS = (
    r"^any lawful (purpose|use|retail use|business)\b",
    r"^retail sales?$",
    r"^general retail\b",
    r"^any (retail|commercial|permitted) use\b",
    r"^any legal purpose\b",
)


# ── Gating logic ──────────────────────────────────────────────────────────────

def should_run_use_analysis(permitted_use: str | None) -> bool:
    """Return True iff the permitted_use clause is specific enough to warrant Stage 5d.

    Skips when:
    - permitted_use is absent or blank
    - fewer than 8 substantive words (too generic)
    - matches known generic patterns ("any lawful purpose" etc.)
    """
    if not permitted_use or not permitted_use.strip():
        return False
    cleaned = permitted_use.strip()
    words = [w for w in re.split(r"\s+", cleaned) if len(w) >= 3]
    if len(words) < 8:
        return False
    lower = cleaned.lower()
    for pattern in _GENERIC_PATTERNS:
        if re.match(pattern, lower):
            return False
    return True


# ── Call 1: Use Profile Generation ────────────────────────────────────────────

_PROFILE_SYSTEM = """You extract structured use profile information from commercial lease permitted use clauses.
Return a single JSON object with exactly these fields. Infer from the clause text; do not hallucinate.
If a field is not evident from the clause, use null or an empty list.

Fields:
- business_type: short description of the business
- operational_dependencies: list of key operational requirements (max 5)
- refrigeration_perishables: null | "None" | short description of criticality
- regulated_activity: null | description of applicable regulation (DEA, FDA, liquor board, health dept, etc.)
- hazardous_material_sensitivity: "None" | "Low" | "Moderate" | "High"
- hours_access_sensitivity: "Standard" | "Extended" | "24-hour" | description
- other_use_risk_factors: list of other lease-relevant risk factors (max 3)

Return only the JSON object, no markdown, no commentary."""


def generate_use_profile(permitted_use: str) -> dict | None:
    """Call 1 — generate a structured use profile from the permitted use clause.

    Returns a dict on success, None on model failure (caller treats as skip).
    """
    from cam.core.provider_router import ModelTarget, ProviderRouter, RouterConfig
    from cam.core.json_extract import safe_json_extract

    raw = ""
    try:
        target = ModelTarget(
            name="openai:gpt-5.5",
            provider="openai",
            model="gpt-5.5",
            max_output_tokens=600,
        )
        router = ProviderRouter([target], RouterConfig())
        adapter = router._get_adapter("openai")

        user_prompt = f"Permitted use clause:\n\n{permitted_use.strip()}"
        raw = adapter.call(_PROFILE_SYSTEM, user_prompt, target).strip()

        profile = safe_json_extract(raw)
        if not isinstance(profile, dict):
            raise ValueError("Profile is not a dict")
        logger.info(f"[lease_use_aware] Use profile generated: business_type={profile.get('business_type')}")
        return profile
    except Exception as e:
        logger.warning(
            f"[lease_use_aware] Use profile generation failed: {e} "
            f"| raw[:200]={repr(raw[:200])}"
        )
        return None


# ── Call 2: Batched Use-Aware Classification ──────────────────────────────────

_CLASSIFY_SYSTEM = """You are a commercial real estate attorney assessing whether a tenant's specific business use
creates material legal or operational risk under each lease provision, given the current coverage classification.

CRITICAL DEFAULT: Most provisions are NOT materially affected by the tenant's specific use.
Return "none" for at least 25 of 32 provisions on most leases.
Return a non-none adjustment ONLY when the use creates a *concrete, substantial* change in
the legal or business consequence of the current coverage state — not based on generic claims
that "this type of business needs X." The adjustment must be tied to specific clause language
or missing elements described in the LP data, and specific to the actual use profile.

Do NOT invent use-sensitivity. Do NOT adjust based on speculative or attenuated reasoning.
Returning "none" for 28–32 LPs is the expected and correct outcome on most leases.

Allowed adjustments (v1):
  covered → covered_unfavorable   (provision exists but becomes actively adverse given use)
  partial → covered_unfavorable   (partial provision becomes actively harmful given use)
  covered_unfavorable → covered_unfavorable  (state unchanged; omit or set adjustment="none")

No downgrades. Do not change potentially_unenforceable, missing, or not_applicable items.
Do not invent coverage improvements.

Return a JSON object with one key per LP, exactly like this example:
{
  "LP-01": {"adjustment": "none"},
  "LP-19": {"adjustment": "covered_unfavorable", "reason": "Specific reason tied to this clause and this use..."},
  "LP-32": {"adjustment": "covered_unfavorable", "reason": "Specific reason..."}
}

Rules for a valid "reason" string:
- Must reference the specific clause deficiency (e.g. "no outage abatement", "no DEA-specific carve-out")
- Must explain why this particular use makes the deficiency materially worse
- Must be 1–3 sentences. No generic boilerplate.
- If adjustment is "none", reason may be omitted.

Return only the JSON object."""


def _build_lp_summary(ca: list) -> str:
    """Serialize CA entries to a compact string for the Call 2 prompt."""
    lines = []
    for a in ca:
        pid = a.get("issue_area_id", "")
        state = a.get("coverage_state", "")
        if state in _SKIP_STATES:
            lines.append(f"{pid}: SKIP (state={state})")
            continue
        name = a.get("issue_area_name", pid)
        found = a.get("elements_found", [])[:3]
        missing = a.get("elements_missing", [])[:3]
        evidence = (a.get("evidence_summary") or "")[:150]
        lines.append(
            f"{pid} [{name}] state={state} | "
            f"found=[{', '.join(found)}] | missing=[{', '.join(missing)}] | evidence: {evidence}"
        )
    return "\n".join(lines)


def assess_use_aware_coverage(
    use_profile: dict,
    coverage_assessment: list,
    cfg: dict | None = None,
) -> tuple[list, list]:
    """Call 2 — batch classify all LPs for use-sensitivity.

    Returns:
        (updated_coverage_assessment, adjustment_log)
        adjustment_log: list of dicts {lp_id, from_state, to_state, reason}
    """
    from cam.core.provider_router import ModelTarget, ProviderRouter, RouterConfig
    from cam.core.json_extract import safe_json_extract

    adjustment_log = []
    raw = ""

    try:
        target = ModelTarget(
            name="openai:gpt-5.5",
            provider="openai",
            model="gpt-5.5",
            max_output_tokens=2500,
        )
        router = ProviderRouter([target], RouterConfig())
        adapter = router._get_adapter("openai")

        profile_str = json.dumps(use_profile, indent=2)
        lp_summary = _build_lp_summary(coverage_assessment)
        user_prompt = (
            f"USE PROFILE:\n{profile_str}\n\n"
            f"LEASE PROVISION COVERAGE (32 LPs):\n{lp_summary}"
        )

        raw = adapter.call(_CLASSIFY_SYSTEM, user_prompt, target).strip()

        adjustments: dict = safe_json_extract(raw)
        if not isinstance(adjustments, dict):
            raise ValueError("Adjustments response is not a dict")

        logger.info(f"[lease_use_aware] Parsed adjustments for {len(adjustments)} LPs")

    except Exception as e:
        logger.warning(
            f"[lease_use_aware] Use-aware classification failed: {e} "
            f"| raw[:200]={repr(raw[:200])}"
        )
        return coverage_assessment, []

    # Apply validated adjustments to coverage_assessment (mutates in place)
    ca_by_pid = {a["issue_area_id"]: a for a in coverage_assessment}

    for pid, entry in adjustments.items():
        if not isinstance(entry, dict):
            continue
        adj = (entry.get("adjustment") or "none").strip()
        if adj == "none":
            continue

        assessment = ca_by_pid.get(pid)
        if not assessment:
            logger.warning(f"[lease_use_aware] LP {pid} not found in coverage_assessment, skipping")
            continue

        current_state = assessment.get("coverage_state", "")
        if current_state in _SKIP_STATES:
            logger.info(f"[lease_use_aware] {pid}: skipping (state={current_state} is protected)")
            continue

        # Resolve target state
        target_state = adj  # model returns e.g. "covered_unfavorable"
        allowed = _ALLOWED_TRANSITIONS.get(current_state, set())
        if target_state not in allowed:
            logger.info(
                f"[lease_use_aware] {pid}: rejected transition {current_state} → {target_state} "
                f"(not in allowed set {allowed})"
            )
            continue

        reason = (entry.get("reason") or "").strip()
        if not reason:
            logger.info(f"[lease_use_aware] {pid}: transition to {target_state} has no reason, skipping")
            continue

        # Apply the adjustment
        from_state = current_state
        assessment["coverage_state"] = target_state
        assessment["use_adjusted"] = True
        assessment["use_adjustment_reason"] = reason

        # When escalating to covered_unfavorable, ensure adverse_to is populated
        if target_state == "covered_unfavorable" and not assessment.get("covered_unfavorable_adverse_to"):
            assessment["covered_unfavorable_adverse_to"] = "tenant"

        adjustment_log.append({
            "lp_id": pid,
            "from": from_state,
            "to": target_state,
            "reason": reason,
        })
        logger.info(f"[lease_use_aware] {pid}: {from_state} → {target_state}")

    logger.info(
        f"[lease_use_aware] Use-aware classification complete: "
        f"{len(adjustment_log)} adjustment(s) applied"
    )
    return coverage_assessment, adjustment_log
