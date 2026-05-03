"""
Cross-provision conflict detection engine.

Reads conflict_rules from the schema and evaluates each rule against the coverage_assessment
array produced by lease_coverage.py. Returns a conflicts[] array describing detected conflicts.

Pure pattern matching, no LLM calls. Architecture mirrors lease_coverage.py and lease_negative_space.py.
"""

from typing import Dict, List, Any, Optional
from cam.adapters.lease_review import lease_knowledge


def detect_conflicts(
    coverage_assessment: List[Dict[str, Any]],
    provisions: Optional[List[Dict[str, Any]]] = None,
    perspective: str = "tenant"
) -> List[Dict[str, Any]]:
    """
    Detect cross-provision conflicts.

    Args:
        coverage_assessment: Output of lease_coverage.assess_coverage()
        provisions: Original provisions array (kept for future cross-text rules; unused in 297a)
        perspective: tenant / landlord / neutral — affects which conflicts surface

    Returns:
        List of conflict dicts:
        [{
            "id": "CR-01",
            "name": "...",
            "lps_implicated": ["LP-14", "LP-05"],
            "description": "...",
            "severity": "high",
            "evidence": "..."
        }, ...]
    """
    schema = lease_knowledge.get_schema()
    conflict_rules = schema.get("conflict_rules", {}).get("rules", [])

    assessment_by_lp = {a["issue_area_id"]: a for a in coverage_assessment}

    conflicts = []
    for rule in conflict_rules:
        match_result = _evaluate_rule(rule, assessment_by_lp, perspective)
        if match_result is not None:
            conflicts.append(match_result)

    return conflicts


def _evaluate_rule(
    rule: Dict[str, Any],
    assessment_by_lp: Dict[str, Dict[str, Any]],
    perspective: str
) -> Optional[Dict[str, Any]]:
    """Evaluate a single conflict rule. Returns conflict dict if matched, None otherwise."""

    # Perspective filter — neutral rules always fire; perspective-specific rules fire for that
    # perspective AND for neutral runs (so neutral runs see all conflicts)
    implicated = rule.get("implicated_perspective", "neutral")
    if implicated != "neutral" and perspective != "neutral" and implicated != perspective:
        return None

    triggers = rule.get("trigger", {})
    evidence_parts = []

    for lp_id, conditions in triggers.items():
        assessment = assessment_by_lp.get(lp_id)
        if assessment is None:
            return None  # LP not in coverage_assessment — rule cannot fire

        if not _check_lp_conditions(assessment, conditions):
            return None

        # Build evidence summary for matched LP
        ev = f"{lp_id}: {assessment.get('coverage_state')}"
        if "evidence_contains" in conditions:
            ev += f" — matched '{conditions['evidence_contains']}'"
        evidence_parts.append(ev)

    return {
        "id": rule["id"],
        "name": rule["name"],
        "lps_implicated": rule["lps"],
        "description": rule["description"],
        "severity": rule.get("severity", "medium"),
        "evidence": "; ".join(evidence_parts),
        "implicated_perspective": rule.get("implicated_perspective", "neutral")
    }


def _signals_to_text(signals: Any) -> str:
    """Extract searchable text from negative_space_signals (may be list of strs or list of dicts)."""
    if not signals:
        return ""
    parts = []
    for s in signals:
        if isinstance(s, str):
            parts.append(s)
        elif isinstance(s, dict):
            parts.append(s.get("evidence", ""))
            parts.append(s.get("description", ""))
    return " ".join(parts)


def _check_lp_conditions(assessment: Dict[str, Any], conditions: Dict[str, Any]) -> bool:
    """Check whether an assessment matches the conditions for this LP in a rule."""

    # coverage_state check
    if "coverage_state" in conditions:
        expected = conditions["coverage_state"]
        actual = assessment.get("coverage_state", "")
        if isinstance(expected, list):
            if actual not in expected:
                return False
        else:
            if actual != expected:
                return False

    ns_text = _signals_to_text(assessment.get("negative_space_signals"))

    # evidence_contains check (substring match, case-insensitive)
    if "evidence_contains" in conditions:
        needle = conditions["evidence_contains"].lower()
        haystack = (assessment.get("evidence_summary", "") + " " + ns_text).lower()
        if needle not in haystack:
            return False

    # evidence_contains_any check (any of the strings)
    if "evidence_contains_any" in conditions:
        haystack = (assessment.get("evidence_summary", "") + " " + ns_text).lower()
        needles = [n.lower() for n in conditions["evidence_contains_any"]]
        if not any(n in haystack for n in needles):
            return False

    # elements_present_includes check
    if "elements_present_includes" in conditions:
        needle = conditions["elements_present_includes"].lower()
        elements = [e.lower() for e in (assessment.get("elements_found", []) or [])]
        if not any(needle in e for e in elements):
            return False

    # elements_missing_includes check
    if "elements_missing_includes" in conditions:
        needle = conditions["elements_missing_includes"].lower()
        elements = [e.lower() for e in (assessment.get("elements_missing", []) or [])]
        if not any(needle in e for e in elements):
            return False

    # elements_missing_includes_any check (any needle matches any missing element)
    if "elements_missing_includes_any" in conditions:
        elements = [e.lower() for e in (assessment.get("elements_missing", []) or [])]
        needles = [n.lower() for n in conditions["elements_missing_includes_any"]]
        if not any(needle in element for needle in needles for element in elements):
            return False

    # elements_present_includes_any check (any needle matches any found element)
    if "elements_present_includes_any" in conditions:
        elements = [e.lower() for e in (assessment.get("elements_found", []) or [])]
        needles = [n.lower() for n in conditions["elements_present_includes_any"]]
        if not any(needle in element for needle in needles for element in elements):
            return False

    return True


def summarize_conflicts(conflicts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Summary stats for conflicts. Reserved for 297b UI work."""
    if not conflicts:
        return {"total": 0, "by_severity": {}, "lps_involved": []}

    by_severity = {}
    lps_involved = set()
    for c in conflicts:
        by_severity[c["severity"]] = by_severity.get(c["severity"], 0) + 1
        lps_involved.update(c["lps_implicated"])

    return {
        "total": len(conflicts),
        "by_severity": by_severity,
        "lps_involved": sorted(lps_involved)
    }


if __name__ == "__main__":
    # Smoke test — synthetic coverage_assessment that should fire CR-01
    test_assessment = [
        {"issue_area_id": "LP-14", "coverage_state": "covered_unfavorable",
         "evidence_summary": "Abatement only when premises are wholly untenantable",
         "elements_found": [], "elements_missing": [], "negative_space_signals": []},
        {"issue_area_id": "LP-05", "coverage_state": "covered",
         "evidence_summary": "Permitted use defined with continuous operation obligation",
         "elements_found": ["continuous operation obligation"],
         "elements_missing": [], "negative_space_signals": []},
    ]
    conflicts = detect_conflicts(test_assessment, perspective="tenant")
    print(f"Conflicts detected: {len(conflicts)}")
    for c in conflicts:
        print(f"  {c['id']}: {c['name']} (severity: {c['severity']})")
        print(f"    Evidence: {c['evidence']}")
    assert len(conflicts) >= 1, "Smoke test failed: CR-01 should have fired"
    print("Smoke test PASSED")
