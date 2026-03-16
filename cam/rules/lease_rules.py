"""
CAM Lease Review — Legal Fragility Rule Library

8 rules for detecting legal fragility patterns in lease provisions.
All rules are pure Python pattern matching — zero API calls.

Rules follow the one-directional CAM principle: they can only FLAG risk,
never suppress it. A rule firing means "this needs attention" — it never
means "this is safe."

Each rule takes template text and tenant text for a provision and returns
a result dict.
"""

import re
from typing import Dict, List, Optional


# ============================================================
# Rule Metadata
# ============================================================

RULE_LS_001 = {
    "id": "RULE-LS-001",
    "name": "Exception Clause",
    "description": "Detects added exception language in tenant lease",
    "signal": "exception_clause",
}

RULE_LS_002 = {
    "id": "RULE-LS-002",
    "name": "Definition Override",
    "description": "Key term redefined differently from template definitions section",
    "signal": "definition_override",
}

RULE_LS_003 = {
    "id": "RULE-LS-003",
    "name": "Qualifier Shift",
    "description": "Obligation qualifier weakened or strengthened",
    "signal": "qualifier_shift",
}

RULE_LS_004 = {
    "id": "RULE-LS-004",
    "name": "Quantitative Deviation",
    "description": "Dollar amounts, percentages, or time periods differ",
    "signal": "quantitative_deviation",
}

RULE_LS_005 = {
    "id": "RULE-LS-005",
    "name": "Negation Pattern",
    "description": "Negation added or removed, reversing obligations",
    "signal": "negation_pattern",
}

RULE_LS_006 = {
    "id": "RULE-LS-006",
    "name": "Cross-Reference Dependency",
    "description": "Clause references another section that may have been modified",
    "signal": "cross_reference_dependency",
}

RULE_LS_007 = {
    "id": "RULE-LS-007",
    "name": "Omission Detection",
    "description": "Provision present in template but missing from tenant lease",
    "signal": "omission",
}

RULE_LS_008 = {
    "id": "RULE-LS-008",
    "name": "Obligation Direction Swap",
    "description": "Landlord/tenant responsibility has been swapped",
    "signal": "obligation_swap",
}

ALL_RULES = [
    RULE_LS_001, RULE_LS_002, RULE_LS_003, RULE_LS_004,
    RULE_LS_005, RULE_LS_006, RULE_LS_007, RULE_LS_008,
]


# ============================================================
# Rule Implementation Functions
# ============================================================

# Exception clause patterns: language that carves out exceptions
_EXCEPTION_PATTERNS = [
    r"provided,?\s+however,?\s+that",
    r"except\s+(?:for|as|that|in\s+the\s+case\s+of|where)",
    r"notwithstanding\s+(?:anything|the\s+foregoing|any)",
    r"other\s+than",
    r"excluding",
    r"with\s+the\s+exception\s+of",
    r"save\s+and\s+except",
    r"subject\s+to\s+the\s+following\s+exception",
    r"unless\s+otherwise",
]

# Qualifier pairs: (stronger, weaker) — direction matters
_QUALIFIER_PAIRS = [
    ("shall", "may"),
    ("must", "may"),
    ("must", "should"),
    ("shall", "should"),
    ("best efforts", "commercially reasonable efforts"),
    ("best efforts", "reasonable efforts"),
    ("commercially reasonable efforts", "reasonable efforts"),
    ("sole discretion", "reasonable discretion"),
    ("absolute discretion", "sole discretion"),
    ("written consent", "consent"),
    ("prior written consent", "consent"),
    ("prior written notice", "notice"),
]

# Negation words/phrases
_NEGATION_WORDS = [
    r"\bnot\b",
    r"\bneither\b",
    r"\bnor\b",
    r"\bwithout\s+limitation\b",
    r"\bno\b(?!\s+later\b)(?!\s+less\b)(?!\s+fewer\b)(?!\s+more\b)",
    r"\bin\s+no\s+event\b",
    r"\bunder\s+no\s+circumstances\b",
    r"\bshall\s+not\b",
    r"\bwill\s+not\b",
]

# Patterns for detecting landlord/tenant obligation references
_LANDLORD_OBLIGATION_PATTERNS = [
    r"landlord\s+shall",
    r"landlord\s+will",
    r"landlord\s+is\s+responsible",
    r"landlord['']s\s+(?:sole\s+)?(?:cost|expense|obligation|responsibility)",
    r"at\s+landlord['']s\s+(?:sole\s+)?(?:cost|expense)",
]

