"""
Jurisdiction-aware coverage state escalation.

Reads jurisdiction_rules from the schema and applies state-specific escalations to
coverage_assessment entries based on the governing law extracted from LP-17.

Pure pattern matching, no LLM calls.
"""

import re
from typing import Any, Dict, List, Optional, Tuple
from cam.adapters.lease_review import lease_knowledge


# State name → state code mapping
_STATE_PATTERNS = [
    (r"\b(?:state\s+of\s+)?new\s+york\b", "NY"),
    (r"\bN\.?\s*Y\.?\b", "NY"),
    (r"\b(?:state\s+of\s+)?california\b", "CA"),
    (r"\bCal\.?\b", "CA"),
    (r"\b(?:state\s+of\s+)?texas\b", "TX"),
    (r"\bTex\.?\b", "TX"),
    (r"\b(?:state\s+of\s+)?florida\b", "FL"),
    (r"\bFla\.?\b", "FL"),
    (r"\b(?:state\s+of\s+)?illinois\b", "IL"),
    (r"\bIll\.?\b", "IL"),
]


def extract_governing_law(
    coverage_assessment: List[Dict[str, Any]],
    provisions: Optional[List[Dict[str, Any]]] = None,
    contract_metadata: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """
    Extract governing law state code from contract_metadata or LP-17 assessment.
    Returns 2-letter state code or None if not detected.

    Sources checked, in priority order:
      1. contract_metadata.governing_law (most reliable — extractor pulls this directly)
      2. LP-17 evidence_summary and elements_found
      3. LP-17 raw provision text (tenant_text / template_text) if provisions provided
    """
    text_parts = []

    # Source 1: contract_metadata.governing_law (highest priority)
    if contract_metadata and contract_metadata.get("governing_law"):
        text_parts.append(contract_metadata["governing_law"])

    # Source 2 & 3: LP-17 fields
    lp17 = next((a for a in coverage_assessment if a.get("issue_area_id") == "LP-17"), None)
    if lp17:
        text_parts.append(lp17.get("evidence_summary", ""))
        text_parts.append(" ".join(lp17.get("elements_found", []) or []))

    if provisions:
        lp17_prov = next((p for p in provisions if p.get("provision_id") == "LP-17"), None)
        if lp17_prov:
            text_parts.append(lp17_prov.get("tenant_text", "") or "")
            text_parts.append(lp17_prov.get("template_text", "") or "")

    text = " ".join(text_parts)

    for pattern, code in _STATE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return code

    return None


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


def apply_jurisdiction_rules(
    coverage_assessment: List[Dict[str, Any]],
    governing_law: Optional[str] = None,
    provisions: Optional[List[Dict[str, Any]]] = None,
    contract_metadata: Optional[Dict[str, Any]] = None
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Apply jurisdiction-specific escalations to coverage_assessment.

    Args:
        coverage_assessment: Output of lease_coverage.assess_coverage()
        governing_law: 2-letter state code, or None to auto-extract
        provisions: Optional, used for governing law extraction
        contract_metadata: Optional, used for governing law extraction (highest priority)

    Returns:
        (modified_assessment, escalation_log)
    """
    if governing_law is None:
        governing_law = extract_governing_law(coverage_assessment, provisions, contract_metadata)

    if not governing_law:
        return (coverage_assessment, [])

    schema = lease_knowledge.get_schema()
    state_rules = schema.get("jurisdiction_rules", {}).get("states", {}).get(governing_law)
    if not state_rules:
        return (coverage_assessment, [])

    escalation_log = []
    assessment_by_lp = {a["issue_area_id"]: a for a in coverage_assessment}

    for rule in state_rules.get("rules", []):
        lp_id = rule["lp"]
        assessment = assessment_by_lp.get(lp_id)
        if not assessment:
            continue

        # Use evidence_summary + signals for positive match (contains_any)
        # Use evidence_summary ONLY for negative match (not_contains) — signals describe
        # what's absent (e.g. "without 'commercially reasonable' qualifier") which would
        # false-positive if included in the not-contains haystack.
        evidence_text = assessment.get("evidence_summary", "").lower()
        full_text = (evidence_text + " " +
                     _signals_to_text(assessment.get("negative_space_signals"))).lower()

        any_required = rule.get("if_evidence_contains_any", [])
        if any_required:
            if not any(needle.lower() in full_text for needle in any_required):
                continue

        none_required = rule.get("if_evidence_not_contains", [])
        if none_required:
            if any(needle.lower() in evidence_text for needle in none_required):
                continue

        old_state = assessment.get("coverage_state")
        new_state = rule.get("escalate_to")
        if new_state and old_state != new_state:
            assessment["coverage_state"] = new_state
            assessment["jurisdiction_escalation"] = {
                "from": old_state,
                "to": new_state,
                "state": governing_law,
                "rationale": rule.get("rationale", "")
            }
            escalation_log.append({
                "lp_id": lp_id,
                "from": old_state,
                "to": new_state,
                "rationale": rule.get("rationale", ""),
                "rule_state": governing_law,
                "state_name": state_rules.get("name", governing_law)
            })

    return (coverage_assessment, escalation_log)


if __name__ == "__main__":
    # Test 1: governing law via LP-17 evidence (existing path)
    test_assessment = [
        {"issue_area_id": "LP-09", "coverage_state": "covered_unfavorable",
         "evidence_summary": "Landlord consent required in sole and absolute discretion",
         "elements_found": [], "elements_missing": [], "negative_space_signals": []},
        {"issue_area_id": "LP-17", "coverage_state": "covered",
         "evidence_summary": "Governed by laws of the State of New York",
         "elements_found": [], "elements_missing": [], "negative_space_signals": []},
    ]
    state = extract_governing_law(test_assessment)
    print(f"Test 1 (LP-17 evidence): detected {state}")
    assert state == "NY"

    # Test 2: governing law via contract_metadata
    test_assessment_no_lp17 = [
        {"issue_area_id": "LP-09", "coverage_state": "covered_unfavorable",
         "evidence_summary": "Landlord consent required in sole and absolute discretion",
         "elements_found": [], "elements_missing": [], "negative_space_signals": []},
    ]
    state2 = extract_governing_law(
        test_assessment_no_lp17,
        contract_metadata={"governing_law": "State of California"}
    )
    print(f"Test 2 (contract_metadata): detected {state2}")
    assert state2 == "CA"

    # Test 3: full escalation chain
    modified, log = apply_jurisdiction_rules(test_assessment)
    print(f"Test 3 escalations: {len(log)}")
    for entry in log:
        print(f"  {entry['lp_id']}: {entry['from']} -> {entry['to']}")
    assert len(log) >= 1

    print("Smoke test PASSED")
