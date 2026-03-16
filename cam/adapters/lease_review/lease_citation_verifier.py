"""
lease_citation_verifier.py — Post-processing citation integrity check.

After evaluators return their responses, verify that any section references
cited in the reasoning actually appear in the provided document text.

This is a pure string-matching check — 0 API calls, fast, deterministic.

If a model cites "Section 9.3" but that string does not appear in either
the template or tenant text for that provision, the evidence_basis is
overridden to "unverified_citation" — which the scorer discounts.

This catches the most common fabrication pattern (citing a plausible-sounding
but nonexistent section number) without requiring expensive re-verification.
"""

import re
from typing import List, Optional


# Regex to extract section/article references from reasoning text.
# Matches: "Section 9.3", "Article XIV", "Section 14.2(a)", "§ 9.3", "Art. VII"
_SECTION_REF_PATTERN = re.compile(
    r'(?:'
    r'Section\s+\d+(?:\.\d+)*(?:\([a-z]\))?'   # Section 9.3, Section 14.2(a)
    r'|Article\s+(?:[IVXLC]+|\d+)'              # Article XIV, Article 2
    r'|Art\.\s+(?:[IVXLC]+|\d+)'               # Art. VII
    r'|§\s*\d+(?:\.\d+)*'                       # § 9.3
    r')',
    re.IGNORECASE
)


def _extract_section_refs(text: str) -> List[str]:
    """Extract all section/article references from a reasoning string."""
    return _SECTION_REF_PATTERN.findall(text)


def _normalize_ref(ref: str) -> str:
    """Normalize a section reference for matching.
    e.g. 'Section  9.3' -> 'section 9.3', 'Article XIV' -> 'article xiv'
    """
    return re.sub(r'\s+', ' ', ref.strip().lower())


def _ref_exists_in_text(ref: str, template_text: str, tenant_text: str) -> bool:
    """Check if a section reference appears in either document text.

    Uses case-insensitive substring matching. Checks both the exact ref
    and a normalized version (collapsed whitespace, lowercase).
    """
    ref_norm = _normalize_ref(ref)
    combined = (template_text + " " + tenant_text).lower()
    combined_norm = re.sub(r'\s+', ' ', combined)
    return ref_norm in combined_norm


def verify_evidence_basis(
    provision_id: str,
    reasoning: str,
    evidence_basis: str,
    template_text: str,
    tenant_text: str,
) -> str:
    """Verify the evidence_basis for a single evaluator's reasoning.

    If the model claimed 'explicit_text', check that at least one of the
    section references it cited actually appears in the documents.
    If none are found, override to 'unverified_citation'.

    Other basis values (structural_inference, absence, ambiguous) pass through
    unchanged — they don't make factual citation claims.

    Args:
        provision_id:   For logging purposes.
        reasoning:      The model's reasoning text.
        evidence_basis: The model's self-declared evidence_basis.
        template_text:  Template clause text for this provision.
        tenant_text:    Tenant clause text for this provision.

    Returns:
        Verified evidence_basis string — either the original or
        'unverified_citation' if explicit_text claims don't check out.
    """
    # Only verify explicit_text claims — other types don't make citation claims
    if evidence_basis != "explicit_text":
        return evidence_basis

    # Extract section references from reasoning
    cited_refs = _extract_section_refs(reasoning)

    # If no refs cited but model claims explicit_text, downgrade to structural_inference.
    # The model may have used phrasing like "the tenant text reads..." without a section
    # number — that's fine, just not section-verifiable. Don't penalize.
    if not cited_refs:
        return "structural_inference"

    # Check each cited ref against the documents
    for ref in cited_refs:
        if _ref_exists_in_text(ref, template_text, tenant_text):
            return "explicit_text"  # At least one ref checks out — accept

    # All cited refs failed verification
    print(
        f"[lease_citation_verifier] {provision_id}: "
        f"unverified citation(s): {cited_refs[:3]} not found in clause texts",
        flush=True
    )
    return "unverified_citation"


def verify_all_evidence_bases(
    aggregated_provisions: List[dict],
    extraction_provisions: List[dict],
    evaluator_results: dict,
) -> None:
    """Verify evidence_basis for all evaluator responses in place.

    Mutates evaluator_results[key]["evaluations"][pid]["evidence_basis"]
    to "unverified_citation" where verification fails.

    Also sets aggregated_provisions[i]["evidence_bases"] = {A: ..., B: ..., C: ...}
    and aggregated_provisions[i]["evidence_basis_consensus"] = most conservative value.

    Args:
        aggregated_provisions: Output of _aggregate_evaluations — mutated in place.
        extraction_provisions: Stage 1 output — used to get clause texts.
        evaluator_results:     Stage 2 evaluator outputs — mutated in place.
    """
    # Build a quick lookup: provision_id -> (template_text, tenant_text)
    text_map = {
        p["provision_id"]: (
            p.get("template_text", ""),
            p.get("tenant_text", ""),
        )
        for p in extraction_provisions
    }

    # Basis priority for consensus (most conservative wins)
    PRIORITY = {
        "unverified_citation": 0,  # worst
        "ambiguous":           1,
        "structural_inference": 2,
        "absence":             3,
        "explicit_text":       4,  # best
    }

    for agg in aggregated_provisions:
        pid = agg["provision_id"]
        tmpl_text, tenant_text = text_map.get(pid, ("", ""))

        bases = {}
        for key in ["A", "B", "C"]:
            ev_result = evaluator_results.get(key, {})
            if "error" in ev_result:
                bases[key] = None
                continue

            ev = ev_result.get("evaluations", {}).get(pid, {})
            original_basis = ev.get("evidence_basis", "structural_inference")
            reasoning = ev.get("reasoning", "")

            verified_basis = verify_evidence_basis(
                provision_id=pid,
                reasoning=reasoning,
                evidence_basis=original_basis,
                template_text=tmpl_text,
                tenant_text=tenant_text,
            )

            # Mutate in place
            ev["evidence_basis"] = verified_basis
            bases[key] = verified_basis

        # Compute consensus: most conservative across active evaluators
        active_bases = [b for b in bases.values() if b is not None]
        if active_bases:
            consensus = min(active_bases, key=lambda b: PRIORITY.get(b, 2))
        else:
            consensus = "structural_inference"

        agg["evidence_bases"] = bases
        agg["evidence_basis_consensus"] = consensus
