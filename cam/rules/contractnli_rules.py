"""
CAM ContractNLI Rule Library

6 rules for legal contract entailment fragility detection.
Rules only downgrade -- they can mark fragile, cap commitment levels,
or flag concerns. They NEVER upgrade or force verdict selection.

Rule evaluation is performed AFTER Stages 1-3 but BEFORE disposition.

Each rule function receives:
- evaluations: dict of evaluator label -> normalized evaluator response (Stage 1)
- challenge_result: normalized challenge response (Stage 2)
- auditor_result: normalized auditor response (Stage 3)

Each returns: dict with {fired, rule_id, rule_name, details, effect, severity} or None if not fired.
"""

import re


# ============================================================
# Rule Definitions (metadata)
# ============================================================

RULE_CN_001 = {
    "id": "RULE-CN-001",
    "name": "Negation by Exception (Local)",
    "description": "Exception keyword found within or near evaluator's cited spans",
    "trigger": "Exception keyword (except, notwithstanding, provided however, subject to, unless, excluding, other than) found in evaluator's cited spans or challenge flagged negation_resolution",
    "effect": "Mark fragile. Cap at L2 (Conditional).",
}

RULE_CN_002 = {
    "id": "RULE-CN-002",
    "name": "Negation by Exception (Non-local)",
    "description": "General rule in one section + exception in distant section; evaluator only cited one",
    "trigger": "Challenge flagged cross_reference with negation/exception component, or challenge flagged negation_resolution with missing_spans distant from cited spans",
    "effect": "Mark fragile. Cap at L2 (Conditional).",
}

RULE_CN_003 = {
    "id": "RULE-CN-003",
    "name": "Definitional Dependency",
    "description": "Evaluator uses a defined term but didn't cite the definition section",
    "trigger": "Challenge flagged definition_resolution, or evaluator has empty definitions_traced but reasoning references defined terms",
    "effect": "Mark fragile. Downgrade one commitment level.",
}

RULE_CN_004 = {
    "id": "RULE-CN-004",
    "name": "Quantifier Mismatch",
    "description": "Hypothesis quantifier mismatches contract quantifier in cited spans",
    "trigger": "Evaluator reasoning contains quantifier words (all, any, every, some, certain) and evaluators disagree on verdict",
    "effect": "Flag for attention. Downgrade if evaluators disagree.",
}

RULE_CN_005 = {
    "id": "RULE-CN-005",
    "name": "Modal Verb Sensitivity",
    "description": "Modal verbs (may/shall/must/will) in cited spans interpreted differently by evaluators",
    "trigger": "Evaluator reasoning references modal verbs and evaluators give different verdicts or different confidence levels",
    "effect": "Flag. Downgrade if disagreement.",
}

RULE_CN_006 = {
    "id": "RULE-CN-006",
    "name": "Temporal Scope Ambiguity",
    "description": "Temporal qualifiers (survival, expiration, termination) near cited spans",
    "trigger": "Evaluator reasoning or cited evidence mentions temporal terms (survive, survival, expiration, termination, term, duration, renewal) and evaluators disagree or confidence is mixed",
    "effect": "Flag for survival-related hypotheses.",
}

ALL_RULES = [RULE_CN_001, RULE_CN_002, RULE_CN_003, RULE_CN_004, RULE_CN_005, RULE_CN_006]


# ============================================================
# Helper: exception keywords
# ============================================================

EXCEPTION_KEYWORDS = [
    "except", "notwithstanding", "provided however", "subject to",
    "unless", "excluding", "other than", "provided that",
    "save for", "apart from",
]

EXCEPTION_PATTERN = re.compile(
    r'\b(' + '|'.join(re.escape(kw) for kw in EXCEPTION_KEYWORDS) + r')\b',
    re.IGNORECASE,
)

QUANTIFIER_PATTERN = re.compile(
    r'\b(all|any|every|each|some|certain|no|none|any and all)\b',
    re.IGNORECASE,
)

