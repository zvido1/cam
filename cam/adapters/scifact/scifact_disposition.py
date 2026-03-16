"""
SciFact Disposition Layer (Stage 5)

Combines all prior stage outputs into terminal state and commitment level.
This is CAM's final word on each claim.

Terminal states: ASSERT_SUPPORT, ASSERT_CONTRADICT, ASSERT_NEI, WITHHOLD_ASSERTION
Commitment levels: L0 (Full Assert) through L4 (Withhold)

No API calls -- pure computation on Stages 1-4 outputs.
Gold comparison is POST-HOC only -- never influences disposition.
"""

from collections import Counter


# ============================================================
# Terminal States
# ============================================================

TERMINAL_STATES = {
    "ASSERT_SUPPORT":     "System asserts the claim is supported by the evidence",
    "ASSERT_CONTRADICT":  "System asserts the claim is contradicted by the evidence",
    "ASSERT_NEI":         "System asserts evidence is insufficient to determine",
    "WITHHOLD_ASSERTION": "System declines to assert any verdict",
}

# ============================================================
# Commitment Levels
# ============================================================

COMMITMENT_LEVELS = {
    "L0_FULL_ASSERT":    "Full assertion -- high confidence, strong grounding, no fragility",
    "L1_QUALIFIED":      "Qualified assertion -- asserted with disclosed conditions or limitations",
    "L2_CONDITIONAL":    "Conditional assertion -- depends on assumptions or has known weaknesses",
    "L3_LOW_CONFIDENCE": "Low confidence -- significant concerns, assertion made with major caveats",
    "L4_WITHHOLD":       "Withheld -- system declines to assert",
}

# Numeric ordering for level comparisons (higher number = more restrictive)
_LEVEL_ORDER = {
    "L0": 0,
    "L1": 1,
    "L2": 2,
    "L3": 3,
    "L4": 4,
}

_LEVEL_NAMES = {
    "L0": "L0_FULL_ASSERT",
    "L1": "L1_QUALIFIED",
    "L2": "L2_CONDITIONAL",
    "L3": "L3_LOW_CONFIDENCE",
    "L4": "L4_WITHHOLD",
}


def _more_restrictive_level(level_a, level_b):
    """Return the more restrictive (higher numbered) of two levels."""
    ord_a = _LEVEL_ORDER.get(level_a, 0)
    ord_b = _LEVEL_ORDER.get(level_b, 0)
    if ord_a >= ord_b:
        return level_a
    return level_b


# ============================================================
# Disposition Logic
# ============================================================

