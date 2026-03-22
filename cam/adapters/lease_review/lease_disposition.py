"""
CAM Lease Review — Stage 6: Final Disposition

0 API calls. Pure Python that assembles the final result for each provision
from all previous stages.
"""

from typing import Any, Dict, List, Optional


# ── Severity Floor Guardrails ──
# For legally sensitive provisions, enforce a minimum severity level
# to prevent the model from soft-reasoning material changes down to LOW/MEDIUM.
# Only applied to DEVIATES verdicts.
SEVERITY_RANK = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}

SEVERITY_FLOORS = {
    # Financial provisions — money changes are always material
    "LP-01": "HIGH",    # Rent & Payment Terms
    "LP-02": "HIGH",    # Rent Escalation
    "LP-07": "HIGH",    # CAM Charges
    # Core landlord control provisions — consent/approval changes are material
    "LP-09": "HIGH",    # Subletting & Assignment
    "LP-10": "HIGH",    # Landlord Access & Entry
    # Default and risk provisions — always material
    "LP-11": "HIGH",    # Default & Remedies
    "LP-12": "HIGH",    # Indemnification & Liability
    # Casualty and termination — structural deal terms
    "LP-13": "HIGH",    # Damage, Destruction & Condemnation
    "LP-14": "HIGH",    # Force Majeure
}


def apply_severity_floor(provision_id: str, model_severity: str) -> tuple:
    """Apply deterministic severity floor for sensitive provisions.

    Returns:
        (final_severity, floor_applied) — floor_applied is True if upgraded.
    """
    floor = SEVERITY_FLOORS.get(provision_id)
    if not floor:
        return model_severity, False
    if SEVERITY_RANK.get(model_severity, 99) > SEVERITY_RANK.get(floor, 99):
        return floor, True  # upgrade to floor
    return model_severity, False  # model was already at or above floor


def apply_severity_modifier(
    provision_id: str,
    model_severity: str,
    fragility: dict,
    challenge: dict,
    extraction: dict,
) -> tuple:
    """Apply signal-based severity modifier after model assessment.

    Catches material changes the provision-ID floors don't cover.
    Based on change type and fragility signals, not provision identity.

    Architecture note: Severity is a judgment layer, not a detection layer.
    This modifier enforces policy-level constraints the model won't reliably
    self-enforce — it does not replace model judgment.

    Returns:
        (final_severity, modifier_applied, modifier_reason)
    """
    signals = [r.get("signal", "") for r in fragility.get("rules_fired", [])]
    challenge_verdict = (challenge or {}).get("challenge_verdict", "")
    status = extraction.get("status", "")

    # Rule M-01: obligation_swap affecting core landlord right → minimum HIGH
    # An obligation swap means party responsibilities shifted. If the shift
    # involves a core landlord right (consent, approval, access, indemnity),
    # this is always at least HIGH regardless of provision.
    if "obligation_swap" in signals:
        if SEVERITY_RANK.get(model_severity, 99) > SEVERITY_RANK.get("HIGH", 99):
            return "HIGH", True, "M-01: obligation_swap on core landlord right"

    # Rule M-02: complete omission of template provision → minimum HIGH
    # If the entire provision was removed from the tenant lease, that is always
    # a material change regardless of what the provision covers.
    if status == "TEMPLATE_ONLY":
        if SEVERITY_RANK.get(model_severity, 99) > SEVERITY_RANK.get("HIGH", 99):
            return "HIGH", True, "M-02: complete omission of template provision"

    # Rule M-03: substantive_deviation + quantitative_deviation on financial provision
    # Numerical changes to financial terms (rent, percentages, time periods)
    # confirmed as substantive by challenger → minimum HIGH
    financial_pids = {"LP-01", "LP-02", "LP-03", "LP-07"}
    if (
        challenge_verdict == "SUBSTANTIVE_DEVIATION"
        and "quantitative_deviation" in signals
        and provision_id in financial_pids
    ):
        if SEVERITY_RANK.get(model_severity, 99) > SEVERITY_RANK.get("HIGH", 99):
            return "HIGH", True, "M-03: quantitative deviation on financial provision"

    # Rule M-04: negation_pattern + qualifier_shift together → minimum MEDIUM
    # Both negation and qualifier shift firing together indicates a compound
    # structural change — not just one weakened word but a reversal pattern.
    if "negation_pattern" in signals and "qualifier_shift" in signals:
        if SEVERITY_RANK.get(model_severity, 99) > SEVERITY_RANK.get("MEDIUM", 99):
            return "MEDIUM", True, "M-04: compound negation + qualifier shift"

    return model_severity, False, ""


# Patterns in definition_changes field that mean "no change" — ignore these
_NO_CHANGE_PATTERNS = [
    "no change", "no difference", "identical", "same as", "none",
    "not applicable", "n/a", "no modification", "unchanged",
    "no definition change", "definitions are the same", "no changes",
]