MODAL_PATTERN = re.compile(
    r'\b(may|shall|must|will|should|can|could|would)\b',
    re.IGNORECASE,
)

TEMPORAL_PATTERN = re.compile(
    r'\b(surviv(?:e|al|ing)|expir(?:e|ation|ing)|terminat(?:e|ion|ing)|'
    r'term|duration|renewal|perpetual|indefinite)\b',
    re.IGNORECASE,
)

# Patterns for identifying negative/empty exception notes (false positives)
_NEGATIVE_EXCEPTION_PATTERNS = [
    "no exception", "no relevant exception", "not applicable",
    "no specific exception", "none found", "does not contain",
    "no modify", "no exception clauses found", "no exception clauses",
    "no exception clause", "no clauses", "none identified",
    "no carve-out", "no carve out",
]

# Boilerplate exception phrases (standard NDA language, not hypothesis-specific)
_BOILERPLATE_EXCEPTION_PATTERNS = [
    "except as required by law",
    "except as may be required",
    "except as required by applicable",
    "compelled disclosure",
    "court order",
    "judicial process",
    "regulatory requirement",
    "legal obligation",
    "government request",
    "required by regulation",
    "required by statute",
    "subpoena",
    "legally compelled",
]


# ============================================================
# Helper: extract reasoning text from evaluations
# ============================================================

def _is_negative_exception_note(text):
    """Check if an exception_clauses_noted entry is actually saying no exceptions were found."""
    text_lower = str(text).lower().strip()
    return any(neg in text_lower for neg in _NEGATIVE_EXCEPTION_PATTERNS)


def _is_boilerplate_exception(text):
    """Check if an exception note describes standard boilerplate (e.g., compelled disclosure)."""
    text_lower = str(text).lower()
    return any(bp in text_lower for bp in _BOILERPLATE_EXCEPTION_PATTERNS)


def _spans_are_adjacent(span_set_a, span_set_b, proximity=2):
    """
    Check if any span in set_a is within ±proximity of any span in set_b.
    Both inputs should be iterables of integer span indices.
    """
    for sa in span_set_a:
        for sb in span_set_b:
            if abs(sa - sb) <= proximity:
                return True
    return False


def _extract_span_refs_from_text(text):
    """Extract span index references from exception note text (e.g., 'Span 15', 'Spans 32-35')."""
    refs = set()
    # Match "Span N" or "Spans N"
    for m in re.finditer(r'[Ss]pans?\s+(\d+)', str(text)):
        refs.add(int(m.group(1)))
    # Match "Span N-M" ranges
    for m in re.finditer(r'[Ss]pans?\s+(\d+)\s*[-–]\s*(\d+)', str(text)):
        start, end = int(m.group(1)), int(m.group(2))
        for i in range(start, end + 1):
            refs.add(i)
    return refs


def _get_all_reasoning(evaluations):
    """Collect reasoning text from all evaluators."""
    texts = []
    for label, ev in evaluations.items():
        if "error" in ev and "verdict" not in ev:
            continue
        reasoning = ev.get("reasoning", "")
        if reasoning:
            texts.append(reasoning)
    return " ".join(texts)


def _get_verdicts(evaluations):
    """Get list of verdicts from evaluators (ignoring errors)."""
    verdicts = []
    for label, ev in sorted(evaluations.items()):
        if "error" in ev and "verdict" not in ev:
            continue
        verdicts.append(ev.get("verdict", "UNKNOWN"))
    return verdicts


def _evaluators_disagree(evaluations):
    """Check if evaluators have different verdicts."""
    verdicts = _get_verdicts(evaluations)
    return len(set(verdicts)) > 1


def _confidence_is_mixed(evaluations):
    """Check if evaluators have different confidence levels."""
    confs = []
    for label, ev in evaluations.items():
        if "error" in ev and "verdict" not in ev:
            continue
        confs.append(ev.get("confidence", "unknown"))
    return len(set(confs)) > 1