def compute_disposition(evaluations, challenge_result, auditor_result, fragility_profile):
    """
    Compute terminal state and commitment level for a single claim.

    Steps A-F as specified in the instruction:
    A. Determine majority verdict
    B. Check for WITHHOLD triggers
    C. Determine base commitment level
    D. Apply fragility cap
    E. Determine terminal state
    F. Build disposition record

    Args:
        evaluations: dict of evaluator label -> normalized response (Stage 1)
        challenge_result: normalized challenge response (Stage 2)
        auditor_result: normalized auditor response (Stage 3)
        fragility_profile: fragility profile dict (Stage 4)

    Returns:
        Disposition record dict.
    """
    conditions = []

    # ---- Step A: Determine majority verdict ----
    verdicts = []
    for label in sorted(evaluations.keys()):
        ev = evaluations[label]
        if "error" not in ev or "verdict" in ev:
            v = ev.get("verdict")
            if v:
                verdicts.append(v)

    counts = Counter(verdicts)
    most_common = counts.most_common()

    majority_verdict = None
    agreement_type = None

    if len(most_common) == 0:
        agreement_type = "none"
    elif len(most_common) == 1:
        majority_verdict = most_common[0][0]
        agreement_type = "3-0"
    elif most_common[0][1] >= 2:
        majority_verdict = most_common[0][0]
        agreement_type = "2-1"
    else:
        # 3-way split
        agreement_type = "1-1-1"

    # ---- Step B: Check for WITHHOLD triggers ----
    auditor_assessment = auditor_result.get("overall_assessment", "")
    fragility_cap = fragility_profile.get("max_cap")

    withhold = False
    withhold_reason = None

    # Trigger 1: No majority verdict (full 3-way split)
    if majority_verdict is None:
        withhold = True
        withhold_reason = "No majority verdict (full split)"

    # Trigger 2: Auditor FAIL
    if auditor_assessment == "FAIL":
        withhold = True
        withhold_reason = "Auditor assessment: FAIL"

    # Trigger 3: Fragility cap L1 AND auditor FLAG (double jeopardy)
    if fragility_cap == "L1" and auditor_assessment == "FLAG":
        withhold = True
        withhold_reason = "Double jeopardy: fragility cap L1 + auditor FLAG"

    if withhold:
        conditions.append(withhold_reason)
        return _build_record(
            terminal_state="WITHHOLD_ASSERTION",
            commitment_level="L4_WITHHOLD",
            majority_verdict=majority_verdict,
            agreement_type=agreement_type,
            base_level="L4",
            fragility_cap=fragility_cap,
            final_level="L4",
            auditor_assessment=auditor_assessment,
            fragile=fragility_profile.get("fragile", False),
            fired_rules=fragility_profile.get("fired_rules", []),
            signal_count=fragility_profile.get("signal_count", 0),
            conditions=conditions,
        )

    # ---- Step C: Determine base commitment level ----
    if agreement_type == "3-0" and auditor_assessment == "PASS":
        base_level = "L0"
    elif agreement_type == "3-0" and auditor_assessment == "FLAG":
        base_level = "L1"
    elif agreement_type == "2-1" and auditor_assessment == "PASS":
        base_level = "L1"
    elif agreement_type == "2-1" and auditor_assessment == "FLAG":
        base_level = "L2"
    else:
        # Default for unexpected combinations
        base_level = "L2"

    # ---- Step D: Apply fragility cap ----
    final_level = base_level
    if fragility_cap is not None:
        final_level = _more_restrictive_level(base_level, fragility_cap)
        if final_level != base_level:
            conditions.append(
                f"Fragility cap {fragility_cap} downgraded from {base_level} to {final_level}"
            )

    # Add conditions from fragility signals
    if fragility_profile.get("fragile"):
        fired = fragility_profile.get("fired_rules", [])
        if fired:
            conditions.append(f"Fragility rules: {', '.join(fired)}")
        # Add fragile agreement detail if present
        signals = fragility_profile.get("signals", [])
        for sig in signals:
            if sig.get("signal_id") == "fragile_agreement":
                conditions.append("Fragile agreement -- evaluators cite different evidence paths")
                break

    # ---- Step E: Determine terminal state ----
    if final_level == "L4":
        terminal_state = "WITHHOLD_ASSERTION"
    else:
        verdict_to_state = {
            "SUPPORT": "ASSERT_SUPPORT",
            "CONTRADICT": "ASSERT_CONTRADICT",
            "NOT_ENOUGH_INFO": "ASSERT_NEI",
        }
        terminal_state = verdict_to_state.get(majority_verdict, "WITHHOLD_ASSERTION")

    commitment_level = _LEVEL_NAMES.get(final_level, "L4_WITHHOLD")

    # ---- Step F: Build disposition record ----
    return _build_record(
        terminal_state=terminal_state,
        commitment_level=commitment_level,
        majority_verdict=majority_verdict,
        agreement_type=agreement_type,
        base_level=base_level,
        fragility_cap=fragility_cap,
        final_level=final_level,
        auditor_assessment=auditor_assessment,
        fragile=fragility_profile.get("fragile", False),
        fired_rules=fragility_profile.get("fired_rules", []),
        signal_count=fragility_profile.get("signal_count", 0),
        conditions=conditions,
    )


# ============================================================
# Disposition with Verdict Elimination (Stage 1b integration)
# ============================================================

