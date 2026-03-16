"""
ContractNLI Fragility Detection (Stage 4)

Aggregates fragility signals from ALL prior stages into a single
fragility profile per (contract, hypothesis) pair. No API calls —
pure computation on Stages 1-3 outputs.

Signal sources:
1. Rule library (cam/rules/contractnli_rules.py) — coded rules that fire on structured data
2. Challenge findings — high/medium severity challenges become fragility signals
3. Auditor flags — escalate/flag recommendation, grounding issues, consistency issues

Cap logic: If multiple signals impose caps, take the most restrictive (lowest level).
L1 < L2 < L3 (L1 = Qualified, most restrictive; L3 = High, least restrictive).
"""

from cam.rules.contractnli_rules import apply_contractnli_rules


# Cap priority: L1 is most restrictive, None is no cap
_CAP_PRIORITY = {
    "L1": 1,
    "L2": 2,
    "L3": 3,
    None: 99,  # No cap = least restrictive
}


def _more_restrictive_cap(cap_a, cap_b):
    """Return the more restrictive of two caps."""
    pri_a = _CAP_PRIORITY.get(cap_a, 99)
    pri_b = _CAP_PRIORITY.get(cap_b, 99)
    if pri_a <= pri_b:
        return cap_a
    return cap_b


def _collect_challenge_signals(challenge_result):
    """
    Collect fragility signals from Stage 2 challenge results.
    High or medium severity challenges become fragility signals.
    """
    signals = []
    challenges = challenge_result.get("challenges", [])
    for ch in challenges:
        severity = ch.get("severity", "low")
        if severity in ("medium", "high"):
            affected = ch.get("affected_evaluators", [])
            signals.append({
                "source": "challenge",
                "signal_id": f"challenge:{ch.get('challenge_type', 'unknown')}",
                "description": (
                    f"[{severity.upper()}] {ch.get('challenge_type', '?')}: "
                    f"affects {', '.join(affected)} - "
                    f"{ch.get('description', '')[:120]}"
                ),
                "severity": severity,
                "effect": "cap_L2" if severity == "medium" else "cap_L1",
            })
    return signals


def _collect_auditor_signals(auditor_result):
    """
    Collect fragility signals from Stage 3 auditor results.
    - escalate or flag recommendation
    - weak/ungrounded grounding quality
    - consistency issues
    - span overlap = none (fragile agreement signal)
    """
    signals = []

    # Recommendation
    recommendation = auditor_result.get("recommendation", "")
    if recommendation == "escalate":
        signals.append({
            "source": "auditor",
            "signal_id": "auditor_escalate",
            "description": "Auditor recommendation: escalate - critical structural issues",
            "severity": "critical",
            "effect": "cap_L1",
        })
    elif recommendation == "flag":
        signals.append({
            "source": "auditor",
            "signal_id": "auditor_flag",
            "description": "Auditor recommendation: flag - concerns detected",
            "severity": "moderate",
            "effect": "mark_fragile",
        })

    # Grounding quality
    grounding = auditor_result.get("grounding_quality", "")
    if grounding == "ungrounded":
        signals.append({
            "source": "auditor",
            "signal_id": "ungrounded_reasoning",
            "description": "Auditor found evaluators reasoning from assumptions, not contract text",
            "severity": "critical",
            "effect": "cap_L1",
        })
    elif grounding == "weak":
        signals.append({
            "source": "auditor",
            "signal_id": "weak_grounding",
            "description": "Auditor found significant reasoning without span support",
            "severity": "moderate",
            "effect": "cap_L2",
        })

    # Consistency issues
    consistency_issues = auditor_result.get("consistency_issues", [])
    if consistency_issues:
        signals.append({
            "source": "auditor",
            "signal_id": "consistency_issues",
            "description": (
                f"{len(consistency_issues)} consistency issue(s): "
                f"{consistency_issues[0][:120]}"
            ),
            "severity": "moderate",
            "effect": "cap_L2",
        })

    # Span overlap = none (fragile agreement signal)
    overlap = auditor_result.get("span_overlap_assessment", "")
    if overlap == "none":
        signals.append({
            "source": "auditor",
            "signal_id": "fragile_agreement",
            "description": "Agreeing evaluators cite completely non-overlapping spans",
            "severity": "moderate",
            "effect": "cap_L2",
        })

    return signals