# ============================================================
# Rule Check Functions
# ============================================================

def check_rule_cn_001(evaluations, challenge_result, auditor_result):
    """
    RULE-CN-001: Negation by Exception (Local)

    CALIBRATED (Step 022): Only fires when exception language is directly
    relevant to the specific hypothesis being evaluated, not just present
    anywhere in the contract.

    Two-part calibration:
    a) Tighten trigger: exception keywords must appear in evaluator's cited
       spans or within ±2 span indices of cited spans. Negative findings
       ("No exception clauses found...") are filtered out.
    b) Soften effect: boilerplate exceptions (e.g., "except as required by
       law") get mark_fragile instead of cap_L2. Only cap_L2 when the
       exception directly relates to the evaluator's reasoning.
    """
    # Collect all evaluator cited spans
    all_cited_spans = set()
    for label, ev in evaluations.items():
        if "error" in ev and "verdict" not in ev:
            continue
        cited = ev.get("cited_spans", [])
        if cited:
            all_cited_spans.update(cited)

    # --- Path 1: Check evaluator exception_clauses_noted ---
    # Filter out negative findings and check span proximity
    evaluators_with_relevant_exceptions = []
    all_boilerplate = True  # Track if all found exceptions are boilerplate

    for label, ev in evaluations.items():
        if "error" in ev and "verdict" not in ev:
            continue
        exceptions = ev.get("exception_clauses_noted", [])
        evaluator_cited = set(ev.get("cited_spans", []))
        if not exceptions:
            continue

        for exc_text in exceptions:
            # Skip negative findings ("No exception clauses found...")
            if _is_negative_exception_note(exc_text):
                continue

            # Extract span references from the exception text
            exc_spans = _extract_span_refs_from_text(exc_text)

            # Check proximity: exception must reference spans near cited spans
            # If no span refs extracted, fall back to keyword check in reasoning
            if exc_spans and evaluator_cited:
                if _spans_are_adjacent(exc_spans, evaluator_cited, proximity=2):
                    evaluators_with_relevant_exceptions.append(label)
                    if not _is_boilerplate_exception(exc_text):
                        all_boilerplate = False
                    break
            elif not exc_spans:
                # No span refs in exception text — still relevant if evaluator
                # cited something (the exception may describe cited span content)
                evaluators_with_relevant_exceptions.append(label)
                if not _is_boilerplate_exception(exc_text):
                    all_boilerplate = False
                break

    # --- Path 2: Check challenge for negation_resolution ---
    # Only count negation challenges whose missing_spans are near cited spans
    challenges = challenge_result.get("challenges", [])
    relevant_negation_challenges = []

    for ch in challenges:
        if ch.get("challenge_type") != "negation_resolution":
            continue
        missing = ch.get("missing_spans", [])
        affected = ch.get("affected_evaluators", [])

        # Get cited spans for affected evaluators
        affected_cited = set()
        for eval_label in affected:
            ev = evaluations.get(eval_label, {})
            affected_cited.update(ev.get("cited_spans", []))

        if not affected_cited:
            affected_cited = all_cited_spans

        # Only relevant if missing spans are near cited spans
        if missing and affected_cited:
            if _spans_are_adjacent(missing, affected_cited, proximity=2):
                relevant_negation_challenges.append(ch)
        elif not missing:
            # No missing spans specified — use severity as signal
            if ch.get("severity") in ("medium", "high"):
                relevant_negation_challenges.append(ch)

    # --- Decision ---
    if not relevant_negation_challenges and not evaluators_with_relevant_exceptions:
        return None

    parts = []
    if relevant_negation_challenges:
        affected = set()
        for ch in relevant_negation_challenges:
            affected.update(ch.get("affected_evaluators", []))
        parts.append(
            f"Challenge found negation issues near cited spans, "
            f"affecting evaluator(s) {', '.join(sorted(affected))}"
        )
    if evaluators_with_relevant_exceptions:
        parts.append(
            f"Evaluator(s) {', '.join(sorted(evaluators_with_relevant_exceptions))} "
            f"noted relevant exception clauses near cited spans"
        )

    # Determine severity based on challenge severity
    severity = "moderate"
    for ch in relevant_negation_challenges:
        if ch.get("severity") == "high":
            severity = "critical"
            break

    # Determine effect: boilerplate -> mark_fragile, substantive -> cap_L2
    if all_boilerplate and not relevant_negation_challenges:
        effect = "mark_fragile"
        parts.append("(boilerplate exceptions only — mark_fragile)")
    else:
        effect = "cap_L2"

    return {
        "fired": True,
        "rule_id": RULE_CN_001["id"],
        "rule_name": RULE_CN_001["name"],
        "details": "; ".join(parts),
        "effect": effect,
        "severity": severity,
    }