def compute_disposition_with_elimination(evaluations, challenge_result, auditor_result,
                                          fragility_profile, elimination_result):
    """
    Compute disposition incorporating verdict elimination results.

    First computes the standard disposition, then applies elimination overrides:
    - If the majority verdict was killed by elimination, override to the surviving verdict
    - If elimination kills the majority verdict, apply additional fragility cap

    Args:
        evaluations: dict of evaluator label -> normalized response (Stage 1)
        challenge_result: normalized challenge response (Stage 2)
        auditor_result: normalized auditor response (Stage 3)
        fragility_profile: fragility profile dict (Stage 4)
        elimination_result: normalized elimination response (Stage 1b)

    Returns:
        Disposition record dict (with elimination_applied field).
    """
    # Get the base disposition without elimination
    base_disposition = compute_disposition(
        evaluations, challenge_result, auditor_result, fragility_profile
    )

    # If elimination result is missing or has errors, return base as-is
    if not elimination_result or "error" in elimination_result:
        base_disposition["elimination_applied"] = False
        return base_disposition

    majority_verdict = base_disposition.get("majority_verdict")
    conditions = list(base_disposition.get("conditions", []))

    # Check if the majority verdict was killed
    eliminations = elimination_result.get("eliminations", [])
    majority_killed = False
    kill_type = None
    for elim in eliminations:
        if elim.get("target_verdict") == majority_verdict and elim.get("killed"):
            majority_killed = True
            kill_type = elim.get("elimination_type", "unknown")
            break

    if not majority_killed:
        # Majority survived elimination — reinforce, no changes needed
        base_disposition["elimination_applied"] = True
        base_disposition["elimination_action"] = "reinforced"
        conditions.append(f"Elimination: majority verdict {majority_verdict} survived stress test")
        base_disposition["conditions"] = conditions
        return base_disposition

    # ---- Majority verdict was KILLED ----
    conditions.append(
        f"Elimination: majority verdict {majority_verdict} killed ({kill_type})"
    )

    survivors = elimination_result.get("survivors", [])
    recommended = elimination_result.get("recommended_verdict")
    confidence = elimination_result.get("confidence_after_elimination", "medium")

    # Determine the new effective verdict
    effective_verdict = None

    if len(survivors) == 1:
        # Single survivor — use it
        effective_verdict = survivors[0]
        conditions.append(f"Elimination: single survivor -> {effective_verdict}")
    elif len(survivors) > 1 and recommended:
        # Multiple survivors — prefer the one that matches remaining evaluator distribution
        # Count evaluator verdicts among survivors
        evaluator_verdicts = []
        for label in sorted(evaluations.keys()):
            ev = evaluations[label]
            v = ev.get("verdict")
            if v and v in survivors:
                evaluator_verdicts.append(v)

        if evaluator_verdicts:
            # Pick the most common surviving verdict among evaluators
            from collections import Counter as _Counter
            survivor_counts = _Counter(evaluator_verdicts)
            effective_verdict = survivor_counts.most_common(1)[0][0]
            conditions.append(
                f"Elimination: {len(survivors)} survivors, "
                f"best evaluator match -> {effective_verdict}"
            )
        else:
            # No evaluator verdicts match survivors — use recommended
            effective_verdict = recommended
            conditions.append(
                f"Elimination: {len(survivors)} survivors, "
                f"no evaluator match, using recommended -> {effective_verdict}"
            )
    elif recommended:
        effective_verdict = recommended
        conditions.append(f"Elimination: using recommended verdict -> {effective_verdict}")
    else:
        # Fallback: if all killed (shouldn't happen), WITHHOLD
        effective_verdict = None

    # Determine new commitment level
    # Killing the majority verdict is a strong fragility signal
    # Cap at L3 minimum, or WITHHOLD if:
    #   - No survivors match any evaluator
    #   - All verdicts were killed
    #   - Confidence is low

    if effective_verdict is None:
        # All killed or no usable survivor
        return _build_record(
            terminal_state="WITHHOLD_ASSERTION",
            commitment_level="L4_WITHHOLD",
            majority_verdict=majority_verdict,
            agreement_type=base_disposition.get("agreement_pattern"),
            base_level=base_disposition.get("base_level"),
            fragility_cap="L3",
            final_level="L4",
            auditor_assessment=base_disposition.get("auditor_assessment"),
            fragile=True,
            fired_rules=base_disposition.get("fired_rules", []),
            signal_count=base_disposition.get("signal_count", 0),
            conditions=conditions,
            elimination_applied=True,
            elimination_action="killed_to_withhold",
        )

    # The majority was killed but we have a surviving verdict
    # Cap at L3 if confidence is low, L2 if medium, leave alone if high
    elimination_cap = "L3" if confidence == "low" else "L2"

    # Apply the cap: take the more restrictive of existing cap and elimination cap
    existing_final = base_disposition.get("final_level", "L0")
    final_level = _more_restrictive_level(existing_final, elimination_cap)

    # Check if final level implies WITHHOLD
    if _LEVEL_ORDER.get(final_level, 0) >= 4:
        terminal_state = "WITHHOLD_ASSERTION"
        commitment_level = "L4_WITHHOLD"
        conditions.append(f"Elimination cap {elimination_cap} -> WITHHOLD")
    else:
        verdict_to_state = {
            "SUPPORT": "ASSERT_SUPPORT",
            "CONTRADICT": "ASSERT_CONTRADICT",
            "NOT_ENOUGH_INFO": "ASSERT_NEI",
        }
        terminal_state = verdict_to_state.get(effective_verdict, "WITHHOLD_ASSERTION")
        commitment_level = _LEVEL_NAMES.get(final_level, "L4_WITHHOLD")
        conditions.append(
            f"Elimination cap {elimination_cap} applied, "
            f"final={final_level}, verdict={effective_verdict}"
        )

    return _build_record(
        terminal_state=terminal_state,
        commitment_level=commitment_level,
        majority_verdict=majority_verdict,
        agreement_type=base_disposition.get("agreement_pattern"),
        base_level=base_disposition.get("base_level"),
        fragility_cap=elimination_cap,
        final_level=final_level,
        auditor_assessment=base_disposition.get("auditor_assessment"),
        fragile=True,
        fired_rules=base_disposition.get("fired_rules", []),
        signal_count=base_disposition.get("signal_count", 0),
        conditions=conditions,
        elimination_applied=True,
        elimination_action=f"killed_{majority_verdict}_to_{effective_verdict}",
    )