def _has_real_definition_change(text: str) -> bool:
    """Return True only if definition_changes field describes an actual change."""
    if not text or not text.strip():
        return False
    lower = text.strip().lower()
    return not any(pattern in lower for pattern in _NO_CHANGE_PATTERNS)


def triage_provisions(
    aggregated_evals: List[dict],
    fragility_results: List[dict],
    extraction_provisions: List[dict],
    cascade_results: Dict[str, dict] = None,
) -> tuple:
    """Split provisions into passed (done) and flagged (need challenge/severity).

    Flagged if ANY of:
    - At least one evaluator said DEVIATES or UNCLEAR
    - Any lease rule fired on this provision (except RULE-LS-002 handled by cascade)
    - RULE-LS-002 fired AND cascade says CASCADE_MATERIAL
    - Provision status from Stage 1 was TEMPLATE_ONLY or AMBIGUOUS

    When cascade results are available, RULE-LS-002 alone does NOT flag a provision.
    Only CASCADE_MATERIAL verdicts cause flagging.

    Returns:
        (passed, flagged) — both are lists of dicts with provision info.
    """
    cascade_results = cascade_results or {}
    frag_map = {f["provision_id"]: f for f in fragility_results}
    ext_map = {p["provision_id"]: p for p in extraction_provisions}

    passed = []
    flagged = []

    for agg in aggregated_evals:
        pid = agg["provision_id"]
        verdicts = agg.get("verdicts", {})
        frag = frag_map.get(pid, {})
        ext = ext_map.get(pid, {})

        flag_reasons = []

        # Check evaluator verdicts
        for key, v in verdicts.items():
            if v in ("DEVIATES", "UNCLEAR"):
                flag_reasons.append(f"evaluator_{key}={v}")

        # Check fragility rules — with cascade-aware RULE-LS-002 handling
        if frag.get("fragile") and frag.get("rules_fired"):
            for r in frag["rules_fired"]:
                if r.get("confidence", 0) >= 0.5:
                    if r["rule_id"] == "RULE-LS-002":
                        # RULE-LS-002: check cascade verdict instead of raw rule fire
                        cascade = cascade_results.get(pid, {})
                        if cascade.get("verdict") == "CASCADE_MATERIAL":
                            flag_reasons.append("cascade=CASCADE_MATERIAL")
                        # CASCADE_IMMATERIAL: record but don't flag
                        # No cascade result yet (shouldn't happen): fall back to flagging
                        elif not cascade:
                            flag_reasons.append(f"rule={r['rule_id']}")
                    else:
                        flag_reasons.append(f"rule={r['rule_id']}")

        # Check extraction status
        status = ext.get("status", "FOUND_BOTH")
        if status in ("TEMPLATE_ONLY", "AMBIGUOUS"):
            flag_reasons.append(f"extraction_status={status}")

        # Check definition changes (only flag if actual change content, not "no change" text)
        # Skip this if cascade already handled the definition change
        defn = ext.get("definition_changes", "")
        cascade = cascade_results.get(pid, {})
        if _has_real_definition_change(defn) and not cascade:
            flag_reasons.append("definition_change_detected")

        item = {
            "provision_id": pid,
            "provision_name": agg.get("provision_name", pid),
            "fragility": frag,
        }

        if flag_reasons:
            item["flag_reasons"] = flag_reasons
            flagged.append(item)
        else:
            passed.append(item)

    return passed, flagged