def check_rule_cn_002(evaluations, challenge_result, auditor_result):
    """
    RULE-CN-002: Negation by Exception (Non-local)

    Fires when challenge flagged cross_reference issue, or negation_resolution
    with missing spans that are distant from evaluator's cited spans.
    """
    challenges = challenge_result.get("challenges", [])

    # Look for cross_reference challenges
    cross_ref_challenges = [
        ch for ch in challenges
        if ch.get("challenge_type") == "cross_reference"
    ]

    # Also look for negation_resolution with missing spans
    negation_with_missing = []
    for ch in challenges:
        if ch.get("challenge_type") == "negation_resolution":
            missing = ch.get("missing_spans", [])
            if missing:
                negation_with_missing.append(ch)

    if not cross_ref_challenges and not negation_with_missing:
        return None

    parts = []
    if cross_ref_challenges:
        for ch in cross_ref_challenges:
            affected = ch.get("affected_evaluators", [])
            missing = ch.get("missing_spans", [])
            parts.append(
                f"Cross-reference gap: evaluator(s) {', '.join(affected)} "
                f"missing spans {missing}"
            )
    if negation_with_missing:
        for ch in negation_with_missing:
            affected = ch.get("affected_evaluators", [])
            missing = ch.get("missing_spans", [])
            parts.append(
                f"Negation with missing distant spans: evaluator(s) {', '.join(affected)} "
                f"missing spans {missing}"
            )

    severity = "moderate"
    for ch in cross_ref_challenges + negation_with_missing:
        if ch.get("severity") == "high":
            severity = "critical"
            break

    return {
        "fired": True,
        "rule_id": RULE_CN_002["id"],
        "rule_name": RULE_CN_002["name"],
        "details": "; ".join(parts),
        "effect": "cap_L2",
        "severity": severity,
    }


def check_rule_cn_003(evaluations, challenge_result, auditor_result):
    """
    RULE-CN-003: Definitional Dependency

    Fires when:
    - Challenge flagged definition_resolution, OR
    - Evaluator has empty definitions_traced but reasoning likely references defined terms
    """
    challenges = challenge_result.get("challenges", [])
    definition_challenges = [
        ch for ch in challenges
        if ch.get("challenge_type") == "definition_resolution"
    ]

    # Check for evaluators with empty definitions_traced
    # (a weak signal, but relevant when challenge also flags it)
    empty_defs = []
    for label, ev in evaluations.items():
        if "error" in ev and "verdict" not in ev:
            continue
        defs = ev.get("definitions_traced", [])
        if not defs:
            empty_defs.append(label)

    if not definition_challenges:
        return None

    parts = []
    affected = set()
    for ch in definition_challenges:
        affected.update(ch.get("affected_evaluators", []))
        desc = ch.get("description", "")[:120]
        parts.append(f"Definition gap: {desc}")

    if empty_defs:
        parts.append(f"Evaluator(s) {', '.join(sorted(empty_defs))} traced no definitions")

    return {
        "fired": True,
        "rule_id": RULE_CN_003["id"],
        "rule_name": RULE_CN_003["name"],
        "details": "; ".join(parts),
        "effect": "downgrade_one",
        "severity": "moderate",
    }