def _build_record(terminal_state, commitment_level, majority_verdict, agreement_type,
                  base_level, fragility_cap, final_level, auditor_assessment,
                  fragile, fired_rules, signal_count, conditions,
                  elimination_applied=False, elimination_action=None):
    """Build the disposition record dict."""
    record = {
        "terminal_state": terminal_state,
        "commitment_level": commitment_level,
        "majority_verdict": majority_verdict,
        "agreement_pattern": agreement_type,
        "base_level": base_level,
        "fragility_cap": fragility_cap,
        "final_level": final_level,
        "auditor_assessment": auditor_assessment,
        "fragile": fragile,
        "fired_rules": fired_rules,
        "signal_count": signal_count,
        "conditions": conditions,
        "elimination_applied": elimination_applied,
    }
    if elimination_action is not None:
        record["elimination_action"] = elimination_action
    return record


# ============================================================
# Gold Comparison (POST-HOC ONLY)
# ============================================================

def compare_to_gold(disposition, gold_label):
    """
    Post-hoc comparison against gold label.
    Never called during disposition computation.

    Args:
        disposition: disposition record dict
        gold_label: gold label string (SUPPORT, CONTRADICT, or NEI/None)

    Returns:
        dict with gold_label, predicted, gold_match, withheld
    """
    state_to_verdict = {
        "ASSERT_SUPPORT": "SUPPORT",
        "ASSERT_CONTRADICT": "CONTRADICT",
        "ASSERT_NEI": "NOT_ENOUGH_INFO",
        "WITHHOLD_ASSERTION": None,
    }
    predicted = state_to_verdict.get(disposition["terminal_state"])

    # Normalize gold label for comparison
    gold_normalized = gold_label
    if gold_label in ("NEI", None):
        gold_normalized = "NOT_ENOUGH_INFO"

    gold_match = (predicted == gold_normalized) if predicted is not None else False

    return {
        "gold_label": gold_label,
        "gold_normalized": gold_normalized,
        "predicted": predicted,
        "gold_match": gold_match,
        "withheld": predicted is None,
    }