def _collect_rule_signals(fired_rules):
    """Convert fired rule library results into fragility signals."""
    signals = []
    for rule in fired_rules:
        signals.append({
            "source": "rule_library",
            "signal_id": rule["rule_id"],
            "description": f"{rule['rule_name']}: {rule['details'][:120]}",
            "severity": rule.get("severity", "moderate"),
            "effect": rule.get("effect", "mark_fragile"),
        })
    return signals


def _compute_max_cap(signals):
    """
    Compute the most restrictive cap from all signals.
    Returns None if no caps imposed.
    """
    current_cap = None
    for signal in signals:
        effect = signal.get("effect", "")
        if effect.startswith("cap_"):
            cap_level = effect.replace("cap_", "")
            current_cap = _more_restrictive_cap(current_cap, cap_level)
        elif effect == "downgrade_one":
            # downgrade_one acts as a soft cap at L2 for now
            # (disposition layer will interpret this as "drop one level")
            current_cap = _more_restrictive_cap(current_cap, "L2")
    return current_cap


def _compute_fragility_score(signals):
    """
    Compute a 0.0-1.0 fragility score from signals.

    Scoring:
    - Each signal adds weight based on severity
    - critical = 0.35, moderate = 0.20, low = 0.10
    - Score is capped at 1.0
    """
    if not signals:
        return 0.0

    severity_weights = {
        "critical": 0.35,
        "high": 0.30,
        "moderate": 0.20,
        "low": 0.10,
    }

    total = 0.0
    for signal in signals:
        severity = signal.get("severity", "moderate")
        total += severity_weights.get(severity, 0.15)

    return min(total, 1.0)


def _summarize(fragile, signal_count, fired_rules, max_cap, fragility_score):
    """Generate a one-line human-readable summary."""
    if not fragile:
        return "No fragility detected. Reasoning is structurally sound."

    parts = []
    if fired_rules:
        rule_names = [r["rule_name"] for r in fired_rules]
        parts.append(f"Rules fired: {', '.join(rule_names)}")
    if max_cap:
        parts.append(f"Cap: {max_cap}")
    parts.append(f"{signal_count} signal(s)")
    parts.append(f"score={fragility_score:.2f}")

    return "FRAGILE. " + ". ".join(parts) + "."


def compute_fragility_profile(evaluations, challenge_result, auditor_result):
    """
    Compute a complete fragility profile for a single (contract, hypothesis) pair.

    Collects fragility signals from ALL sources into a single profile.

    Args:
        evaluations: dict of evaluator label -> normalized response (Stage 1)
        challenge_result: normalized challenge response (Stage 2)
        auditor_result: normalized auditor response (Stage 3)

    Returns:
        dict with: fragile, fragility_score, signals, max_cap, fired_rules,
                   signal_count, summary
    """
    # 1. Run rule library
    fired_rules = apply_contractnli_rules(evaluations, challenge_result, auditor_result)
    rule_signals = _collect_rule_signals(fired_rules)

    # 2. Collect challenge signals (medium+ severity challenges)
    challenge_signals = _collect_challenge_signals(challenge_result)

    # 3. Collect auditor signals (escalate/flag, grounding, consistency, overlap)
    auditor_signals = _collect_auditor_signals(auditor_result)

    # Combine all signals
    all_signals = rule_signals + challenge_signals + auditor_signals

    # Compute cap
    max_cap = _compute_max_cap(all_signals)

    # Compute fragility score
    fragility_score = _compute_fragility_score(all_signals)

    # Determine fragility
    fragile = len(all_signals) > 0

    # Build fired rules list (just IDs)
    fired_rule_ids = [r["rule_id"] for r in fired_rules]

    # Summary
    summary = _summarize(fragile, len(all_signals), fired_rules, max_cap, fragility_score)

    return {
        "fragile": fragile,
        "fragility_score": fragility_score,
        "signals": all_signals,
        "max_cap": max_cap,
        "fired_rules": fired_rule_ids,
        "signal_count": len(all_signals),
        "summary": summary,
    }