def check_rule_cn_004(evaluations, challenge_result, auditor_result):
    """
    RULE-CN-004: Quantifier Mismatch

    Fires when evaluator reasoning contains quantifier words AND evaluators disagree.
    """
    all_reasoning = _get_all_reasoning(evaluations)

    quantifiers_found = QUANTIFIER_PATTERN.findall(all_reasoning)
    if not quantifiers_found:
        return None

    disagree = _evaluators_disagree(evaluations)
    if not disagree:
        return None

    unique_quantifiers = sorted(set(q.lower() for q in quantifiers_found))

    return {
        "fired": True,
        "rule_id": RULE_CN_004["id"],
        "rule_name": RULE_CN_004["name"],
        "details": (
            f"Quantifier terms ({', '.join(unique_quantifiers)}) found in reasoning "
            f"and evaluators disagree on verdict"
        ),
        "effect": "downgrade_one",
        "severity": "moderate",
    }


def check_rule_cn_005(evaluations, challenge_result, auditor_result):
    """
    RULE-CN-005: Modal Verb Sensitivity

    Fires when evaluator reasoning references modal verbs and evaluators
    give different verdicts or different confidence levels.
    """
    all_reasoning = _get_all_reasoning(evaluations)

    modals_found = MODAL_PATTERN.findall(all_reasoning)
    if not modals_found:
        return None

    disagree = _evaluators_disagree(evaluations)
    mixed_conf = _confidence_is_mixed(evaluations)

    if not disagree and not mixed_conf:
        return None

    unique_modals = sorted(set(m.lower() for m in modals_found))
    trigger_reason = []
    if disagree:
        trigger_reason.append("evaluators disagree on verdict")
    if mixed_conf:
        trigger_reason.append("mixed confidence levels")

    return {
        "fired": True,
        "rule_id": RULE_CN_005["id"],
        "rule_name": RULE_CN_005["name"],
        "details": (
            f"Modal verbs ({', '.join(unique_modals)}) in reasoning; "
            f"{'; '.join(trigger_reason)}"
        ),
        "effect": "mark_fragile",
        "severity": "moderate" if disagree else "low",
    }


def check_rule_cn_006(evaluations, challenge_result, auditor_result):
    """
    RULE-CN-006: Temporal Scope Ambiguity

    Fires when evaluator reasoning mentions temporal terms (survival, expiration,
    termination, etc.) and evaluators disagree or confidence is mixed.
    """
    all_reasoning = _get_all_reasoning(evaluations)

    temporal_found = TEMPORAL_PATTERN.findall(all_reasoning)
    if not temporal_found:
        return None

    disagree = _evaluators_disagree(evaluations)
    mixed_conf = _confidence_is_mixed(evaluations)

    if not disagree and not mixed_conf:
        return None

    unique_temporal = sorted(set(t.lower() for t in temporal_found))
    trigger_reason = []
    if disagree:
        trigger_reason.append("evaluators disagree on verdict")
    if mixed_conf:
        trigger_reason.append("mixed confidence levels")

    return {
        "fired": True,
        "rule_id": RULE_CN_006["id"],
        "rule_name": RULE_CN_006["name"],
        "details": (
            f"Temporal terms ({', '.join(unique_temporal)}) in reasoning; "
            f"{'; '.join(trigger_reason)}"
        ),
        "effect": "mark_fragile",
        "severity": "moderate" if disagree else "low",
    }


# ============================================================
# Aggregate Rule Application
# ============================================================

_RULE_CHECKS = [
    check_rule_cn_001,
    check_rule_cn_002,
    check_rule_cn_003,
    check_rule_cn_004,
    check_rule_cn_005,
    check_rule_cn_006,
]


def apply_contractnli_rules(evaluations, challenge_result, auditor_result):
    """
    Run all ContractNLI rules and return list of fired rules with details.

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
