"""
ContractNLI Disposition Layer (Stage 6)

Combines all prior stage outputs into terminal state and commitment level.
This is CAM's final word on each (contract, hypothesis) pair.

Terminal states: ASSERT_ENTAILMENT, ASSERT_CONTRADICTION, ASSERT_NOT_MENTIONED, WITHHOLD_ASSERTION
Commitment levels: L0 (Full Assert) through L4 (Withhold)

No API calls -- pure computation on Stages 1-5 outputs.
Gold comparison is POST-HOC only -- never influences disposition.
"""

from collections import Counter


# ============================================================
# Terminal States
# ============================================================

TERMINAL_STATES = {
    "ASSERT_ENTAILMENT":    "System asserts the hypothesis is entailed by the contract",
    "ASSERT_CONTRADICTION": "System asserts the hypothesis is contradicted by the contract",
    "ASSERT_NOT_MENTIONED": "System asserts the contract does not address the hypothesis",
    "WITHHOLD_ASSERTION":   "System declines to assert any verdict",
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

COMMITMENT_LABELS = {
    "L0": "Full Assert",
    "L1": "Qualified Assert",
    "L2": "Conditional Assert",
    "L3": "Low Confidence",
    "L4": "Withhold",
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

# Conviction weights for confidence levels
_CONVICTION_WEIGHTS = {
    "high": 1.0,
    "medium": 0.6,
    "low": 0.3,
}


def _more_restrictive_level(level_a, level_b):
    """Return the more restrictive (higher numbered) of two levels."""
    ord_a = _LEVEL_ORDER.get(level_a, 0)
    ord_b = _LEVEL_ORDER.get(level_b, 0)
    if ord_a >= ord_b:
        return level_a
    return level_b


# ============================================================
# Conviction Score
# ============================================================

def _compute_conviction_score(evaluations, majority_verdict):
    """
    Compute conviction score (0.0-1.0) based on evaluator confidence weighted
    by agreement with the majority verdict.

    Evaluators who agree with the majority get their full conviction weight.
    Evaluators who disagree contribute negative weight (clamped to 0).
    """
    if majority_verdict is None:
        return 0.0

    total_weight = 0.0
    for label, ev in evaluations.items():
        if "error" in ev and "verdict" not in ev:
            continue
        verdict = ev.get("verdict")
        confidence = ev.get("confidence", "medium")
        weight = _CONVICTION_WEIGHTS.get(confidence, 0.5)

        if verdict == majority_verdict:
            total_weight += weight
        else:
            total_weight -= weight * 0.5  # Disagreement penalizes

    # Normalize to 0-1 range (max possible: 3 * 1.0 = 3.0)
    max_possible = len(evaluations) * 1.0
    score = max(0.0, total_weight) / max_possible if max_possible > 0 else 0.0
    return min(1.0, score)


# ============================================================
# Disposition Logic
# ============================================================

def compute_disposition(evaluations, challenge_result, auditor_result,
                        fragility_profile, elimination_result):
    """
    Compute terminal state and commitment level for a single
    (contract, hypothesis) pair.

    Steps:
    A. Determine majority verdict
    B. Check for WITHHOLD triggers
    C. Determine base commitment level
    D. Apply legal-specific downgrade triggers
    E. Apply fragility cap
    F. Apply elimination overrides
    G. Compute conviction score
    H. Determine terminal state
    I. Build disposition record

    Args:
        evaluations: dict of evaluator label -> normalized response (Stage 1)
        challenge_result: normalized challenge response (Stage 2)
        auditor_result: normalized auditor response (Stage 3)
        fragility_profile: fragility profile dict (Stage 4)
        elimination_result: normalized elimination response (Stage 5)

    Returns:
        Disposition record dict.
    """
    downgrade_reasons = []
    rules_applied = fragility_profile.get("fired_rules", [])

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
        agreement_type = "1-1-1"

    # ---- Step B: Check for WITHHOLD triggers ----
    auditor_recommendation = auditor_result.get("recommendation", "")
    auditor_validity = auditor_result.get("structural_validity", "")
    fragility_cap = fragility_profile.get("max_cap")
    fragility_score = fragility_profile.get("fragility_score", 0.0)

    withhold = False
    withhold_reason = None

    # Trigger 1: No majority verdict (full 3-way split)
    if majority_verdict is None:
        withhold = True
        withhold_reason = "No majority verdict (full split)"

    # Trigger 2: Auditor says invalid
    if auditor_validity == "invalid":
        withhold = True
        withhold_reason = "Auditor structural validity: invalid"

    # Trigger 3: All 3 verdicts survive elimination equally
    if elimination_result and "error" not in elimination_result:
        surviving = elimination_result.get("surviving_verdicts", [])
        if len(surviving) == 3:
            # Check if all are roughly equal confidence
            assessments = elimination_result.get("verdict_assessments", [])
            confidences = [va.get("confidence_if_selected", "medium") for va in assessments
                           if isinstance(va, dict) and va.get("survives")]
            all_same = len(set(confidences)) <= 1
            if all_same:
                withhold = True
                withhold_reason = "All 3 verdicts survive elimination equally -- genuine ambiguity"

    # Trigger 4: Fragility cap L1 AND auditor escalate (double jeopardy)
    if fragility_cap == "L1" and auditor_recommendation == "escalate":
        withhold = True
        withhold_reason = "Double jeopardy: fragility cap L1 + auditor escalate"

    if withhold:
        downgrade_reasons.append(withhold_reason)
        conviction = _compute_conviction_score(evaluations, majority_verdict)
        return _build_record(
            terminal_state="WITHHOLD_ASSERTION",
            commitment_level="L4",
            selected_verdict=None,
            majority_verdict=majority_verdict,
            agreement_type=agreement_type,
            conviction_score=conviction,
            downgrade_reasons=downgrade_reasons,
            rules_applied=rules_applied,
            base_level="L4",
            fragility_cap=fragility_cap,
            elimination_applied=False,
        )

    # ---- Step C: Determine base commitment level ----
    # Based on agreement pattern + auditor recommendation
    # Calibration (Step 025): incomplete auditor data defaults to L1, not L2.
    # Only L2 when auditor explicitly flags structural problems (escalate).
    if agreement_type == "3-0" and auditor_recommendation == "proceed":
        base_level = "L0"
    elif agreement_type == "3-0" and auditor_recommendation == "flag":
        base_level = "L1"
    elif agreement_type == "3-0" and auditor_recommendation == "escalate":
        base_level = "L2"
    elif agreement_type == "2-1" and auditor_recommendation == "proceed":
        base_level = "L1"
    elif agreement_type == "2-1" and auditor_recommendation == "flag":
        base_level = "L2"
    elif agreement_type == "2-1" and auditor_recommendation == "escalate":
        base_level = "L3"
    elif agreement_type in ("3-0", "2-1") and auditor_recommendation in ("", None):
        # Incomplete auditor data (missing recommendation) -> default L1, not L2
        base_level = "L1"
        downgrade_reasons.append("Auditor recommendation missing -- defaulting to L1 (not L2)")
    else:
        base_level = "L2"

    final_level = base_level

    # ---- Step D: Apply legal-specific downgrade triggers ----

    # D1: RULE-CN-001 or CN-002 at HIGH severity -> cap at L2
    #     RULE-CN-001 or CN-002 at MEDIUM severity -> downgrade by 1 level (not hard-cap)
    # Calibration (Step 025): medium severity no longer hard-caps at L2.
    for rule_id in rules_applied:
        if rule_id in ("RULE-CN-001", "RULE-CN-002"):
            for sig in fragility_profile.get("signals", []):
                if sig.get("signal_id") == rule_id:
                    sev = sig.get("severity", "")
                    if sev in ("critical", "high"):
                        final_level = _more_restrictive_level(final_level, "L2")
                        downgrade_reasons.append(
                            f"{rule_id} fired at HIGH severity -- capped at L2"
                        )
                    elif sev == "medium":
                        # Downgrade by 1 level instead of hard-capping
                        current_ord = _LEVEL_ORDER.get(final_level, 0)
                        candidates = [k for k, v in _LEVEL_ORDER.items() if v == current_ord + 1]
                        if candidates:
                            final_level = candidates[0]
                            downgrade_reasons.append(
                                f"{rule_id} fired at MEDIUM severity -- downgraded one level"
                            )
                    break

    # D2: RULE-CN-003 fired + evaluators disagree -> downgrade one level
    if "RULE-CN-003" in rules_applied and agreement_type == "2-1":
        current_ord = _LEVEL_ORDER.get(final_level, 0)
        new_level = [k for k, v in _LEVEL_ORDER.items() if v == current_ord + 1]
        if new_level:
            final_level = new_level[0]
            downgrade_reasons.append(
                "RULE-CN-003 (definitional dependency) + evaluator disagreement -- downgraded one level"
            )

    # D3: All evaluators agree but cite completely non-overlapping spans -> cap at L2
    overlap = auditor_result.get("span_overlap_assessment", "")
    if agreement_type == "3-0" and overlap == "none":
        final_level = _more_restrictive_level(final_level, "L2")
        downgrade_reasons.append(
            "Unanimous agreement but zero span overlap -- capped at L2"
        )

    # D4: 2/3 evaluators vote NOT_MENTIONED but one cites specific evidence -> cap at L3
    if majority_verdict == "NOT_MENTIONED" and agreement_type == "2-1":
        # Find the dissenter
        for label, ev in evaluations.items():
            if "error" in ev and "verdict" not in ev:
                continue
            if ev.get("verdict") != "NOT_MENTIONED":
                cited = ev.get("cited_spans", [])
                if len(cited) >= 2:  # Dissenter has substantive evidence
                    final_level = _more_restrictive_level(final_level, "L3")
                    downgrade_reasons.append(
                        f"Majority NOT_MENTIONED but Evaluator {label} cites {len(cited)} spans "
                        f"for {ev.get('verdict', '?')} -- escalated to L3"
                    )
                    break

    # ---- Step E: Apply fragility cap ----
    if fragility_cap is not None:
        new_level = _more_restrictive_level(final_level, fragility_cap)
        if new_level != final_level:
            downgrade_reasons.append(
                f"Fragility cap {fragility_cap} applied (from {final_level} to {new_level})"
            )
            final_level = new_level

    # ---- Step F: Apply elimination overrides ----
    elimination_applied = False
    effective_verdict = majority_verdict
    guard_overrode = False

    if elimination_result and "error" not in elimination_result:
        surviving = elimination_result.get("surviving_verdicts", [])
        eliminated = elimination_result.get("eliminated_verdicts", [])
        recommended = elimination_result.get("recommended_verdict")

        elimination_applied = True

        # GUARD: Protect unanimous evaluator consensus from elimination override
        # If all 3 evaluators agreed AND elimination killed their verdict,
        # check if the kill has a valid category from the closed taxonomy.
        # If not, defer to evaluators.
        if agreement_type == "3-0" and majority_verdict in eliminated:
            valid_kill = False
            VALID_KILL_CATEGORIES = {
                "direct_textual_contradiction",
                "definitional_exclusion",
                "logical_impossibility",
                "complete_scope_absence",
            }
            assessments = elimination_result.get("verdict_assessments", [])
            for va in assessments:
                if isinstance(va, dict) and va.get("verdict") == majority_verdict:
                    kill_cat = va.get("kill_category")
                    if kill_cat in VALID_KILL_CATEGORIES:
                        # Additional check: does the critical_weakness contain a verbatim quote?
                        weakness = va.get("critical_weakness", "")
                        has_quote = '"' in weakness or "'" in weakness  # quoted contract text
                        if has_quote:
                            valid_kill = True
                        else:
                            valid_kill = False  # valid category but no quote = not a real kill
                    break

            if not valid_kill:
                # Override elimination — defer to unanimous evaluators
                downgrade_reasons.append(
                    f"Elimination guard: eliminated unanimous verdict {majority_verdict} "
                    f"but no valid kill category — deferring to evaluator consensus"
                )
                effective_verdict = majority_verdict
                final_level = _more_restrictive_level(final_level, "L2")
                guard_overrode = True
            else:
                # Valid kill of unanimous verdict — allow but cap heavily
                downgrade_reasons.append(
                    f"Elimination: unanimous verdict {majority_verdict} killed with "
                    f"valid category — proceeding with override but capping at L3"
                )
                final_level = _more_restrictive_level(final_level, "L3")

        # Check if majority verdict was killed (only if guard didn't fire)
        if majority_verdict in eliminated and not guard_overrode:
            downgrade_reasons.append(
                f"Elimination: majority verdict {majority_verdict} was killed"
            )

            if len(surviving) == 1:
                effective_verdict = surviving[0]
                downgrade_reasons.append(
                    f"Elimination: single survivor -> {effective_verdict}"
                )
                # Cap at L2 minimum when elimination overrides majority
                final_level = _more_restrictive_level(final_level, "L2")
            elif len(surviving) > 1 and recommended:
                # Multiple survivors — prefer one matching remaining evaluator votes
                survivor_votes = Counter()
                for label, ev in evaluations.items():
                    v = ev.get("verdict")
                    if v and v in surviving:
                        survivor_votes[v] += 1

                if survivor_votes:
                    effective_verdict = survivor_votes.most_common(1)[0][0]
                else:
                    effective_verdict = recommended
                downgrade_reasons.append(
                    f"Elimination: {len(surviving)} survivors, selected {effective_verdict}"
                )
                # Cap at L3 when multiple survive and majority killed
                final_level = _more_restrictive_level(final_level, "L3")
            elif recommended:
                effective_verdict = recommended
                final_level = _more_restrictive_level(final_level, "L3")
            else:
                # All killed (shouldn't happen but handle it)
                effective_verdict = None
                final_level = "L4"
                downgrade_reasons.append("Elimination: all verdicts killed")
        else:
            # Majority survived — reinforced
            downgrade_reasons.append(
                f"Elimination: majority verdict {majority_verdict} survived stress test"
            )

            # Check if only 1 verdict survived — narrows to single defensible option
            if len(surviving) == 1:
                # Might boost confidence but never upgrade beyond base
                pass

            # If multiple survive with low confidence recommended, note it
            if len(surviving) >= 2:
                # Multiple verdicts surviving is mildly concerning
                assessments = elimination_result.get("verdict_assessments", [])
                for va in assessments:
                    if isinstance(va, dict) and va.get("verdict") == majority_verdict:
                        elim_confidence = va.get("confidence_if_selected", "medium")
                        if elim_confidence == "low":
                            final_level = _more_restrictive_level(final_level, "L2")
                            downgrade_reasons.append(
                                "Elimination: majority survives but with low confidence"
                            )
                        break

    # ---- Step G: Compute conviction score ----
    conviction = _compute_conviction_score(evaluations, effective_verdict)

    # Low conviction can trigger a final downgrade
    if conviction < 0.3 and _LEVEL_ORDER.get(final_level, 0) < 3:
        final_level = _more_restrictive_level(final_level, "L3")
        downgrade_reasons.append(
            f"Low conviction score ({conviction:.2f}) -- capped at L3"
        )

    # ---- Step H: Determine terminal state ----
    if final_level == "L4" or effective_verdict is None:
        terminal_state = "WITHHOLD_ASSERTION"
        selected_verdict = None
    else:
        verdict_to_state = {
            "ENTAILMENT": "ASSERT_ENTAILMENT",
            "CONTRADICTION": "ASSERT_CONTRADICTION",
            "NOT_MENTIONED": "ASSERT_NOT_MENTIONED",
        }
        terminal_state = verdict_to_state.get(effective_verdict, "WITHHOLD_ASSERTION")
        selected_verdict = effective_verdict

    # ---- Step I: Build disposition record ----
    return _build_record(
        terminal_state=terminal_state,
        commitment_level=final_level,
        selected_verdict=selected_verdict,
        majority_verdict=majority_verdict,
        agreement_type=agreement_type,
        conviction_score=conviction,
        downgrade_reasons=downgrade_reasons,
        rules_applied=rules_applied,
        base_level=base_level,
        fragility_cap=fragility_cap,
        elimination_applied=elimination_applied,
    )


def _build_record(terminal_state, commitment_level, selected_verdict,
                   majority_verdict, agreement_type, conviction_score,
                   downgrade_reasons, rules_applied, base_level,
                   fragility_cap, elimination_applied):
    """Build the disposition record dict."""
    return {
        "terminal_state": terminal_state,
        "commitment_level": _LEVEL_NAMES.get(commitment_level, commitment_level),
        "commitment_label": COMMITMENT_LABELS.get(commitment_level, commitment_level),
        "selected_verdict": selected_verdict,
        "conviction_score": round(conviction_score, 3),
        "downgrade_reasons": downgrade_reasons,
        "rules_applied": rules_applied,
        # Internal fields for tracing
        "majority_verdict": majority_verdict,
        "agreement_pattern": agreement_type,
        "base_level": base_level,
        "final_level": commitment_level,
        "fragility_cap": fragility_cap,
        "elimination_applied": elimination_applied,
    }


# ============================================================
# Gold Comparison (POST-HOC ONLY)
# ============================================================

def compare_to_gold(disposition, gold_label):
    """
    Post-hoc comparison against gold label.
    Never called during disposition computation.

    Args:
        disposition: disposition record dict
        gold_label: gold label string (ENTAILMENT, CONTRADICTION, NOT_MENTIONED)

    Returns:
        dict with gold_label, predicted, gold_match, withheld
    """
    predicted = disposition.get("selected_verdict")

    gold_match = (predicted == gold_label) if predicted is not None else False

    return {
        "gold_label": gold_label,
        "predicted": predicted,
        "gold_match": gold_match,
        "withheld": predicted is None,
    }


# ============================================================
# Pipeline Summary (human-readable end-to-end trace)
# ============================================================

def format_pipeline_summary(item_id, hypothesis_text, gold_label, evaluations,
                            challenge_result, auditor_result, fragility_profile,
                            elimination_result, disposition, gold_comparison):
    """
    Generate a human-readable end-to-end trace for a single item.
    Shows how signals accumulated through the pipeline to produce the final disposition.
    """
    lines = []
    lines.append("=" * 70)
    safe_hyp = hypothesis_text[:80].encode("ascii", errors="replace").decode("ascii")
    lines.append(f"  ITEM {item_id}")
    lines.append(f"  Hypothesis: {safe_hyp}...")
    lines.append("=" * 70)
    lines.append("")

    # Stage 1: Evaluator Verdicts
    lines.append("  STAGE 1 -- EVALUATION:")
    for label in sorted(evaluations.keys()):
        ev = evaluations[label]
        v = ev.get("verdict", "ERROR")
        c = ev.get("confidence", "?")
        cs = ev.get("cited_spans", [])
        lines.append(f"    Evaluator {label}: {v} (confidence={c}, cited_spans={cs})")
    agreement = disposition.get("agreement_pattern", "?")
    majority = disposition.get("majority_verdict", "?")
    lines.append(f"    -> Agreement: {agreement}, Majority verdict: {majority}")
    lines.append("")

    # Stage 2: Challenge
    lines.append("  STAGE 2 -- EVIDENCE CHALLENGE:")
    challenges = challenge_result.get("challenges", [])
    if challenges:
        for ch in challenges:
            sev = ch.get("severity", "?")
            ct = ch.get("challenge_type", "?")
            affected = ch.get("affected_evaluators", [])
            lines.append(f"    [{sev.upper()}] {ct}: affects {', '.join(affected)}")
    else:
        lines.append("    No challenges found")
    overall = challenge_result.get("overall_grounding_assessment", "?")
    lines.append(f"    -> Overall grounding: {overall}")
    lines.append("")

    # Stage 3: Auditor
    lines.append("  STAGE 3 -- AUDITOR:")
    validity = auditor_result.get("structural_validity", "?")
    grounding = auditor_result.get("grounding_quality", "?")
    recommendation = auditor_result.get("recommendation", "?")
    overlap = auditor_result.get("span_overlap_assessment", "?")
    lines.append(f"    Validity: {validity}, Grounding: {grounding}")
    lines.append(f"    Span overlap: {overlap}, Recommendation: {recommendation}")
    issues = auditor_result.get("consistency_issues", [])
    if issues:
        for iss in issues:
            safe_iss = str(iss)[:80].encode("ascii", errors="replace").decode("ascii")
            lines.append(f"    Issue: {safe_iss}")
    lines.append("")

    # Stage 4: Fragility
    lines.append("  STAGE 4 -- FRAGILITY:")
    fragile = fragility_profile.get("fragile", False)
    f_score = fragility_profile.get("fragility_score", 0.0)
    status = f"FRAGILE (score={f_score:.2f})" if fragile else "CLEAN"
    lines.append(f"    Status: {status}")
    if fragility_profile.get("fired_rules"):
        lines.append(f"    Rules fired: {', '.join(fragility_profile['fired_rules'])}")
    cap = fragility_profile.get("max_cap")
    if cap:
        lines.append(f"    Cap: {cap}")
    lines.append(f"    Signal count: {fragility_profile.get('signal_count', 0)}")
    lines.append("")

    # Stage 5: Verdict Elimination
    lines.append("  STAGE 5 -- VERDICT ELIMINATION:")
    if elimination_result and "error" not in elimination_result:
        surviving = elimination_result.get("surviving_verdicts", [])
        eliminated = elimination_result.get("eliminated_verdicts", [])
        recommended = elimination_result.get("recommended_verdict", "?")
        lines.append(f"    Surviving: {surviving}")
        lines.append(f"    Eliminated: {eliminated}")
        lines.append(f"    Recommended: {recommended}")
        for va in elimination_result.get("verdict_assessments", []):
            if isinstance(va, dict):
                v = va.get("verdict", "?")
                surv = "SURVIVES" if va.get("survives") else "KILLED"
                conf = va.get("confidence_if_selected", "?")
                lines.append(f"    {v}: {surv} (confidence={conf})")
    else:
        lines.append("    [Elimination not available]")
    lines.append("")

    # Stage 6: Disposition
    lines.append("  STAGE 6 -- DISPOSITION:")
    lines.append(f"    Base level: {disposition.get('base_level', '?')}")
    lines.append(f"    Final level: {disposition.get('final_level', '?')} -> "
                 f"{disposition.get('commitment_level', '?')} "
                 f"({disposition.get('commitment_label', '?')})")
    lines.append(f"    Terminal state: {disposition.get('terminal_state', '?')}")
    lines.append(f"    Selected verdict: {disposition.get('selected_verdict', 'NONE')}")
    lines.append(f"    Conviction score: {disposition.get('conviction_score', 0):.3f}")
    if disposition.get("downgrade_reasons"):
        for reason in disposition["downgrade_reasons"]:
            safe_reason = str(reason)[:100].encode("ascii", errors="replace").decode("ascii")
            lines.append(f"    Downgrade: {safe_reason}")
    lines.append("")

    # Gold comparison (post-hoc)
    lines.append("  GOLD COMPARISON (post-hoc):")
    lines.append(f"    Gold label: {gold_label}")
    lines.append(f"    Predicted: {gold_comparison.get('predicted', '?')}")
    match = "MATCH" if gold_comparison.get("gold_match") else "MISMATCH"
    if gold_comparison.get("withheld"):
        match = "WITHHELD"
    lines.append(f"    Result: {match}")
    lines.append("")

    return "\n".join(lines)