_TENANT_OBLIGATION_PATTERNS = [
    r"tenant\s+shall",
    r"tenant\s+will",
    r"tenant\s+is\s+responsible",
    r"tenant['']s\s+(?:sole\s+)?(?:cost|expense|obligation|responsibility)",
    r"at\s+tenant['']s\s+(?:sole\s+)?(?:cost|expense)",
]


def check_rule_ls_001(template_text: str, tenant_text: str) -> dict:
    """RULE-LS-001: Exception Clause Detection.

    Checks if tenant lease adds exception language not present in template.
    """
    template_lower = template_text.lower()
    tenant_lower = tenant_text.lower()

    found_exceptions = []
    for pattern in _EXCEPTION_PATTERNS:
        template_matches = re.findall(pattern, template_lower, re.IGNORECASE)
        tenant_matches = re.findall(pattern, tenant_lower, re.IGNORECASE)

        # Fire if tenant has MORE instances of the pattern than template
        if len(tenant_matches) > len(template_matches):
            # Find the actual text in tenant for details
            for m in re.finditer(pattern, tenant_lower, re.IGNORECASE):
                # Expand to sentence boundaries: back to previous period/newline,
                # forward to next period/newline. Minimum ±100 chars.
                raw_start = max(0, m.start() - 100)
                raw_end = min(len(tenant_text), m.end() + 150)
                # Snap back to start of sentence (after last . or newline)
                pre = tenant_text[raw_start:m.start()]
                sent_break = max(pre.rfind('. '), pre.rfind('\n'), pre.rfind('; '))
                start = raw_start + sent_break + 2 if sent_break >= 0 else raw_start
                # Snap forward to end of sentence (next . or newline)
                post = tenant_text[m.end():raw_end]
                sent_end = min(
                    (post.find('. ') + 1) if post.find('. ') >= 0 else len(post),
                    (post.find('\n') + 1) if post.find('\n') >= 0 else len(post),
                )
                end = m.end() + sent_end if sent_end < len(post) else raw_end
                context = tenant_text[start:end].strip()
                # Store match offsets relative to context for highlighting
                match_start_in_context = m.start() - start
                match_end_in_context = m.end() - start
                found_exceptions.append({
                    "text": context,
                    "match_start": match_start_in_context,
                    "match_end": match_end_in_context,
                    "matched_phrase": tenant_text[m.start():m.end()],
                })

    if found_exceptions:
        # Build details string from text excerpts for backward compatibility
        detail_parts = [ex["text"] if isinstance(ex, dict) else ex for ex in found_exceptions[:3]]
        return {
            "rule_id": "RULE-LS-001",
            "fired": True,
            "signal": "exception_clause",
            "details": f"Found exception language in tenant not in template: {'; '.join(detail_parts)}",
            "excerpts": found_exceptions[:3],  # structured excerpts with highlight offsets
            "confidence": 0.9,
        }

    return {"rule_id": "RULE-LS-001", "fired": False, "signal": "exception_clause", "details": "", "confidence": 0.0}


def identify_changed_definitions(template_definitions: str, tenant_definitions: str) -> List[str]:
    """Compare definitions sections and return list of changed term names.

    Used by RULE-LS-002 to scope per-provision firing.
    """
    if not template_definitions or not tenant_definitions:
        return []
    tmpl_def = template_definitions.strip().lower()
    tenant_def = tenant_definitions.strip().lower()
    if tmpl_def == tenant_def:
        return []

    # Extract defined terms (words in quotes)
    tmpl_terms = set(re.findall(r'"([^"]+)"', template_definitions))
    tenant_terms = set(re.findall(r'"([^"]+)"', tenant_definitions))

    changed_terms = []
    for term in tmpl_terms & tenant_terms:
        tmpl_pattern = re.escape(f'"{term}"') + r"[^.]*\."
        tenant_pattern = re.escape(f'"{term}"') + r"[^.]*\."
        tmpl_match = re.search(tmpl_pattern, template_definitions, re.IGNORECASE)
        tenant_match = re.search(tenant_pattern, tenant_definitions, re.IGNORECASE)
        if tmpl_match and tenant_match:
            tmpl_defn_text = tmpl_match.group().strip()
            if tmpl_defn_text.lower() != tenant_match.group().strip().lower():
                # Skip blank-fill completions: filling in a template placeholder
                # (e.g. Suite _____ -> Suite 220) is NOT a definition override.
                if re.search(r'_{2,}|\[_+\]|\[blank\]|\[insert[^\]]*\]', tmpl_defn_text, re.IGNORECASE):
                    continue
                changed_terms.append(term)

    # Also flag terms only in one side
    added = tenant_terms - tmpl_terms
    removed = tmpl_terms - tenant_terms
    changed_terms.extend(added)
    changed_terms.extend(removed)

    return changed_terms