def compute_disposition(
    provision_id: str,
    extraction: dict,
    fragility: dict,
    evaluation: dict,
    challenge: Optional[dict],
    severity: Optional[dict],
    triage_result: str,
    cascade: Optional[dict] = None,
) -> dict:
    """Compute final disposition for a single provision.

    cascade: If present, the cascade micro-stage result for this provision.
             CASCADE_MATERIAL overrides evaluator CONFORMS when text is identical
             but definition changed.
    """
    pname = extraction.get("provision_name", provision_id)

    # Determine final verdict
    # CASCADE_MATERIAL override: if cascade confirms material impact, force DEVIATES
    # even if evaluators say CONFORMS (they see identical text)
    cascade_material = cascade and cascade.get("verdict") == "CASCADE_MATERIAL"

    if triage_result == "PASSED" and not cascade_material:
        final_verdict = "CONFORMS"
        sev = "CONFORMS"
        stages_run = [1, 2, 4, 6]
    elif cascade_material and (
        not challenge or challenge.get("challenge_verdict") in ("COSMETIC_ONLY", None)
    ):
        # Cascade says MATERIAL but challenger missed it (or wasn't run yet on this provision)
        # Cascade overrides → DEVIATES
        final_verdict = "DEVIATES"
        sev = severity.get("severity", "MEDIUM") if severity else "MEDIUM"
        stages_run = [1, 2, 4, 5, 6]
        if challenge:
            stages_run = [1, 2, 3, 4, 5, 6]
    elif challenge and challenge.get("challenge_verdict") == "COSMETIC_ONLY" and not cascade_material:
        # COSMETIC_ONLY challenger behaviour depends on evaluator unanimity:
        #
        # Unanimous (3-0 or 2-0 DEVIATES): challenger is a single model — it cannot
        # veto three independent unanimous evaluators. Hold DEVIATES; record challenger
        # disagreement as a fragility signal in cam_metadata.
        #
        # Majority (2-1 DEVIATES): genuine disagreement between evaluators and
        # challenger. CAM invariant: unresolved disagreement → UNCLEAR.
        #
        # CONFORMS majority or no majority: challenger's COSMETIC_ONLY is persuasive.
        majority_v = evaluation.get("majority_verdict", "")
        pattern = evaluation.get("agreement_pattern", "")
        is_unanimous = pattern.startswith("3-0") or pattern.startswith("2-0")

        if majority_v == "DEVIATES" and is_unanimous:
            # Unanimous evaluators override COSMETIC_ONLY challenger (Step 191 fix)
            final_verdict = "DEVIATES"
            sev = severity.get("severity", "MEDIUM") if severity else "MEDIUM"
            stages_run = [1, 2, 3, 4, 5, 6]
        elif majority_v == "DEVIATES":
            # Split evaluators + COSMETIC_ONLY challenger — genuine disagreement.
            # CAM invariant: unresolved disagreement → UNCLEAR.
            final_verdict = "UNCLEAR"
            sev = "REVIEW"
            stages_run = [1, 2, 3, 4, 6]
        else:
            # Majority was CONFORMS or unclear — challenger's COSMETIC_ONLY is persuasive.
            final_verdict = "CONFORMS"
            sev = "CONFORMS"
            stages_run = [1, 2, 3, 4, 6]
    elif extraction.get("status") == "TEMPLATE_ONLY":
        final_verdict = "DEVIATES"
        sev = severity.get("severity", "HIGH") if severity else "HIGH"
        stages_run = [1, 2, 3, 4, 5, 6]
    elif challenge and challenge.get("challenge_verdict") == "SUBSTANTIVE_DEVIATION":
        final_verdict = "DEVIATES"
        sev = severity.get("severity", "MEDIUM") if severity else "MEDIUM"
        stages_run = [1, 2, 3, 4, 5, 6]
    elif challenge and challenge.get("challenge_verdict") == "NEEDS_EXPERT":
        final_verdict = "UNCLEAR"
        sev = "REVIEW"
        stages_run = [1, 2, 3, 4, 6]
    else:
        # CAM invariant: unresolved disagreement surfaces as UNCLEAR, not majority vote.
        # If evaluators split and challenge did not resolve it, the correct output is
        # "we don't know" — not whichever side had more votes.
        pattern = evaluation.get("agreement_pattern", "")
        is_split = any(x in pattern for x in ["split", "1-1", "3-way", "2-1", "1-2"])
        if is_split:
            final_verdict = "UNCLEAR"
            sev = "REVIEW"
        else:
            # Unanimous or near-unanimous without challenge resolution — use consensus
            final_verdict = evaluation.get("majority_verdict", "UNCLEAR")
            sev = severity.get("severity", "MEDIUM") if severity else "MEDIUM"
        stages_run = [1, 2, 3, 4, 5, 6]

    # Apply severity governance for DEVIATES verdicts:
    # Step 1 — Signal-based modifier (cross-cutting, change-type rules)
    # Step 2 — Provision floor (ID-based hard minimums)
    # Order matters: modifier runs first, floor catches anything still too low.
    severity_modifier_applied = False
    severity_modifier_reason = ""
    severity_floor_applied = False
    if final_verdict == "DEVIATES":
        sev, severity_modifier_applied, severity_modifier_reason = apply_severity_modifier(
            provision_id=provision_id,
            model_severity=sev,
            fragility=fragility,
            challenge=challenge or {},
            extraction=extraction,
        )
        sev, severity_floor_applied = apply_severity_floor(provision_id, sev)

    # Build rules fired list
    rules_fired = [r["rule_id"] for r in fragility.get("rules_fired", [])]
    fragility_signals = [r["signal"] for r in fragility.get("rules_fired", [])]

    result = {
        "provision_id": provision_id,
        "provision_name": pname,
        "final_verdict": final_verdict,
        "severity": sev,
        "severity_floor_applied": severity_floor_applied,
        "severity_modifier_applied": severity_modifier_applied,
        "severity_modifier_reason": severity_modifier_reason,
        "discovered": extraction.get("discovered", False),
        "agreement_pattern": evaluation.get("agreement_pattern", "unknown"),
        "evaluator_verdicts": evaluation.get("verdicts", {}),
        "evaluator_reasoning": evaluation.get("reasoning", {}),
        "evaluator_confidences": evaluation.get("confidences", {}),
        "challenge_finding": challenge.get("challenge_verdict") if challenge else None,
        "challenge_details": challenge.get("substantive_finding", "") if challenge else "",
        "risk_headline": challenge.get("risk_headline", "") if challenge else "",
        "hidden_dependencies": challenge.get("hidden_dependencies", []) if challenge else [],
        "cascade_verdict": cascade.get("verdict") if cascade else None,
        "cascade_mechanism": cascade.get("mechanism", "") if cascade else "",
        "cascade_impact": cascade.get("impact_summary", "") if cascade else "",
        "cascade_source": {
            "term": cascade.get("changed_term", ""),
            "defined_in": extraction.get("template_section_ref", ""),
        } if cascade and cascade.get("changed_term") else None,
        "fragility": {
            "fragile": fragility.get("fragile", False),
            "score": fragility.get("fragility_score", 0.0),
            "signals": fragility_signals,
        },
        "severity_reasoning": severity.get("severity_reasoning", "") if severity else "",
        "financial_impact": severity.get("financial_impact", "") if severity else "",
        "recommended_action": _compute_recommended_action(final_verdict, sev, challenge, severity),
        "template_text": extraction.get("template_text", ""),
        "tenant_text": extraction.get("tenant_text", ""),
        "template_section_ref": extraction.get("template_section_ref", ""),
        "tenant_section_ref": extraction.get("tenant_section_ref", ""),
        "definition_changes": extraction.get("definition_changes", ""),
        "cam_metadata": {
            "stages_run": stages_run,
            "rules_fired": rules_fired,
            "triage_result": triage_result,
            "cascade_verdict": cascade.get("verdict") if cascade else None,
        },
    }

    # LP-00 metadata-only mode: suppress verdict
    if extraction.get("_identity_check_mode") == "metadata_only":
        result["final_verdict"] = "CONFORMS"
        result["severity"] = "REVIEW"
        result["cam_metadata"]["identity_check_suppressed"] = True

    return result