# ============================================================
# CAM Metrics
# ============================================================

def compute_cam_metrics(dispositions_with_gold):
    """
    Compute the four key CAM metrics.

    Args:
        dispositions_with_gold: list of dicts, each with:
            - disposition: disposition record
            - gold_comparison: gold comparison record
            - fragility: fragility profile

    Returns:
        dict with: cca, abstention_rate, abstention_value, fragility_prediction, details
    """
    total = len(dispositions_with_gold)
    if total == 0:
        return {"cca": 0, "abstention_rate": 0, "abstention_value": None, "fragility_prediction": None}

    # Count assertions vs withholds
    assertions = [d for d in dispositions_with_gold if not d["gold_comparison"]["withheld"]]
    withholds = [d for d in dispositions_with_gold if d["gold_comparison"]["withheld"]]

    # CCA: Among asserted, how many match gold?
    correct_assertions = sum(1 for d in assertions if d["gold_comparison"]["gold_match"])
    total_assertions = len(assertions)
    cca = correct_assertions / total_assertions if total_assertions > 0 else 0

    # Abstention rate
    abstention_rate = len(withholds) / total

    # Abstention value: Among withheld claims, would the majority verdict have matched gold?
    abstention_value_details = []
    for d in withholds:
        majority = d["disposition"].get("majority_verdict")
        gold = d["gold_comparison"]["gold_normalized"]
        would_match = (majority == gold) if majority else False
        abstention_value_details.append({
            "claim_id": d.get("claim_id"),
            "majority_verdict": majority,
            "gold_label": gold,
            "would_have_matched": would_match,
        })
    # Abstention value = fraction of withheld claims that would have been WRONG
    withheld_would_be_wrong = sum(1 for av in abstention_value_details if not av["would_have_matched"])
    abstention_value = withheld_would_be_wrong / len(withholds) if withholds else None

    # Fragility prediction: Among fragile claims, what fraction had issues?
    fragile_claims = [d for d in dispositions_with_gold if d["fragility"].get("fragile")]
    fragile_with_issues = sum(
        1 for d in fragile_claims
        if not d["gold_comparison"]["gold_match"] or d["gold_comparison"]["withheld"]
    )
    fragility_prediction = fragile_with_issues / len(fragile_claims) if fragile_claims else None

    return {
        "cca": cca,
        "correct_assertions": correct_assertions,
        "total_assertions": total_assertions,
        "abstention_rate": abstention_rate,
        "abstention_count": len(withholds),
        "abstention_value": abstention_value,
        "abstention_value_details": abstention_value_details,
        "fragility_prediction": fragility_prediction,
        "fragile_count": len(fragile_claims),
        "fragile_with_issues": fragile_with_issues,
        "total_claims": total,
    }


# ============================================================
# Pipeline Summary (human-readable end-to-end trace)
# ============================================================