def check_rule_ls_002(template_text: str, tenant_text: str, template_definitions: str = "", tenant_definitions: str = "", changed_terms: List[str] = None) -> dict:
    """RULE-LS-002: Definition Override Detection.

    Scoped to per-provision: only fires if this provision's text references
    a defined term that was actually changed between template and tenant.
    changed_terms should be pre-computed at document level via identify_changed_definitions().
    """
    # If changed_terms provided (preferred path), check if provision references any
    if changed_terms is not None:
        if not changed_terms:
            return {"rule_id": "RULE-LS-002", "fired": False, "signal": "definition_override", "details": "", "confidence": 0.0}

        # Check if this provision's text references any changed term
        provision_text = (template_text + " " + tenant_text).lower()
        referenced = [term for term in changed_terms if term.lower() in provision_text]
        if referenced:
            return {
                "rule_id": "RULE-LS-002",
                "fired": True,
                "signal": "definition_override",
                "details": f"References changed defined terms: {', '.join(referenced[:5])}",
                "confidence": 0.85,
            }
        return {"rule_id": "RULE-LS-002", "fired": False, "signal": "definition_override", "details": "", "confidence": 0.0}

    # Legacy path: if changed_terms not provided, compare definitions directly
    if template_definitions and tenant_definitions:
        legacy_changed = identify_changed_definitions(template_definitions, tenant_definitions)
        if legacy_changed:
            provision_text = (template_text + " " + tenant_text).lower()
            referenced = [term for term in legacy_changed if term.lower() in provision_text]
            if referenced:
                return {
                    "rule_id": "RULE-LS-002",
                    "fired": True,
                    "signal": "definition_override",
                    "details": f"References changed defined terms: {', '.join(referenced[:5])}",
                    "confidence": 0.85,
                }
            return {"rule_id": "RULE-LS-002", "fired": False, "signal": "definition_override", "details": "", "confidence": 0.0}

    # Fallback: check for percentage/threshold changes near defined terms
    tmpl_percents = re.findall(r'(\w+(?:\s+\w+)?)\s*(?:means?|shall\s+mean)\s+[^.]*?(\d+(?:\.\d+)?)\s*(?:percent|%)', template_text, re.IGNORECASE)
    tenant_percents = re.findall(r'(\w+(?:\s+\w+)?)\s*(?:means?|shall\s+mean)\s+[^.]*?(\d+(?:\.\d+)?)\s*(?:percent|%)', tenant_text, re.IGNORECASE)

    if tmpl_percents and tenant_percents:
        tmpl_dict = {t[0].lower(): float(t[1]) for t in tmpl_percents}
        tenant_dict = {t[0].lower(): float(t[1]) for t in tenant_percents}

        changes = []
        for term in set(tmpl_dict) & set(tenant_dict):
            if tmpl_dict[term] != tenant_dict[term]:
                changes.append(f"{term}: {tmpl_dict[term]}% → {tenant_dict[term]}%")

        if changes:
            return {
                "rule_id": "RULE-LS-002",
                "fired": True,
                "signal": "definition_override",
                "details": f"Definition thresholds changed: {'; '.join(changes[:3])}",
                "confidence": 0.8,
            }

    return {"rule_id": "RULE-LS-002", "fired": False, "signal": "definition_override", "details": "", "confidence": 0.0}


