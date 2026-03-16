"""
CAM Lease Review — Cross-Reference Linker (Step 115)

Post-processing pass that connects conforming fragile provisions to deviating
provisions whose definition changes affect them.

Runs after Stage 6 (Disposition) and before report generation.
Uses data already present in pipeline results — no API calls.

This is additive only: no verdicts or severities are changed. The linkage
is purely informational, surfaced as warnings in the UI and PDF.
"""

from typing import Any, Dict, List


def run(results: dict) -> dict:
    """Run cross-reference linkage on pipeline results.

    Scans for deviating provisions with cascade/definition changes,
    then finds conforming provisions with cross_reference_dependency
    that reference those same terms.

    Args:
        results: Full pipeline results dict (with "provisions" list).

    Returns:
        Same results dict with cross_reference_links added to affected
        provisions and cross_reference_warnings added to summary.
        Returns unchanged if no links are found.
    """
    provisions = results.get("provisions", [])
    if not provisions:
        return results

    # Step 1: Collect deviating provisions with definition changes
    deviating_definitions = _collect_deviating_definitions(provisions)

    if not deviating_definitions:
        return results

    # Step 2: Find conforming provisions with cross_reference_dependency
    # Step 3: Build linkage records
    warnings = []
    for prov in provisions:
        if prov.get("final_verdict") != "CONFORMS":
            continue

        fragility = prov.get("fragility", {})
        signals = fragility.get("signals", [])
        if "cross_reference_dependency" not in signals:
            continue

        # Check if this provision's text references any deviating defined terms
        tenant_text = (prov.get("tenant_text", "") or "").lower()
        template_text = (prov.get("template_text", "") or "").lower()
        combined_text = tenant_text + " " + template_text

        # Also check definition_changes field
        defn_changes = (prov.get("definition_changes", "") or "").lower()
        combined_text += " " + defn_changes

        linked_deviations = []
        for term, info in deviating_definitions.items():
            term_lower = term.lower()
            if term_lower in combined_text:
                linked_deviations.append({
                    "defined_term": term,
                    "deviating_provision": info["provision"],
                    "severity": info["severity"],
                    "summary": info["summary"],
                })

        if not linked_deviations:
            continue

        # Build linkage record
        linked_prov_refs = ", ".join(
            f"{ld['deviating_provision']}" for ld in linked_deviations
        )
        linkage_warning = (
            f"This provision conforms on its face but depends on defined "
            f"term(s) that were modified elsewhere. Review {linked_prov_refs} findings."
        )

        linkage_record = {
            "provision": prov["provision_id"],
            "verdict": "CONFORMS",
            "fragility_signal": "cross_reference_dependency",
            "linked_deviations": linked_deviations,
            "linkage_warning": linkage_warning,
        }

        # Step 4: Attach to provision
        prov["cross_reference_links"] = linkage_record
        warnings.append(linkage_record)

    # Add top-level summary warnings
    if warnings:
        if "summary" not in results:
            results["summary"] = {}
        results["summary"]["cross_reference_warnings"] = warnings
        print(
            f"[lease_crossref_linker] Found {len(warnings)} cross-reference "
            f"link(s) between conforming and deviating provisions",
            flush=True,
        )
    else:
        print("[lease_crossref_linker] No cross-reference links found", flush=True)

    return results


def _collect_deviating_definitions(provisions: List[dict]) -> Dict[str, dict]:
    """Collect defined terms from deviating provisions with cascade/definition changes.

    Returns a dict mapping term names to their source provision info.
    """
    deviating_definitions = {}

    for prov in provisions:
        if prov.get("final_verdict") != "DEVIATES":
            continue

        pid = prov.get("provision_id", "")
        severity = prov.get("severity", "")

        # Check cascade data
        cascade_source = prov.get("cascade_source")
        cascade_verdict = prov.get("cascade_verdict")
        cascade_mechanism = prov.get("cascade_mechanism", "")

        if cascade_verdict == "CASCADE_MATERIAL" and cascade_source:
            term = cascade_source.get("term", "")
            if term:
                deviating_definitions[term] = {
                    "provision": pid,
                    "severity": severity,
                    "summary": cascade_mechanism or prov.get("risk_headline", ""),
                }

        # Also extract terms from definition_changes field
        defn_changes = prov.get("definition_changes", "")
        if defn_changes and isinstance(defn_changes, str) and len(defn_changes) > 5:
            # Extract quoted terms from definition_changes text
            import re
            # Look for patterns like "Additional Rent" or 'Base Rent'
            quoted_terms = re.findall(r'["\u201c]([^"\u201d]+)["\u201d]', defn_changes)
            for term in quoted_terms:
                term = term.strip()
                if len(term) > 2 and term not in deviating_definitions:
                    deviating_definitions[term] = {
                        "provision": pid,
                        "severity": severity,
                        "summary": prov.get("risk_headline", defn_changes[:200]),
                    }

        # Also check risk_headline for definition-related flags
        risk_headline = prov.get("risk_headline", "")
        if risk_headline and ("definition" in risk_headline.lower() or "defined term" in risk_headline.lower()):
            # The provision name itself may be a defined term
            pname = prov.get("provision_name", "")
            if pname and pname not in deviating_definitions:
                deviating_definitions[pname] = {
                    "provision": pid,
                    "severity": severity,
                    "summary": risk_headline,
                }

    return deviating_definitions