def _compute_recommended_action(
    verdict: str,
    severity: str,
    challenge: Optional[dict],
    severity_result: Optional[dict],
) -> str:
    """Determine the recommended action based on verdict and severity."""
    if verdict == "CONFORMS":
        return "no_action"
    if verdict == "UNCLEAR":
        return "attorney_review_recommended"

    # Use severity assessor's recommendation if available
    if severity_result and severity_result.get("recommended_action"):
        return severity_result["recommended_action"]

    # Use challenger's recommendation if available
    if challenge and challenge.get("recommended_action"):
        return challenge["recommended_action"]

    # Fallback based on severity
    severity_actions = {
        "CRITICAL": "attorney_review_required",
        "HIGH": "attorney_review_recommended",
        "MEDIUM": "note_for_awareness",
        "LOW": "note_for_awareness",
    }
    return severity_actions.get(severity, "note_for_awareness")


def compute_all_dispositions(
    extraction_provisions: List[dict],
    fragility_results: List[dict],
    evaluation_aggregated: List[dict],
    challenge_results: Dict[str, dict],
    severity_results: Dict[str, dict],
    passed_ids: set,
    flagged_ids: set,
    cascade_results: Dict[str, dict] = None,
) -> List[dict]:
    """Compute dispositions for all provisions.

    Args:
        extraction_provisions: Stage 1 results.
        fragility_results: Stage 4 results.
        evaluation_aggregated: Stage 2 aggregated results.
        challenge_results: Stage 3 results (provision_id -> dict).
        severity_results: Stage 5 results (provision_id -> dict).
        passed_ids: Set of provision IDs that passed triage.
        flagged_ids: Set of provision IDs that were flagged.
        cascade_results: Cascade micro-stage results (provision_id -> dict).

    Returns:
        List of disposition dicts (one per provision).
    """
    cascade_results = cascade_results or {}
    ext_map = {p["provision_id"]: p for p in extraction_provisions}
    frag_map = {f["provision_id"]: f for f in fragility_results}
    eval_map = {a["provision_id"]: a for a in evaluation_aggregated}

    dispositions = []
    for prov in extraction_provisions:
        pid = prov["provision_id"]

        triage = "PASSED" if pid in passed_ids else "FLAGGED"

        disp = compute_disposition(
            provision_id=pid,
            extraction=ext_map.get(pid, {}),
            fragility=frag_map.get(pid, {}),
            evaluation=eval_map.get(pid, {}),
            challenge=challenge_results.get(pid),
            severity=severity_results.get(pid),
            triage_result=triage,
            cascade=cascade_results.get(pid),
        )
        dispositions.append(disp)

    return dispositions