def check_rule_ls_003(template_text: str, tenant_text: str) -> dict:
    """RULE-LS-003: Qualifier Shift Detection.

    Checks if obligation qualifiers have been weakened or changed.
    """
    template_lower = template_text.lower()
    tenant_lower = tenant_text.lower()
    shifts = []

    for stronger, weaker in _QUALIFIER_PAIRS:
        stronger_in_template = len(re.findall(r'\b' + re.escape(stronger) + r'\b', template_lower))
        weaker_in_template = len(re.findall(r'\b' + re.escape(weaker) + r'\b', template_lower))
        stronger_in_tenant = len(re.findall(r'\b' + re.escape(stronger) + r'\b', tenant_lower))
        weaker_in_tenant = len(re.findall(r'\b' + re.escape(weaker) + r'\b', tenant_lower))

        # Detect downgrade: stronger term lost AND weaker term gained
        if stronger_in_template > stronger_in_tenant and weaker_in_tenant > weaker_in_template:
            shifts.append(f'"{stronger}" → "{weaker}"')

    if shifts:
        return {
            "rule_id": "RULE-LS-003",
            "fired": True,
            "signal": "qualifier_shift",
            "details": f"Qualifier shifts detected: {'; '.join(shifts[:3])}",
            "confidence": 0.85,
        }

    return {"rule_id": "RULE-LS-003", "fired": False, "signal": "qualifier_shift", "details": "", "confidence": 0.0}


def check_rule_ls_004(template_text: str, tenant_text: str) -> dict:
    """RULE-LS-004: Quantitative Deviation Detection.

    Checks for differences in dollar amounts, percentages, time periods.
    """
    # Extract dollar amounts
    def extract_dollars(text):
        # Match patterns like "$5,000", "$5,000.00", "Five Thousand Dollars ($5,000)"
        return re.findall(r'\$[\d,]+(?:\.\d{2})?', text)

    # Extract percentages
    def extract_percentages(text):
        # Match patterns like "5%", "5 percent", "five percent (5%)"
        return re.findall(r'(\d+(?:\.\d+)?)\s*(?:%|percent)', text, re.IGNORECASE)

    # Extract time periods
    def extract_time_periods(text):
        # Match patterns like "30 days", "six (6) months", "5 years"
        return re.findall(r'(\d+)\s*(?:\))?\s*(days?|months?|years?|business\s+days?)', text, re.IGNORECASE)

    tmpl_dollars = extract_dollars(template_text)
    tenant_dollars = extract_dollars(tenant_text)
    tmpl_percents = extract_percentages(template_text)
    tenant_percents = extract_percentages(tenant_text)
    tmpl_periods = extract_time_periods(template_text)
    tenant_periods = extract_time_periods(tenant_text)

    deviations = []

    # Compare dollar amounts (simple: check if sets differ)
    if set(tmpl_dollars) != set(tenant_dollars):
        added = set(tenant_dollars) - set(tmpl_dollars)
        removed = set(tmpl_dollars) - set(tenant_dollars)
        if added or removed:
            parts = []
            if removed:
                parts.append(f"removed: {', '.join(list(removed)[:3])}")
            if added:
                parts.append(f"added: {', '.join(list(added)[:3])}")
            deviations.append(f"Dollar amounts changed ({'; '.join(parts)})")

    # Compare percentages
    if set(tmpl_percents) != set(tenant_percents):
        added = set(tenant_percents) - set(tmpl_percents)
        removed = set(tmpl_percents) - set(tenant_percents)
        if added or removed:
            deviations.append(f"Percentages changed (template: {tmpl_percents}, tenant: {tenant_percents})")

    # Compare time periods
    tmpl_period_set = set((n, u.lower().rstrip('s')) for n, u in tmpl_periods)
    tenant_period_set = set((n, u.lower().rstrip('s')) for n, u in tenant_periods)
    if tmpl_period_set != tenant_period_set:
        diff = tmpl_period_set.symmetric_difference(tenant_period_set)
        if diff:
            deviations.append(f"Time periods differ: {[f'{n} {u}' for n, u in list(diff)[:4]]}")

    if deviations:
        return {
            "rule_id": "RULE-LS-004",
            "fired": True,
            "signal": "quantitative_deviation",
            "details": "; ".join(deviations[:3]),
            "confidence": 0.8,
        }

    return {"rule_id": "RULE-LS-004", "fired": False, "signal": "quantitative_deviation", "details": "", "confidence": 0.0}


