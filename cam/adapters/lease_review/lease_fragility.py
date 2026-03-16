"""
CAM Lease Review — Stage 4: Rule-Based Fragility Detection

0 API calls. Pure Python using cam/rules/lease_rules.py.
Runs ALL 8 rules on ALL provisions (not just flagged).
Rules provide independent signal that feeds into triage.
"""

import re
from typing import Dict, List

from cam.rules.lease_rules import run_all_rules, get_fired_rules, identify_changed_definitions


def _extract_definitions_section(full_text: str) -> str:
    """Extract the definitions article from a full lease text."""
    blocks = re.split(r'={10,}', full_text)
    for i, block in enumerate(blocks):
        if 'DEFINITIONS' in block.upper():
            if i + 1 < len(blocks):
                return blocks[i + 1].strip()
    return ""


def detect_fragility(
    extraction_provisions: List[dict],
    template_text: str = "",
    tenant_text: str = "",
) -> List[dict]:
    """Run all lease rules on extracted provision text.

    Runs on ALL provisions, not just flagged ones.
    Rules may catch things evaluators miss (and vice versa).

    Args:
        extraction_provisions: List of provision dicts from Stage 1.
        template_text: Full template document text (for definitions extraction).
        tenant_text: Full tenant document text (for definitions extraction).

    Returns:
        List of fragility results, one per provision.
    """
    # Extract definitions sections for RULE-LS-002
    template_defs = _extract_definitions_section(template_text) if template_text else ""
    tenant_defs = _extract_definitions_section(tenant_text) if tenant_text else ""

    # Pre-compute changed definitions at document level (Fix 1: scoped RULE-LS-002)
    changed_terms = identify_changed_definitions(template_defs, tenant_defs)

    # Collect modified section numbers for RULE-LS-006
    modified_sections = []
    for prov in extraction_provisions:
        notes = prov.get("alignment_notes", "").lower()
        defn = prov.get("definition_changes", "").lower()
        if ("modif" in notes or "different" in notes or "added" in notes or
                "exception" in notes or defn):
            # Extract section refs
            refs = re.findall(r'(?:Section|Article)\s+(\d+(?:\.\d+)?)', prov.get("tenant_section_ref", ""), re.IGNORECASE)
            modified_sections.extend(refs)

    results = []
    for prov in extraction_provisions:
        pid = prov["provision_id"]
        tmpl = prov.get("template_text", "")
        tenant = prov.get("tenant_text", "")
        status = prov.get("status", "FOUND_BOTH")

        # Run all 8 rules
        rule_results = run_all_rules(
            template_text=tmpl,
            tenant_text=tenant,
            status=status,
            template_definitions=template_defs,
            tenant_definitions=tenant_defs,
            modified_sections=modified_sections,
            changed_terms=changed_terms,
        )

        fired = get_fired_rules(rule_results)

        # Compute fragility score
        # Weighted average of fired rule confidences, rules < 0.3 don't count
        significant_rules = [r for r in fired if r.get("confidence", 0) >= 0.3]
        if significant_rules:
            score = sum(r["confidence"] for r in significant_rules) / len(significant_rules)
            score = min(1.0, score)
        else:
            score = 0.0

        results.append({
            "provision_id": pid,
            "fragile": len(fired) > 0,
            "rules_fired": [
                {
                    "rule_id": r["rule_id"],
                    "signal": r["signal"],
                    "details": r["details"],
                    "confidence": r["confidence"],
                }
                for r in fired
            ],
            "all_rule_results": rule_results,
            "fragility_score": round(score, 3),
        })

    return results
