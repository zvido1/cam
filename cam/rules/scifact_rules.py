"""
CAM SciFact Rule Library

5 initial rules for scientific claim verification fragility detection.
Rules only downgrade -- they can mark fragile, cap commitment levels,
or flag concerns. They NEVER upgrade or force verdict selection.

Rule evaluation is performed AFTER Stages 1-3 but BEFORE disposition.

Each rule function receives:
- evaluations: dict of evaluator label -> normalized evaluator response (Stage 1)
- challenge_result: normalized challenge response (Stage 2)
- auditor_result: normalized auditor response (Stage 3)

Each returns: {"fired": bool, "details": str, "effect": str} or None if not fired.
"""


# ============================================================
# Rule Definitions (metadata)
# ============================================================

RULE_SF_001 = {
    "id": "RULE-SF-001",
    "name": "External Knowledge Usage",
    "description": "An evaluator used knowledge not present in the abstract",
    "trigger": "Any inference_flag with type 'external_knowledge' and severity 'moderate' or 'critical'",
    "effect": "Mark fragile. Cap at L2 (Conditional).",
}

RULE_SF_002 = {
    "id": "RULE-SF-002",
    "name": "Scope Mismatch",
    "description": "Evaluator scope assessment shows mismatch between claim and evidence",
    "trigger": "Any evaluator has scope_match = 'mismatch'",
    "effect": "Mark fragile. Cap at L1 (Qualified).",
}

RULE_SF_003 = {
    "id": "RULE-SF-003",
    "name": "Fragile Agreement",
    "description": "Evaluators agree on verdict but auditor detected fragile agreement",
    "trigger": "Auditor fragile_agreement.detected = true",
    "effect": "Mark fragile. Cap at L2 (Conditional).",
}

RULE_SF_004 = {
    "id": "RULE-SF-004",
    "name": "Zero Sentence Overlap",
    "description": "Evaluators who agree on verdict cite completely non-overlapping sentences",
    "trigger": "Auditor cross_evaluator_analysis.sentence_overlap = 'none'",
    "effect": "Mark fragile. Cap at L2 (Conditional).",
}

RULE_SF_005 = {
    "id": "RULE-SF-005",
    "name": "Weak Evaluator Grounding",
    "description": "At least one evaluator has weak or ungrounded evidence per challenge",
    "trigger": "Any evaluator grounding_quality = 'weak' or 'ungrounded' in challenge results",
    "effect": "Mark fragile.",
}

# All rules in a list for iteration
ALL_RULES = [RULE_SF_001, RULE_SF_002, RULE_SF_003, RULE_SF_004, RULE_SF_005]


# ============================================================
# Rule Check Functions
# ============================================================

def check_rule_sf_001(evaluations, challenge_result, auditor_result):
    """
    RULE-SF-001: External Knowledge Usage

    Fires when any inference_flag has type='external_knowledge'
    and severity='moderate' or 'critical'.
    """
    flags = challenge_result.get("inference_flags", [])
    triggered_flags = []
    for flag in flags:
        if flag.get("inference_type") == "external_knowledge":
            severity = flag.get("severity", "minor")
            if severity in ("moderate", "critical"):
                triggered_flags.append(flag)

    if not triggered_flags:
        return None

    evaluators = [f.get("evaluator", "?") for f in triggered_flags]
    severities = [f.get("severity", "?") for f in triggered_flags]
    details = (
        f"External knowledge detected in evaluator(s) {', '.join(evaluators)} "
        f"with severity {', '.join(severities)}"
    )

    return {
        "fired": True,
        "rule_id": RULE_SF_001["id"],
        "rule_name": RULE_SF_001["name"],
        "details": details,
        "effect": "cap_L2",
        "severity": max(severities, key=lambda s: {"minor": 0, "moderate": 1, "critical": 2}.get(s, 0)),
    }


def check_rule_sf_002(evaluations, challenge_result, auditor_result):
    """
    RULE-SF-002: Scope Mismatch

    Fires when any evaluator has scope_match = 'mismatch'.
    """
    mismatched = []
    for label, ev in evaluations.items():
        if "error" in ev and "verdict" not in ev:
            continue
        scope = ev.get("scope_assessment", {})
        if scope.get("scope_match") == "mismatch":
            mismatched.append(label)

    if not mismatched:
        return None

    details = f"Scope mismatch detected in evaluator(s) {', '.join(mismatched)}"

    return {
        "fired": True,
        "rule_id": RULE_SF_002["id"],
        "rule_name": RULE_SF_002["name"],
        "details": details,
        "effect": "cap_L1",
        "severity": "moderate",
    }


def check_rule_sf_003(evaluations, challenge_result, auditor_result):
    """
    RULE-SF-003: Fragile Agreement

    Fires when auditor detected fragile agreement.
    """
    fa = auditor_result.get("fragile_agreement", {})
    if not fa.get("detected"):
        return None

    details_text = fa.get("details", "No details provided")

    return {
        "fired": True,
        "rule_id": RULE_SF_003["id"],
        "rule_name": RULE_SF_003["name"],
        "details": f"Fragile agreement detected: {details_text}",
        "effect": "cap_L2",
        "severity": "moderate",
    }


def check_rule_sf_004(evaluations, challenge_result, auditor_result):
    """
    RULE-SF-004: Zero Sentence Overlap

    Fires when auditor reports sentence_overlap = 'none'.
    """
    cea = auditor_result.get("cross_evaluator_analysis", {})
    if cea.get("sentence_overlap") != "none":
        return None

    return {
        "fired": True,
        "rule_id": RULE_SF_004["id"],
        "rule_name": RULE_SF_004["name"],
        "details": "Evaluators cite completely non-overlapping sentences despite agreeing on verdict",
        "effect": "cap_L2",
        "severity": "moderate",
    }


def check_rule_sf_005(evaluations, challenge_result, auditor_result):
    """
    RULE-SF-005: Weak Evaluator Grounding

    Fires when any evaluator has grounding_quality = 'weak' or 'ungrounded'
    in the challenge results.
    """
    ga_list = challenge_result.get("grounding_analysis", [])
    weak_evals = []
    for ga in ga_list:
        gq = ga.get("grounding_quality", "")
        if gq in ("weak", "ungrounded"):
            weak_evals.append(ga.get("evaluator", "?"))

    if not weak_evals:
        return None

    return {
        "fired": True,
        "rule_id": RULE_SF_005["id"],
        "rule_name": RULE_SF_005["name"],
        "details": f"Weak/ungrounded evaluator grounding in evaluator(s) {', '.join(weak_evals)}",
        "effect": "mark_fragile",
        "severity": "moderate",
    }


# ============================================================
# Aggregate Rule Application
# ============================================================

# Map from check functions to rule metadata
_RULE_CHECKS = [
    check_rule_sf_001,
    check_rule_sf_002,
    check_rule_sf_003,
    check_rule_sf_004,
    check_rule_sf_005,
]


def apply_scifact_rules(evaluations, challenge_result, auditor_result):
    """
    Run all SciFact rules and return list of fired rules with details.

    Args:
        evaluations: dict of evaluator label -> normalized response (Stage 1)
        challenge_result: normalized challenge response (Stage 2)
        auditor_result: normalized auditor response (Stage 3)

    Returns:
        list of fired rule dicts (each with: fired, rule_id, rule_name, details, effect, severity)
    """
    fired = []
    for check_fn in _RULE_CHECKS:
        result = check_fn(evaluations, challenge_result, auditor_result)
        if result is not None and result.get("fired"):
            fired.append(result)
    return fired