def check_rule_ls_005(template_text: str, tenant_text: str) -> dict:
    """RULE-LS-005: Negation Pattern Detection.

    Checks for added or removed negation that could reverse obligations.
    """
    template_lower = template_text.lower()
    tenant_lower = tenant_text.lower()
    changes = []

    for pattern in _NEGATION_WORDS:
        tmpl_count = len(re.findall(pattern, template_lower))
        tenant_count = len(re.findall(pattern, tenant_lower))

        if tmpl_count != tenant_count:
            # Find the pattern text for reporting
            pattern_clean = pattern.replace(r"\b", "").replace(r"\s+", " ")
            if tenant_count > tmpl_count:
                changes.append(f"Added negation: '{pattern_clean}' ({tmpl_count} → {tenant_count})")
            else:
                changes.append(f"Removed negation: '{pattern_clean}' ({tmpl_count} → {tenant_count})")

    if changes:
        return {
            "rule_id": "RULE-LS-005",
            "fired": True,
            "signal": "negation_pattern",
            "details": "; ".join(changes[:3]),
            "confidence": 0.75,
        }

    return {"rule_id": "RULE-LS-005", "fired": False, "signal": "negation_pattern", "details": "", "confidence": 0.0}


def check_rule_ls_006(template_text: str, tenant_text: str, modified_sections: List[str] = None) -> dict:
    """RULE-LS-006: Cross-Reference Dependency Detection.

    Checks if the clause references other sections, and flags if those sections
    may have been modified (indicated by modified_sections list).
    """
    # Extract section references from tenant text
    section_refs = re.findall(
        r'(?:Section|Article|Paragraph)\s+(\d+(?:\.\d+)?)',
        tenant_text,
        re.IGNORECASE,
    )

    if not section_refs:
        return {"rule_id": "RULE-LS-006", "fired": False, "signal": "cross_reference_dependency", "details": "", "confidence": 0.0}

    # If we have a list of modified sections, check for overlap
    if modified_sections:
        modified_set = set(s.lower() for s in modified_sections)
        flagged_refs = [ref for ref in section_refs if ref.lower() in modified_set]
        if flagged_refs:
            return {
                "rule_id": "RULE-LS-006",
                "fired": True,
                "signal": "cross_reference_dependency",
                "details": f"Clause references modified sections: {', '.join(sorted(set(flagged_refs))[:5])}",
                "confidence": 0.85,
            }

    # Fallback: just note that cross-references exist (lower confidence)
    if len(section_refs) > 2:
        unique_refs = sorted(set(section_refs))
        return {
            "rule_id": "RULE-LS-006",
            "fired": True,
            "signal": "cross_reference_dependency",
            "details": f"Clause has {len(section_refs)} cross-references to other sections: {', '.join(unique_refs[:5])}. Verify referenced sections are unchanged.",
            "confidence": 0.4,
        }

    return {"rule_id": "RULE-LS-006", "fired": False, "signal": "cross_reference_dependency", "details": "", "confidence": 0.0}


def check_rule_ls_007(template_text: str, tenant_text: str, status: str = None) -> dict:
    """RULE-LS-007: Omission Detection.

    Checks if a provision present in the template is missing from the tenant lease.
    Can use the extraction status directly, or check for omission markers.
    """
    # Direct status check from extraction
    if status == "TEMPLATE_ONLY":
        return {
            "rule_id": "RULE-LS-007",
            "fired": True,
            "signal": "omission",
            "details": "Provision present in template but missing from tenant lease.",
            "confidence": 0.95,
        }

    # Check for intentional omission markers
    tenant_lower = tenant_text.lower().strip()
    omission_markers = [
        "intentionally omitted",
        "intentionally deleted",
        "intentionally left blank",
        "this section intentionally",
        "[omitted]",
    ]
    # "reserved" needs word boundary check to avoid matching "unreserved", "reserved parking", etc.
    _RESERVED_PATTERN = re.compile(
        r'(?:^|\.\s+)\[?\s*reserved\s*\]?\s*\.?\s*$'   # standalone "Reserved." or "[Reserved]"
        r'|(?:section|article)\s+\S+\s+(?:is\s+)?reserved',  # "Section X is reserved"
        re.IGNORECASE,
    )

    for marker in omission_markers:
        if marker in tenant_lower:
            return {
                "rule_id": "RULE-LS-007",
                "fired": True,
                "signal": "omission",
                "details": f"Provision marked as intentionally omitted in tenant lease ('{marker}' found).",
                "confidence": 0.95,
            }

    # Check for standalone "Reserved" as omission marker (word-boundary safe)
    if _RESERVED_PATTERN.search(tenant_lower):
        return {
            "rule_id": "RULE-LS-007",
            "fired": True,
            "signal": "omission",
            "details": "Provision marked as 'Reserved' in tenant lease.",
            "confidence": 0.95,
        }

    # Check if tenant text is substantially shorter (may indicate partial omission)
    if template_text and tenant_text:
        tmpl_len = len(template_text.strip())
        tenant_len = len(tenant_text.strip())
        if tmpl_len > 100 and tenant_len < tmpl_len * 0.2:
            return {
                "rule_id": "RULE-LS-007",
                "fired": True,
                "signal": "omission",
                "details": f"Tenant text is {tenant_len} chars vs template's {tmpl_len} chars — possible partial omission.",
                "confidence": 0.6,
            }

    return {"rule_id": "RULE-LS-007", "fired": False, "signal": "omission", "details": "", "confidence": 0.0}


