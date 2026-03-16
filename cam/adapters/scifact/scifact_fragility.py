"""
SciFact Fragility Detection (Stage 4)

Aggregates fragility signals from ALL prior stages into a single
fragility profile per claim. No API calls — pure computation on
Stages 1-3 outputs.

Signal sources:
1. Rule library (cam/rules/scifact_rules.py) — coded rules that fire on structured data
2. Challenge inference flags — moderate/critical flags become fragility signals
3. Auditor flags — FLAG/FAIL assessment, fragile agreement, constraint violations

Cap logic: If multiple signals impose caps, take the most restrictive (lowest level).
L1 < L2 < L3 (L1 = Qualified, most restrictive; L3 = High, least restrictive).
"""

from cam.rules.scifact_rules import apply_scifact_rules


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
    Any moderate or critical inference flags become fragility signals.
    """
    signals = []
    flags = challenge_result.get("inference_flags", [])
    for flag in flags:
        severity = flag.get("severity", "minor")
        if severity in ("moderate", "critical"):
            signals.append({
                "source": "challenge",
                "signal_id": f"inference_flag:{flag.get('inference_type', 'unknown')}",
                "description": (
                    f"Evaluator {flag.get('evaluator', '?')}: "
                    f"{flag.get('inference_type', '?')} - "
                    f"{flag.get('description', '')[:120]}"
                ),
                "severity": severity,
                "effect": "cap_L2" if severity == "moderate" else "cap_L1",
            })
    return signals


def _collect_auditor_signals(auditor_result):
    """
    Collect fragility signals from Stage 3 auditor results.
    - FLAG or FAIL overall assessment
    - Fragile agreement detection
    - Constraint violations with moderate+ severity
    """
    signals = []

    # Overall assessment
    assessment = auditor_result.get("overall_assessment", "")
    if assessment == "FAIL":
        signals.append({
            "source": "auditor",
            "signal_id": "auditor_fail",
            "description": "Auditor assessment: FAIL - critical structural issues",
            "severity": "critical",
            "effect": "cap_L1",
        })
    elif assessment == "FLAG":
        signals.append({
            "source": "auditor",
            "signal_id": "auditor_flag",
            "description": "Auditor assessment: FLAG - concerns detected",
            "severity": "moderate",
            "effect": "mark_fragile",
        })

    # Fragile agreement (also picked up by RULE-SF-003, but we record the
    # auditor signal separately for completeness)
    fa = auditor_result.get("fragile_agreement", {})
    if fa.get("detected"):
        signals.append({
            "source": "auditor",
            "signal_id": "fragile_agreement",
            "description": f"Fragile agreement: {fa.get('details', '')[:120]}",
            "severity": "moderate",
            "effect": "cap_L2",
        })

    # Constraint violations with moderate+ severity
    cc = auditor_result.get("constraint_compliance", {})
    for v in cc.get("violations", []):
        severity = v.get("severity", "minor")
        if severity in ("moderate", "critical"):
            signals.append({
                "source": "auditor",
                "signal_id": f"constraint_violation:{v.get('evaluator', '?')}",
                "description": (
                    f"Evaluator {v.get('evaluator', '?')}: "
                    f"{v.get('violation', '')[:120]}"
                ),
                "severity": severity,
                "effect": "cap_L2" if severity == "moderate" else "cap_L1",
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
    return current_cap


def _summarize(fragile, signal_count, fired_rules, max_cap):
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

    return "FRAGILE. " + ". ".join(parts) + "."


def compute_fragility_profile(claim_data, evaluations, challenge_result, auditor_result):
    """
    Compute a complete fragility profile for a single claim.

    Collects fragility signals from ALL sources into a single profile.

    Args:
        claim_data: dict with claim_id, claim_text, gold_label, etc.
        evaluations: dict of evaluator label -> normalized response (Stage 1)
        challenge_result: normalized challenge response (Stage 2)
        auditor_result: normalized auditor response (Stage 3)

    Returns:
        dict with: fragile, signals, max_cap, fired_rules, signal_count, summary
    """
    # 1. Run rule library
    fired_rules = apply_scifact_rules(evaluations, challenge_result, auditor_result)
    rule_signals = _collect_rule_signals(fired_rules)

    # 2. Collect challenge signals (moderate+ inference flags)
    challenge_signals = _collect_challenge_signals(challenge_result)

    # 3. Collect auditor signals (FLAG/FAIL, fragile agreement, violations)
    auditor_signals = _collect_auditor_signals(auditor_result)

    # Combine all signals
    all_signals = rule_signals + challenge_signals + auditor_signals

    # Compute cap
    max_cap = _compute_max_cap(all_signals)

    # Determine fragility
    fragile = len(all_signals) > 0

    # Build fired rules list (just IDs)
    fired_rule_ids = [r["rule_id"] for r in fired_rules]

    # Summary
    summary = _summarize(fragile, len(all_signals), fired_rules, max_cap)

    return {
        "fragile": fragile,
        "signals": all_signals,
        "max_cap": max_cap,
        "fired_rules": fired_rule_ids,
        "signal_count": len(all_signals),
        "summary": summary,
    }