def format_pipeline_summary(claim_id, claim_text, gold_label, evaluations,
                            challenge_result, auditor_result, fragility_profile,
                            disposition, gold_comparison):
    """
    Generate a human-readable end-to-end trace for a single claim.
    Shows how signals accumulated through the pipeline to produce the final disposition.
    """
    lines = []
    lines.append("=" * 70)
    lines.append(f"  CLAIM {claim_id}: {claim_text[:80]}...")
    lines.append("=" * 70)
    lines.append("")

    # Stage 1: Evaluator Verdicts
    lines.append("  STAGE 1 -- EVALUATION:")
    for label in sorted(evaluations.keys()):
        ev = evaluations[label]
        v = ev.get("verdict", "ERROR")
        c = ev.get("confidence", "?")
        cs = ev.get("cited_sentences", [])
        lines.append(f"    Evaluator {label}: {v} (confidence={c}, cited={cs})")
    agreement = disposition.get("agreement_pattern", "?")
    majority = disposition.get("majority_verdict", "?")
    lines.append(f"    -> Agreement: {agreement}, Majority verdict: {majority}")
    lines.append("")

    # Stage 2: Challenge
    lines.append("  STAGE 2 -- EVIDENCE CHALLENGE:")
    ga_list = challenge_result.get("grounding_analysis", [])
    for ga in ga_list:
        ev = ga.get("evaluator", "?")
        gq = ga.get("grounding_quality", "?")
        lines.append(f"    Evaluator {ev}: grounding={gq}")
    flags = challenge_result.get("inference_flags", [])
    if flags:
        for flag in flags:
            sev = flag.get("severity", "?")
            if sev in ("moderate", "critical"):
                lines.append(f"    FLAG: {flag.get('evaluator', '?')} - {flag.get('inference_type', '?')} ({sev})")
    oq = challenge_result.get("overall_grounding_quality", "?")
    lines.append(f"    -> Overall grounding: {oq}")
    lines.append("")

    # Stage 3: Auditor
    lines.append("  STAGE 3 -- AUDITOR:")
    assessment = auditor_result.get("overall_assessment", "?")
    fa = auditor_result.get("fragile_agreement", {})
    fa_status = "FRAGILE" if fa.get("detected") else "robust"
    cea = auditor_result.get("cross_evaluator_analysis", {})
    overlap = cea.get("sentence_overlap", "?")
    alignment = cea.get("reasoning_alignment", "?")
    lines.append(f"    Assessment: {assessment}")
    lines.append(f"    Agreement: {fa_status}, overlap={overlap}, alignment={alignment}")
    violations = auditor_result.get("constraint_compliance", {}).get("violations", [])
    for v in violations:
        lines.append(f"    Violation: {v.get('evaluator', '?')} - {v.get('violation', '')[:60]} ({v.get('severity', '?')})")
    lines.append("")

    # Stage 4: Fragility
    lines.append("  STAGE 4 -- FRAGILITY:")
    fragile = fragility_profile.get("fragile", False)
    status = "FRAGILE" if fragile else "CLEAN"
    lines.append(f"    Status: {status}")
    if fragility_profile.get("fired_rules"):
        lines.append(f"    Rules fired: {', '.join(fragility_profile['fired_rules'])}")
    cap = fragility_profile.get("max_cap")
    if cap:
        lines.append(f"    Cap: {cap}")
    lines.append(f"    Signal count: {fragility_profile.get('signal_count', 0)}")
    lines.append("")

    # Stage 5: Disposition
    lines.append("  STAGE 5 -- DISPOSITION:")
    lines.append(f"    Base level: {disposition.get('base_level', '?')} (agreement={agreement}, auditor={assessment})")
    if cap:
        lines.append(f"    Fragility cap applied: {cap}")
    lines.append(f"    Final level: {disposition.get('final_level', '?')} -> {disposition.get('commitment_level', '?')}")
    lines.append(f"    Terminal state: {disposition.get('terminal_state', '?')}")
    if disposition.get("conditions"):
        for cond in disposition["conditions"]:
            lines.append(f"    Condition: {cond}")
    lines.append("")

    # Gold comparison (post-hoc)
    lines.append("  GOLD COMPARISON (post-hoc):")
    lines.append(f"    Gold label: {gold_label}")
    lines.append(f"    Predicted: {gold_comparison.get('predicted', '?')}")
    match = "MATCH" if gold_comparison.get("gold_match") else "MISMATCH"
    lines.append(f"    Result: {match}")
    lines.append("")

    return "\n".join(lines)