def check_rule_ls_008(template_text: str, tenant_text: str) -> dict:
    """RULE-LS-008: Obligation Direction Swap Detection.

    Checks if landlord/tenant responsibilities have been swapped.
    """
    template_lower = template_text.lower()
    tenant_lower = tenant_text.lower()

    # Count landlord obligation patterns
    tmpl_landlord = sum(len(re.findall(p, template_lower)) for p in _LANDLORD_OBLIGATION_PATTERNS)
    tenant_landlord = sum(len(re.findall(p, tenant_lower)) for p in _LANDLORD_OBLIGATION_PATTERNS)
    tmpl_tenant_ob = sum(len(re.findall(p, template_lower)) for p in _TENANT_OBLIGATION_PATTERNS)
    tenant_tenant_ob = sum(len(re.findall(p, tenant_lower)) for p in _TENANT_OBLIGATION_PATTERNS)

    swaps = []

    # Detect if landlord obligations decreased while tenant obligations increased
    if tmpl_landlord > tenant_landlord and tenant_tenant_ob > tmpl_tenant_ob:
        swaps.append(
            f"Landlord obligations decreased ({tmpl_landlord} → {tenant_landlord}), "
            f"tenant obligations increased ({tmpl_tenant_ob} → {tenant_tenant_ob})"
        )

    # Detect if tenant obligations decreased while landlord obligations increased
    if tmpl_tenant_ob > tenant_tenant_ob and tenant_landlord > tmpl_landlord:
        swaps.append(
            f"Tenant obligations decreased ({tmpl_tenant_ob} → {tenant_tenant_ob}), "
            f"landlord obligations increased ({tmpl_landlord} → {tenant_landlord})"
        )

    if swaps:
        return {
            "rule_id": "RULE-LS-008",
            "fired": True,
            "signal": "obligation_swap",
            "details": "; ".join(swaps),
            "confidence": 0.7,
        }

    return {"rule_id": "RULE-LS-008", "fired": False, "signal": "obligation_swap", "details": "", "confidence": 0.0}


# ============================================================
# Main entry point: run all rules on a provision pair
# ============================================================

def run_all_rules(
    template_text: str,
    tenant_text: str,
    status: str = None,
    template_definitions: str = "",
    tenant_definitions: str = "",
    modified_sections: List[str] = None,
    changed_terms: List[str] = None,
) -> List[dict]:
    """Run all 8 lease rules on a single provision's text pair.

    Args:
        template_text: Provision text from template.
        tenant_text: Provision text from tenant lease.
        status: Extraction status (FOUND_BOTH, TEMPLATE_ONLY, etc.).
        template_definitions: Definitions section from template (for RULE-LS-002).
        tenant_definitions: Definitions section from tenant (for RULE-LS-002).
        modified_sections: List of section numbers known to be modified (for RULE-LS-006).
        changed_terms: Pre-computed list of changed defined terms (for scoped RULE-LS-002).

    Returns:
        List of rule result dicts (one per rule, regardless of whether fired).
    """
    results = [
        check_rule_ls_001(template_text, tenant_text),
        check_rule_ls_002(template_text, tenant_text, template_definitions, tenant_definitions, changed_terms),
        check_rule_ls_003(template_text, tenant_text),
        check_rule_ls_004(template_text, tenant_text),
        check_rule_ls_005(template_text, tenant_text),
        check_rule_ls_006(template_text, tenant_text, modified_sections),
        check_rule_ls_007(template_text, tenant_text, status),
        check_rule_ls_008(template_text, tenant_text),
    ]
    return results


def get_fired_rules(results: List[dict]) -> List[dict]:
    """Filter rule results to only those that fired."""
    return [r for r in results if r.get("fired", False)]
