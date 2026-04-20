"""
CAM Lease Review — Negative Space Detector (Step 241)

Detects structural absence signals in extracted lease provisions.
Pure heuristics — zero API calls.

Negative space signals are EVIDENCE, not verdicts. They feed into the
coverage state assessor (Step 242) which makes the actual determination.

Signal types:
    reserved_or_omitted   — section marked Reserved / Intentionally Omitted
    broken_xref           — cross-reference to a section/exhibit not found in document
    blank_placeholder     — numeric or monetary placeholder left empty
    undefined_term        — defined term referenced but not defined anywhere
    missing_exhibit       — Exhibit/Schedule/Rider referenced but not found
    truncated_list        — list ends mid-sentence suggesting deleted content
    schema_clue_match     — negative space clue from knowledge schema matched

Usage:
    from cam.adapters.lease_review.lease_negative_space import detect_negative_space

    signals = detect_negative_space(provisions, full_tenant_text)
    # Returns dict keyed by provision_id → list of signal dicts
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Compiled patterns ──────────────────────────────────────────────────────────

# Matches "Reserved", "Intentionally Omitted", "Intentionally Left Blank", etc.
_RESERVED_PATTERN = re.compile(
    r"\b(intentionally\s+omitted|intentionally\s+left\s+blank|reserved|"
    r"this\s+section\s+intentionally|omitted\s+intentionally)\b",
    re.IGNORECASE,
)

# Section references: "Section 9.1", "Article IV", "§ 4.2", "Paragraph 3(b)"
_SECTION_REF_PATTERN = re.compile(
    r"\b(?:section|article|paragraph|clause|§)\s*(\d+(?:\.\d+)*(?:\([a-z]\))?)",
    re.IGNORECASE,
)

# Exhibit / Schedule / Rider / Appendix references
_EXHIBIT_REF_PATTERN = re.compile(
    r"\b(?:exhibit|schedule|rider|addendum|appendix|attachment)\s+([A-Z0-9]+(?:-\d+)?)",
    re.IGNORECASE,
)

# Blank dollar amounts: "$___", "$ ___", "$0.00" as a placeholder, "[AMOUNT]", "TBD"
_BLANK_DOLLAR_PATTERN = re.compile(
    r"\$\s*(?:_{2,}|\[[\s_]*\]|\[amount\]|\[to be determined\]|tbd\b|0\.00\b)",
    re.IGNORECASE,
)

# Blank day/number placeholders: "__ days", "[NUMBER] days", "TBD days"
_BLANK_NUMBER_PATTERN = re.compile(
    r"\b(?:_{2,}|\[___+\]|\[number\]|\[to be determined\]|tbd)\s*(?:days?|months?|years?|percent|%)",
    re.IGNORECASE,
)

# Truncated list signals: "including without limitation," or "including but not limited to,"
# followed by end of sentence with nothing listed
_TRUNCATED_LIST_PATTERN = re.compile(
    r"including\s+(?:without\s+limitation|but\s+not\s+limited\s+to)[,\s]*[.;]",
    re.IGNORECASE,
)

# Definition references: "as defined herein", "as defined in Article I", "as defined above"
# used to detect when a term is referenced as defined but we should check if it's actually defined
_DEFINED_TERM_REF_PATTERN = re.compile(
    r'"([A-Z][A-Za-z\s]+?)"\s+(?:as\s+defined\s+(?:herein|above|in\s+(?:article|section)\s+\w+)|'
    r'shall\s+have\s+the\s+meaning)',
    re.IGNORECASE,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _extract_section_numbers(text: str) -> set:
    """Extract all section numbers mentioned in a text block."""
    return {m.group(1) for m in _SECTION_REF_PATTERN.finditer(text)}


def _extract_exhibit_refs(text: str) -> set:
    """Extract all exhibit/schedule/rider labels mentioned in a text block."""
    return {m.group(1).upper() for m in _EXHIBIT_REF_PATTERN.finditer(text)}


def _extract_definitions(full_text: str) -> set:
    """
    Extract defined terms from the full document text.
    Looks for patterns like: "Term" means ..., "Term" shall mean ...,
    "Term" is defined as ...
    """
    defined = set()
    define_pattern = re.compile(
        r'"([A-Z][A-Za-z\s]{1,40}?)"\s+(?:means?|shall\s+mean|is\s+defined\s+as|refers?\s+to)',
        re.IGNORECASE,
    )
    for m in define_pattern.finditer(full_text):
        defined.add(m.group(1).strip().lower())
    return defined


def _extract_section_headers(full_text: str) -> set:
    """
    Extract section numbers that appear as actual section headers in the document.
    These are sections that EXIST, not just references to sections.
    Handles three common header formats:
      - "16.3 Rent During Force Majeure"            (number-first, no "Section" keyword)
      - "Section 16.3. Rent During Force Majeure"   ("Section" keyword + number + period)
      - "Section 16.3 Rent During Force Majeure"    ("Section" keyword + number, no period)
    """
    headers = set()
    # Pattern 1: number-first headers (legacy — preserved byte-for-byte)
    header_pattern = re.compile(
        r"^\s*(\d+(?:\.\d+)*)\s+[A-Z]",
        re.MULTILINE,
    )
    for m in header_pattern.finditer(full_text):
        headers.add(m.group(1))
    # Pattern 2 & 3: "Section N.N." / "Section N.N" headers (new)
    # Period after number is optional. IGNORECASE on Section keyword only (leases
    # vary between Section/section/SECTION). Capital letter or quote must follow
    # to avoid matching inline prose references like "pursuant to Section 14.1 above".
    section_keyword_pattern = re.compile(
        r"^\s*Section\s+(\d+(?:\.\d+)*)\.?\s+[A-Z\"]",
        re.MULTILINE | re.IGNORECASE,
    )
    for m in section_keyword_pattern.finditer(full_text):
        headers.add(m.group(1))
    return headers


def _extract_exhibit_labels(full_text: str) -> set:
    """
    Extract exhibit/schedule labels that actually appear as headers in the document.
    """
    labels = set()
    exhibit_header_pattern = re.compile(
        r"^[\s]*(?:exhibit|schedule|rider|addendum|appendix|attachment)\s+([A-Z0-9]+(?:-\d+)?)\b",
        re.IGNORECASE | re.MULTILINE,
    )
    for m in exhibit_header_pattern.finditer(full_text):
        labels.add(m.group(1).upper())
    return labels


def _make_signal(signal_type: str, description: str, evidence: str,
                 severity: str = "medium") -> dict:
    """Build a standardized signal dict."""
    return {
        "signal_type": signal_type,
        "description": description,
        "evidence": evidence[:200],  # cap to avoid huge payloads
        "severity": severity,        # low / medium / high
    }


# ── Main detector ──────────────────────────────────────────────────────────────

def detect_negative_space(
    provisions: list,
    full_tenant_text: str,
    run_schema_clue_check: bool = True,
) -> dict:
    """Detect negative space signals in extracted lease provisions.

    Args:
        provisions: list of provision dicts from extraction stage
        full_tenant_text: full raw text of the tenant lease document
        run_schema_clue_check: if True, also check schema-defined clues per provision

    Returns:
        dict keyed by provision_id → list of signal dicts.
        Empty list means no signals detected for that provision.
    """
    # Pre-compute document-level structures once
    doc_section_headers = _extract_section_headers(full_tenant_text)
    doc_exhibit_labels = _extract_exhibit_labels(full_tenant_text)
    doc_defined_terms = _extract_definitions(full_tenant_text)

    results = {}

    for prov in provisions:
        pid = prov.get("provision_id", "")
        signals = []

        tenant_text = prov.get("tenant_text", "") or ""
        template_text = prov.get("template_text", "") or ""
        provision_name = prov.get("provision_name", pid)

        # ── 1. Reserved / Intentionally Omitted ──────────────────────────────
        if _RESERVED_PATTERN.search(tenant_text):
            match = _RESERVED_PATTERN.search(tenant_text)
            signals.append(_make_signal(
                "reserved_or_omitted",
                f"{provision_name}: section or subsection marked as omitted/reserved",
                match.group(0),
                severity="high",
            ))

        # ── 2. Broken cross-references ────────────────────────────────────────
        # References in the tenant clause text that don't exist as section headers
        tenant_refs = _extract_section_numbers(tenant_text)
        for ref in tenant_refs:
            # Check if this section number exists in the document
            # We check for exact match AND prefix match (9.1 exists if 9.1.1 is a header)
            exists = (
                ref in doc_section_headers
                or any(h.startswith(ref + ".") for h in doc_section_headers)
                or any(h == ref for h in doc_section_headers)
            )
            if not exists and _is_meaningful_ref(ref):
                signals.append(_make_signal(
                    "broken_xref",
                    f"{provision_name}: references Section {ref} which was not found in document",
                    f"Section {ref}",
                    severity="high",
                ))

        # ── 3. Missing exhibits ───────────────────────────────────────────────
        tenant_exhibit_refs = _extract_exhibit_refs(tenant_text)
        for label in tenant_exhibit_refs:
            if label not in doc_exhibit_labels:
                signals.append(_make_signal(
                    "missing_exhibit",
                    f"{provision_name}: references Exhibit {label} which was not found in document",
                    f"Exhibit {label}",
                    severity="high",
                ))

        # ── 4. Blank placeholders ─────────────────────────────────────────────
        dollar_blanks = _BLANK_DOLLAR_PATTERN.findall(tenant_text)
        for blank in dollar_blanks:
            signals.append(_make_signal(
                "blank_placeholder",
                f"{provision_name}: contains unfilled monetary placeholder",
                blank.strip(),
                severity="medium",
            ))

        number_blanks = _BLANK_NUMBER_PATTERN.findall(tenant_text)
        for blank in number_blanks:
            signals.append(_make_signal(
                "blank_placeholder",
                f"{provision_name}: contains unfilled numeric placeholder",
                blank.strip(),
                severity="medium",
            ))

        # ── 5. Truncated lists ────────────────────────────────────────────────
        if _TRUNCATED_LIST_PATTERN.search(tenant_text):
            match = _TRUNCATED_LIST_PATTERN.search(tenant_text)
            signals.append(_make_signal(
                "truncated_list",
                f"{provision_name}: 'including without limitation' followed by no items — possible deleted content",
                match.group(0),
                severity="low",
            ))

        # ── 6. Referenced-but-undefined defined terms ─────────────────────────
        term_refs = _DEFINED_TERM_REF_PATTERN.findall(tenant_text)
        for term in term_refs:
            if term.strip().lower() not in doc_defined_terms:
                signals.append(_make_signal(
                    "undefined_term",
                    f"{provision_name}: references '{term}' as a defined term but no definition found in document",
                    f'"{term}"',
                    severity="medium",
                ))

        # ── 7. Schema negative-space clue matching ────────────────────────────
        if run_schema_clue_check:
            schema_signals = _check_schema_clues(pid, tenant_text, template_text)
            signals.extend(schema_signals)

        # Deduplicate signals with identical type+evidence
        signals = _deduplicate_signals(signals)

        results[pid] = signals

    total_signals = sum(len(s) for s in results.values())
    logger.info(
        f"[lease_negative_space] Negative space scan complete: "
        f"{total_signals} signal(s) across {len(results)} provisions"
    )

    return results


def _is_meaningful_ref(ref: str) -> bool:
    """Filter out trivial section references that are unlikely to be real xrefs.

    e.g. "1" alone is probably a list item, not a section reference.
    We want things like "9.1", "14.2.3", "IV" etc.
    """
    # Single digit with no decimal — likely a list item
    if re.match(r"^\d$", ref):
        return False
    # Very high numbers unlikely to be real sections in a lease
    parts = ref.split(".")
    try:
        if int(parts[0]) > 50:
            return False
    except ValueError:
        pass
    return True


def _check_schema_clues(pid: str, tenant_text: str, template_text: str) -> list:
    """Check schema-defined negative space clues for a provision."""
    try:
        from cam.adapters.lease_review.lease_knowledge import get_negative_space_clues
    except ImportError:
        return []

    signals = []
    clues = get_negative_space_clues(pid)
    text_lower = tenant_text.lower()

    for clue in clues:
        clue_lower = clue.lower()
        # Check if any key phrase from the clue appears in the text
        # We use a simplified keyword match: extract key noun phrases from clue
        keywords = _extract_clue_keywords(clue_lower)
        if any(kw in text_lower for kw in keywords):
            signals.append(_make_signal(
                "schema_clue_match",
                f"Schema clue matched: {clue}",
                clue,
                severity="medium",
            ))

    return signals


def _extract_clue_keywords(clue: str) -> list:
    """Extract meaningful keywords from a schema clue string for text matching."""
    # Remove common stop phrases and extract meaningful terms
    stop_words = {
        "section", "marked", "present", "but", "with", "no", "not",
        "the", "a", "an", "or", "and", "in", "of", "to", "for",
        "is", "are", "has", "have", "been", "by", "at", "as",
    }
    # Split on spaces and punctuation, filter stop words, keep 4+ char words
    words = re.split(r"[\s\-–—/,;:()]+", clue)
    keywords = [
        w for w in words
        if len(w) >= 4 and w not in stop_words
    ]
    return keywords[:3]  # return top 3 keywords to avoid over-matching


def _deduplicate_signals(signals: list) -> list:
    """Remove signals with identical type and evidence text."""
    seen = set()
    deduped = []
    for sig in signals:
        key = (sig["signal_type"], sig["evidence"][:50])
        if key not in seen:
            seen.add(key)
            deduped.append(sig)
    return deduped


# ── Summary helpers ────────────────────────────────────────────────────────────

def summarize_negative_space(signals_by_provision: dict) -> dict:
    """Build a summary of negative space findings across all provisions.

    Returns:
        {
            "total_signals": int,
            "provisions_with_signals": int,
            "by_type": {"reserved_or_omitted": N, "broken_xref": N, ...},
            "high_severity_count": int,
            "flagged_provision_ids": [list of PIDs with any signal],
        }
    """
    total = 0
    by_type = {}
    high_count = 0
    flagged = []

    for pid, signals in signals_by_provision.items():
        if signals:
            flagged.append(pid)
            for sig in signals:
                total += 1
                stype = sig.get("signal_type", "unknown")
                by_type[stype] = by_type.get(stype, 0) + 1
                if sig.get("severity") == "high":
                    high_count += 1

    return {
        "total_signals": total,
        "provisions_with_signals": len(flagged),
        "by_type": by_type,
        "high_severity_count": high_count,
        "flagged_provision_ids": sorted(flagged),
    }


# ── CLI / Quick Test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Quick smoke test with synthetic provision data
    test_provisions = [
        {
            "provision_id": "LP-09",
            "provision_name": "Subletting & Assignment",
            "tenant_text": (
                'Tenant may assign this Lease with Landlord\'s consent, as defined in Section 14.7. '
                'Affiliate (as defined herein) assignments are permitted without consent. '
                'Profit sharing shall be per Exhibit C. '
                'The cure period shall be ___ days.'
            ),
            "template_text": "Standard assignment provision text.",
        },
        {
            "provision_id": "LP-11",
            "provision_name": "Default & Remedies",
            "tenant_text": (
                'In the event of default, Landlord may exercise remedies set forth in Section 9.1 '
                'and Section 22.4. Acceleration of rent shall be per Exhibit F. '
                'This section intentionally omitted with respect to tenant self-help rights.'
            ),
            "template_text": "Standard default provision text.",
        },
        {
            "provision_id": "LP-14",
            "provision_name": "Force Majeure",
            "tenant_text": (
                'Force majeure events include, without limitation, acts of God, war, pandemics, '
                'including without limitation.'
            ),
            "template_text": "Standard force majeure text.",
        },
    ]

    # Synthetic full document text — includes some sections but not all referenced ones
    fake_full_text = """
    ARTICLE I — DEFINITIONS
    "Affiliate" means any entity controlling, controlled by, or under common control.

    1.1 Parties. Landlord is ABC Corp, Tenant is XYZ LLC.

    ARTICLE IX — MAINTENANCE
    9.1 Landlord Maintenance. Landlord shall maintain the roof and structure.

    ARTICLE XIV — ASSIGNMENT
    14.1 General. Tenant shall not assign without consent.

    EXHIBIT A — RENT SCHEDULE
    Base Rent: $8,400/month.
    """

    print("Running negative space detection on test provisions...\n")
    results = detect_negative_space(test_provisions, fake_full_text)

    for pid, signals in results.items():
        print(f"{pid}: {len(signals)} signal(s)")
        for sig in signals:
            print(f"  [{sig['severity'].upper()}] {sig['signal_type']}: {sig['description']}")
        if not signals:
            print("  (no signals)")

    print()
    summary = summarize_negative_space(results)
    print("Summary:")
    print(f"  Total signals: {summary['total_signals']}")
    print(f"  High severity: {summary['high_severity_count']}")
    print(f"  By type: {summary['by_type']}")
    print(f"  Flagged provisions: {summary['flagged_provision_ids']}")

    # ── Step 248 inline unit test: Section N.N. header format ─────────────────
    # Ensures _extract_section_headers() now recognizes the "Section 16.3." style
    # headers used in T-10 Article XVI (and inherited from the standard template).
    print("\n[Step 248] Unit test — Section N.N. header recognition")
    t10_article_xvi_fixture = """
ARTICLE XVI — FORCE MAJEURE

Section 16.1. Force Majeure. Neither party shall be in default.
Section 16.2. Duration. If a Force Majeure Event prevents performance.
Section 16.3. Rent During Force Majeure. Tenant's obligation to pay.
"""
    hdrs = _extract_section_headers(t10_article_xvi_fixture)
    expected = {"16.1", "16.2", "16.3"}
    missing = expected - hdrs
    assert not missing, f"FAIL: missing headers {missing}; got {sorted(hdrs)}"
    print(f"  PASS: detected Section N.N headers {sorted(expected)}")

    # Legacy number-first format must still work
    legacy_fixture = "\n9.1 Landlord Maintenance. Landlord shall maintain.\n"
    legacy_hdrs = _extract_section_headers(legacy_fixture)
    assert "9.1" in legacy_hdrs, f"FAIL: legacy regex broken, got {legacy_hdrs}"
    print(f"  PASS: legacy number-first format preserved ({sorted(legacy_hdrs)})")
